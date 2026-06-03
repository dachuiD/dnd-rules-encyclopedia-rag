from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .adapters import FiveEToolsCnAdapter
from .chunking import build_chunks
from .models import RuleChunk, RuleDocument, SearchResult, SearchScope
from .planner import MultiHopEvidencePlanner, MultiHopSearchResult
from .providers import EmbeddingProvider, LLMProvider
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
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.documents = documents
        self.chunks = chunks
        self.chunk_embeddings = chunk_embeddings or {}
        self.embedding_provider = embedding_provider
        self.llm_provider = llm_provider
        self.documents_by_id = {doc.id: doc for doc in documents}
        self.retriever = HybridRetriever(
            chunks,
            chunk_embeddings=self.chunk_embeddings,
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
        evidence_requirements = self._evidence_requirements(planned)
        direct_answer = self._direct_answer(question, search_scope, evidence, missing_requirements)
        supporting_points = self._supporting_points(evidence)
        caveats = self._caveats(question, evidence, missing_requirements)
        answer = self._template_answer(question, search_scope, evidence, direct_answer, supporting_points, caveats)
        if self.llm_provider:
            answer = self._llm_answer(question, search_scope, evidence, evidence_requirements)
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
            evidence_requirements=evidence_requirements,
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
                f"{sections[2]}：如果证据没有覆盖额外例外，应补充上下文后再裁定。",
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

    def _llm_answer(
        self,
        question: str,
        scope: SearchScope,
        evidence: List[SearchResult],
        evidence_requirements: List[Dict[str, object]],
    ) -> str:
        system_prompt = (
            "你是中文 D&D 规则百科 RAG 产品的回答器。只能基于 evidence pack 回答。"
            "不能补充 evidence pack 之外的规则细节，即使你知道这些细节是真的。"
            "如果 evidence pack 顶部包含 Evidence Requirements，必须先检查每个 required requirement 的 status。"
            "只要存在 missing 的 required requirement，结论必须是证据不足，不能把缺失需求当成已覆盖。"
            "适用条件只能写 evidence pack 明示的信息；没有明示就写“证据包未覆盖更多适用条件”。"
            "容易误判只能写 evidence pack 已经出现的误判点；没有明示就写“证据包未覆盖常见误判”。"
            "输出结构：结论、依据、适用条件、容易误判、引用。每个关键结论必须带 [E编号]。"
        )
        user_prompt = "\n\n".join(
            [
                f"Question: {question}",
                f"Scope: {scope.value}",
                "Evidence Pack:",
                self._evidence_pack(evidence, evidence_requirements),
            ]
        )
        return self.llm_provider.answer(system_prompt, user_prompt)

    def _evidence_pack(self, evidence: List[SearchResult], evidence_requirements: List[Dict[str, object]]) -> str:
        lines: List[str] = []
        if evidence_requirements:
            lines.append("Evidence Requirements:")
            for item in evidence_requirements:
                status = "covered" if item.get("covered") else "missing"
                required = "required" if item.get("required") else "optional"
                titles = "、".join(str(title) for title in item.get("evidence_titles", []) if title) or "-"
                lines.append(
                    "- {id} | {label} | role={role} | {required} | status={status} | evidence_titles={titles}".format(
                        id=item.get("id", ""),
                        label=item.get("label", ""),
                        role=item.get("role", ""),
                        required=required,
                        status=status,
                        titles=titles,
                    )
                )
        for idx, result in enumerate(evidence, 1):
            chunk = result.chunk
            text = " ".join(chunk.display_text.split())
            lines.append(
                "[E{}] {} | {} | document_id={} | score={:.3f}\n{}".format(
                    idx,
                    chunk.citation.title or chunk.document_id,
                    chunk.citation.label(),
                    chunk.document_id,
                    result.score.final_score,
                    text,
                )
            )
        return "\n\n".join(lines)
