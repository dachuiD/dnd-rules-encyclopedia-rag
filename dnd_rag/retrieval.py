from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import replace
from typing import Dict, Iterable, List, Sequence, Set

from .models import CORE_SOURCES, EvidenceScore, RuleChunk, SearchResult, SearchScope


DEFAULT_ALIASES = {
    "机会攻击": "借机攻击",
    "藉机攻击": "借机攻击",
    "隐身": "隐形",
    "维持法术": "专注",
    "救免": "豁免",
    "有利": "优势",
    "不利": "劣势",
    "被打": "受到伤害",
    "挨打": "受到伤害",
    "打了一下": "受到伤害",
    "立刻断": "专注",
    "oa": "借机攻击",
    "opportunity attack": "借机攻击",
}


CORE_WEIGHTS = {
    "dense": 0.40,
    "lexical": 0.30,
    "alias": 0.10,
    "title": 0.10,
    "source": 0.05,
    "structure": 0.05,
}

FULL_WEIGHTS = {
    "dense": 0.45,
    "lexical": 0.20,
    "alias": 0.10,
    "title": 0.15,
    "source": 0.02,
    "structure": 0.08,
}


class HybridRetriever:
    def __init__(self, chunks: Sequence[RuleChunk], aliases: Dict[str, str] | None = None) -> None:
        self.chunks = list(chunks)
        self.aliases = {**DEFAULT_ALIASES, **(aliases or {})}
        self.doc_children = defaultdict(list)
        for chunk in self.chunks:
            if chunk.parent_chunk_id:
                self.doc_children[chunk.parent_chunk_id].append(chunk)

    def search(self, query: str, scope: SearchScope = SearchScope.CORE, top_k: int = 8) -> List[SearchResult]:
        scoped = [chunk for chunk in self.chunks if self._in_scope(chunk, scope)]
        normalized_query, matched_aliases = self._normalize_query(query)
        query_tokens = _tokens(normalized_query)
        dense_raw = {}
        lexical_raw = {}
        for chunk in scoped:
            dense_raw[chunk.id] = _jaccard(query_tokens, _tokens(chunk.embedding_text))
            lexical_raw[chunk.id] = _lexical_overlap(query_tokens, _tokens(chunk.text + " " + " ".join(chunk.aliases)))

        dense_scores = _normalize_scores(dense_raw)
        lexical_scores = _normalize_scores(lexical_raw)
        weights = CORE_WEIGHTS if scope == SearchScope.CORE else FULL_WEIGHTS
        results: List[SearchResult] = []

        for chunk in scoped:
            alias_score = self._alias_score(chunk, matched_aliases)
            title_score = self._title_score(chunk, normalized_query)
            source_score = 1.0 if chunk.source_id in CORE_SOURCES else 0.3
            structure_score = 1.0 if chunk.chunk_type in {"rule", "definition", "spell_description", "feature"} else 0.5
            score = EvidenceScore(
                dense_score=dense_scores.get(chunk.id, 0.0),
                lexical_score=lexical_scores.get(chunk.id, 0.0),
                alias_score=alias_score,
                title_score=title_score,
                source_score=source_score,
                structure_score=structure_score,
                reasons=[],
            )
            score.final_score = (
                weights["dense"] * score.dense_score
                + weights["lexical"] * score.lexical_score
                + weights["alias"] * score.alias_score
                + weights["title"] * score.title_score
                + weights["source"] * score.source_score
                + weights["structure"] * score.structure_score
            )
            score.reasons = self._reasons(chunk, score, matched_aliases)
            if score.final_score > 0:
                results.append(SearchResult(chunk=chunk, score=score))

        results.sort(key=lambda result: result.score.final_score, reverse=True)
        expanded = self._parent_child_expand(results, scoped)
        return expanded[:top_k]

    def _in_scope(self, chunk: RuleChunk, scope: SearchScope) -> bool:
        if chunk.knowledge_domain in {"adventure", "utility"}:
            return False
        if scope == SearchScope.CORE:
            return chunk.search_scope == "core" and chunk.source_id in CORE_SOURCES
        return chunk.knowledge_domain in {"rules", "entity", "lore"}

    def _normalize_query(self, query: str) -> tuple[str, Dict[str, str]]:
        normalized = query
        matched: Dict[str, str] = {}
        lower_query = query.lower()
        for alias, canonical in self.aliases.items():
            if alias.lower() in lower_query:
                matched[alias] = canonical
                normalized += f" {canonical}"
        return normalized, matched

    def _alias_score(self, chunk: RuleChunk, matched_aliases: Dict[str, str]) -> float:
        if not matched_aliases:
            return 0.0
        corpus = " ".join([chunk.text, chunk.embedding_text, *chunk.aliases]).lower()
        return 1.0 if any(canonical.lower() in corpus for canonical in matched_aliases.values()) else 0.0

    def _title_score(self, chunk: RuleChunk, query: str) -> float:
        query_lower = query.lower()
        for alias in chunk.aliases:
            if alias and alias.lower() in query_lower:
                return 1.0
        if any(part and part.lower() in query_lower for part in chunk.title_path):
            return 1.0
        return 0.0

    def _reasons(self, chunk: RuleChunk, score: EvidenceScore, matched_aliases: Dict[str, str]) -> List[str]:
        reasons: List[str] = []
        if score.dense_score > 0:
            reasons.append(f"语义相似 {score.dense_score:.2f}")
        if score.lexical_score > 0:
            reasons.append(f"关键词重合 {score.lexical_score:.2f}")
        for alias, canonical in matched_aliases.items():
            corpus = " ".join([chunk.text, chunk.embedding_text, *chunk.aliases]).lower()
            if canonical.lower() in corpus:
                reasons.append(f"别名命中：{alias} -> {canonical}")
        if score.title_score > 0:
            reasons.append("标题/条目名命中")
        if chunk.source_id in CORE_SOURCES:
            reasons.append(f"核心来源：{chunk.source_id}")
        reasons.append(f"结构类型：{chunk.chunk_type}")
        return reasons

    def _parent_child_expand(self, results: List[SearchResult], scoped: Sequence[RuleChunk]) -> List[SearchResult]:
        by_id = {chunk.id: chunk for chunk in scoped}
        seen: Set[str] = set()
        expanded: List[SearchResult] = []
        for result in results:
            if result.chunk.id not in seen:
                expanded.append(result)
                seen.add(result.chunk.id)
            parent_id = result.chunk.parent_chunk_id
            if parent_id and parent_id in by_id and parent_id not in seen:
                parent_score = replace(result.score, final_score=result.score.final_score * 0.92)
                parent_score.reasons = result.score.reasons + ["父级条目补全上下文"]
                expanded.append(SearchResult(chunk=by_id[parent_id], score=parent_score))
                seen.add(parent_id)
            elif result.chunk.chunk_level == "parent":
                for child in self.doc_children.get(result.chunk.id, [])[:2]:
                    if child.id in seen:
                        continue
                    child_score = replace(result.score, final_score=result.score.final_score * 0.88)
                    child_score.reasons = result.score.reasons + ["子级证据补充精确引用"]
                    expanded.append(SearchResult(chunk=child, score=child_score))
                    seen.add(child.id)
        expanded.sort(key=lambda item: item.score.final_score, reverse=True)
        return expanded


def _tokens(text: str) -> Counter:
    lower = text.lower()
    cjk = re.findall(r"[\u4e00-\u9fff]{1,2}", lower)
    latin = re.findall(r"[a-z0-9]+", lower)
    terms = re.findall(r"[\u4e00-\u9fff]{2,8}", lower)
    return Counter(cjk + latin + terms)


def _jaccard(left: Counter, right: Counter) -> float:
    if not left or not right:
        return 0.0
    intersection = sum((left & right).values())
    union = sum((left | right).values())
    return intersection / union if union else 0.0


def _lexical_overlap(left: Counter, right: Counter) -> float:
    if not left or not right:
        return 0.0
    overlap = sum((left & right).values())
    return overlap / max(1, sum(left.values()))


def _normalize_scores(scores: Dict[str, float]) -> Dict[str, float]:
    if not scores:
        return {}
    max_score = max(scores.values())
    if max_score <= 0:
        return {key: 0.0 for key in scores}
    return {key: value / max_score for key, value in scores.items()}
