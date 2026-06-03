from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .adapters import FiveEToolsCnAdapter
from .chunking import build_chunks
from .models import RuleChunk, RuleDocument, SearchResult, SearchScope
from .planner import MultiHopEvidencePlanner, MultiHopSearchResult
from .providers import EmbeddingProvider
from .retrieval import HybridRetriever


@dataclass
class AskResponse:
    answer: str
    direct_answer: str
    supporting_points: List[str]
    caveats: List[str]
    citations: List[Dict[str, str]]
    related_entries: List[RuleDocument]
    evidence: List[SearchResult]
    mode: str
    is_multi_hop: bool = False
    coverage_score: float = 0.0
    missing_requirements: List[str] = field(default_factory=list)
    evidence_requirements: List[Dict[str, object]] = field(default_factory=list)


class RagService:
    def __init__(
        self,
        documents: List[RuleDocument],
        chunks: List[RuleChunk],
        chunk_embeddings: Dict[str, List[float]] | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.documents = documents
        self.chunks = chunks
        self.documents_by_id = {doc.id: doc for doc in documents}
        self.retriever = HybridRetriever(
            chunks,
            chunk_embeddings=chunk_embeddings,
            embedding_provider=embedding_provider,
        )
        self.planner = MultiHopEvidencePlanner(self.retriever)

    @classmethod
    def from_adapter(cls, adapter: FiveEToolsCnAdapter) -> "RagService":
        documents = adapter.load_documents()
        chunks = [chunk for doc in documents for chunk in build_chunks(doc)]
        return cls(documents, chunks)

    @classmethod
    def from_sample_data(cls) -> "RagService":
        return cls.from_adapter(FiveEToolsCnAdapter.sample())

    def ask(self, question: str, scope: str = "core") -> AskResponse:
        search_scope = SearchScope.FULL if scope == "full" else SearchScope.CORE
        planned = self.planner.search(question, scope=search_scope, top_k=8)
        evidence = planned.evidence
        related = self._related_entries(evidence)
        missing_requirements = [requirement.label for requirement in planned.missing_requirements]
        direct_answer = self._direct_answer(question, search_scope, evidence, missing_requirements)
        supporting_points = self._supporting_points(evidence)
        caveats = self._caveats(question, evidence, missing_requirements)
        answer = self._template_answer(question, search_scope, evidence, direct_answer, supporting_points, caveats)
        citations = self._grouped_citations(evidence)
        return AskResponse(
            answer=answer,
            direct_answer=direct_answer,
            supporting_points=supporting_points,
            caveats=caveats,
            citations=citations,
            related_entries=related,
            evidence=evidence,
            mode=search_scope.value,
            is_multi_hop=planned.is_multi_hop,
            coverage_score=planned.coverage_score,
            missing_requirements=missing_requirements,
            evidence_requirements=self._evidence_requirements(planned),
        )

    def entry(self, document_id: str) -> RuleDocument | None:
        return self.documents_by_id.get(document_id)

    def _related_entries(self, evidence: List[SearchResult]) -> List[RuleDocument]:
        seen = set()
        related: List[RuleDocument] = []
        for result in evidence:
            doc = self.documents_by_id.get(result.chunk.document_id)
            if doc and doc.id not in seen:
                related.append(doc)
                seen.add(doc.id)
        return related[:6]

    def _template_answer(
        self,
        question: str,
        scope: SearchScope,
        evidence: List[SearchResult],
        direct_answer: str,
        supporting_points: List[str],
        caveats: List[str],
    ) -> str:
        if not evidence:
            return direct_answer
        if scope == SearchScope.CORE:
            heading = "判定"
            sections = ["依据", "适用条件", "容易误判"]
        else:
            heading = "概览"
            sections = ["相关条目", "分类整理", "关键差异"]
        lines = [
            f"{heading}：{direct_answer}",
            "",
            f"{sections[0]}：",
        ]
        for idx, point in enumerate(supporting_points, 1):
            lines.append(f"{idx}. {point} [{idx}]")
        caveat_text = "；".join(caveats) if caveats else "请以引用片段为准。"
        lines.extend(
            [
                "",
                f"{sections[1]}：{caveat_text}",
                "",
                f"{sections[2]}：如果证据没有覆盖你桌上的特殊能力、特殊感官或房规，应补充上下文后再裁定。",
            ]
        )
        return "\n".join(lines)

    def _answer_evidence(self, evidence: List[SearchResult]) -> List[SearchResult]:
        if not evidence:
            return []
        threshold = evidence[0].score.final_score * 0.5
        focused = [result for result in evidence if result.score.final_score >= threshold]
        return focused[:4] or evidence[:1]

    def _citation_evidence(self, evidence: List[SearchResult]) -> List[SearchResult]:
        focused = self._answer_evidence(evidence)
        children = [result for result in focused if result.chunk.chunk_level == "child"]
        candidates = children or focused
        selected: List[SearchResult] = []
        seen = set()
        for result in candidates:
            key = (result.chunk.document_id, result.chunk.display_text)
            if key in seen:
                continue
            seen.add(key)
            selected.append(result)
        return selected[:4]

    def _grouped_citations(self, evidence: List[SearchResult]) -> List[Dict[str, object]]:
        grouped: Dict[str, Dict[str, object]] = {}
        for result in self._citation_evidence(evidence):
            doc = self.documents_by_id.get(result.chunk.document_id)
            key = result.chunk.document_id
            item = grouped.setdefault(
                key,
                {
                    "document_id": key,
                    "label": result.chunk.citation.label(),
                    "title": result.chunk.citation.title or (doc.title_zh if doc else ""),
                    "source_id": result.chunk.source_id,
                    "score": f"{result.score.final_score:.3f}",
                    "passages": [],
                },
            )
            item["passages"].append(
                {
                    "chunk_id": result.chunk.id,
                    "display_text": result.chunk.display_text,
                    "score": f"{result.score.final_score:.3f}",
                }
            )
        return list(grouped.values())

    def _direct_answer(
        self,
        question: str,
        scope: SearchScope,
        evidence: List[SearchResult],
        missing_requirements: List[str] | None = None,
    ) -> str:
        missing_requirements = missing_requirements or []
        if missing_requirements:
            missing = "、".join(missing_requirements)
            return f"当前证据不足，缺少必要证据：{missing}。不能可靠完成这个复合裁定。"
        if not evidence:
            return "当前资料没有检索到足够依据，不能可靠裁定。建议切换到全量模式或补充更具体的问题。"
        corpus = " ".join(result.chunk.text for result in evidence[:5])
        if "隐形" in corpus and "攻击检定" in corpus and "优势" in corpus:
            return "通常有优势。若攻击者处于隐形且目标无法看见它，隐形生物进行攻击检定时具有优势；但特殊感官、魔法或具体场景可能改变这个前提。"
        if "专注" in corpus and "体质豁免" in corpus:
            return "不会自动中断。受到伤害时通常需要进行体质豁免来维持专注，失败才会失去专注。"
        if "借机攻击" in corpus and "触及范围" in corpus:
            return "通常在敌对生物离开你的触及范围时触发，你可以用反应发动借机攻击；若目标采取撤离动作，则不会触发。"
        top = evidence[0].chunk
        if scope == SearchScope.CORE:
            return f"根据核心规则，最相关条目是《{top.citation.title}》。需要结合下方依据确认具体条件。"
        return f"在全量资料中，最相关条目是《{top.citation.title}》。下方列出相关条目和证据链。"

    def _supporting_points(self, evidence: List[SearchResult]) -> List[str]:
        focused = self._answer_evidence(evidence)
        children = [result for result in focused if result.chunk.chunk_level == "child"]
        candidates = children or focused
        points: List[str] = []
        seen = set()
        for result in candidates:
            text = result.chunk.display_text
            if text in seen:
                continue
            seen.add(text)
            points.append(text)
        return points[:4]

    def _caveats(
        self,
        question: str,
        evidence: List[SearchResult],
        missing_requirements: List[str] | None = None,
    ) -> List[str]:
        missing_requirements = missing_requirements or []
        if missing_requirements:
            return [f"缺少证据需求：{'、'.join(missing_requirements)}。"]
        if not evidence:
            return ["没有足够证据时不要硬答。"]
        corpus = " ".join(result.chunk.text for result in self._answer_evidence(evidence))
        caveats: List[str] = []
        if "隐形" in corpus:
            caveats.append("关键前提是目标是否真的无法看见或感知攻击者。")
        if "专注" in corpus:
            caveats.append("需要看伤害、豁免结果，以及是否存在其他会打断专注的状态。")
        if "借机攻击" in corpus:
            caveats.append("撤离、强制移动、传送等情况需要按对应规则另行判断。")
        if not caveats:
            caveats.append("请以引用片段覆盖的条件为准。")
        return caveats[:3]

    def _evidence_requirements(self, planned: MultiHopSearchResult) -> List[Dict[str, object]]:
        items: List[Dict[str, object]] = []
        for group in planned.requirement_evidence:
            items.append(
                {
                    "id": group.requirement.id,
                    "label": group.requirement.label,
                    "role": group.requirement.role,
                    "required": group.requirement.required,
                    "covered": group.covered,
                    "evidence_titles": [result.chunk.citation.title for result in group.evidence],
                }
            )
        return items
