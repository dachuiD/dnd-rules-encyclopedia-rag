from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, List, Sequence

from .models import EvidenceScore, SearchResult, SearchScope
from .retrieval import HybridRetriever


@dataclass(frozen=True)
class EvidenceRequirement:
    id: str
    label: str
    query: str
    required_terms: List[str]
    preferred_categories: List[str]
    expected_titles: List[str]
    role: str
    required: bool = True


@dataclass(frozen=True)
class QueryAnalysis:
    original_query: str
    explicit_entities: List[str]
    category_mentions: List[str]
    mechanic_mentions: List[str]
    likely_multi_hop: bool


@dataclass(frozen=True)
class RequirementEvidence:
    requirement: EvidenceRequirement
    evidence: List[SearchResult]
    covered: bool


@dataclass(frozen=True)
class MultiHopPlan:
    analysis: QueryAnalysis
    requirements: List[EvidenceRequirement]


@dataclass(frozen=True)
class MultiHopSearchResult:
    plan: MultiHopPlan
    requirement_evidence: List[RequirementEvidence]
    evidence: List[SearchResult]
    coverage_score: float
    missing_requirements: List[EvidenceRequirement]

    @property
    def is_multi_hop(self) -> bool:
        return self.plan.analysis.likely_multi_hop


@dataclass(frozen=True)
class _Concept:
    requirement: EvidenceRequirement
    matcher: Callable[[str], bool]
    entity_markers: List[str]
    category_markers: List[str]
    mechanic_markers: List[str]


class MultiHopEvidencePlanner:
    def __init__(self, retriever: HybridRetriever) -> None:
        self.retriever = retriever
        self.concepts = _concepts()

    def plan(self, query: str) -> MultiHopPlan:
        normalized = query.lower()
        matched = [concept for concept in self.concepts if concept.matcher(normalized)]
        requirements = _dedupe_requirements([concept.requirement for concept in matched])
        analysis = QueryAnalysis(
            original_query=query,
            explicit_entities=_dedupe([marker for concept in matched for marker in concept.entity_markers if marker in query]),
            category_mentions=_dedupe([marker for concept in matched for marker in concept.category_markers if marker in query]),
            mechanic_mentions=_dedupe([marker for concept in matched for marker in concept.mechanic_markers if marker in query]),
            likely_multi_hop=len(requirements) > 1,
        )
        return MultiHopPlan(analysis=analysis, requirements=requirements)

    def search(self, query: str, scope: SearchScope = SearchScope.CORE, top_k: int = 8) -> MultiHopSearchResult:
        plan = self.plan(query)
        if not plan.requirements:
            evidence = self.retriever.search(query, scope=scope, top_k=top_k)
            return MultiHopSearchResult(
                plan=plan,
                requirement_evidence=[],
                evidence=evidence,
                coverage_score=0.0,
                missing_requirements=[],
            )

        per_requirement: List[RequirementEvidence] = []
        for requirement in plan.requirements:
            candidates = self.retriever.search(requirement.query, scope=scope, top_k=max(4, top_k))
            matching = [result for result in candidates if _matches_requirement(result, requirement)]
            selected = matching or candidates[:1]
            covered = bool(matching)
            per_requirement.append(
                RequirementEvidence(requirement=requirement, evidence=_tag_evidence(selected, requirement), covered=covered)
            )

        merged = _merge_requirement_evidence(per_requirement, top_k)
        required = [group for group in per_requirement if group.requirement.required]
        covered_required = [group for group in required if group.covered]
        missing = [group.requirement for group in required if not group.covered]
        coverage = len(covered_required) / len(required) if required else 0.0
        return MultiHopSearchResult(
            plan=plan,
            requirement_evidence=per_requirement,
            evidence=merged,
            coverage_score=coverage,
            missing_requirements=missing,
        )


def _concepts() -> List[_Concept]:
    return [
        _Concept(
            requirement=EvidenceRequirement(
                id="counterspell_trigger",
                label="反制法术触发条件",
                query="反制法术 counterspell 中断 生物 施展法术 反应 触发条件 看见 60尺",
                required_terms=["反制法术", "施展法术"],
                preferred_categories=["spells"],
                expected_titles=["反制法术"],
                role="trigger_rule",
            ),
            matcher=lambda query: "反制法术" in query or "counterspell" in query,
            entity_markers=["反制法术"],
            category_markers=["法术"],
            mechanic_markers=["反制", "施展法术"],
        ),
        _Concept(
            requirement=EvidenceRequirement(
                id="magic_item_activation",
                label="魔法物品激活与施法机制",
                query="魔法物品 激活物品 从物品中施展法术 无需构材 施法",
                required_terms=["魔法物品", "激活物品", "施展法术"],
                preferred_categories=["actions", "items", "variantrules"],
                expected_titles=["激活物品"],
                role="mechanic_rule",
            ),
            matcher=_mentions_magic_item_casting,
            entity_markers=["激活物品"],
            category_markers=["魔法物品", "物品"],
            mechanic_markers=["施法", "施展法术", "激活"],
        ),
        _Concept(
            requirement=EvidenceRequirement(
                id="subtle_spell_mechanic",
                label="微妙法术成分机制",
                query="微妙法术 subtle spell 超魔 无需 姿势 言语 成分",
                required_terms=["微妙法术", "无需", "言语", "姿势"],
                preferred_categories=["optionalfeatures", "class"],
                expected_titles=["微妙法术"],
                role="exception_rule",
            ),
            matcher=_mentions_subtle_spell,
            entity_markers=["微妙法术"],
            category_markers=["超魔"],
            mechanic_markers=["静默施法", "言语成分", "姿势成分"],
        ),
        _Concept(
            requirement=EvidenceRequirement(
                id="spell_component_observability",
                label="施法构材可观察性",
                query="辨识法术 感知 施法 法术效果 声音构材 姿势构材 材料构材 看见",
                required_terms=["感知到了施法", "感知到了"],
                preferred_categories=["actions", "book", "variantrules"],
                expected_titles=["辨识法术", "施法构材"],
                role="visibility_rule",
            ),
            matcher=_mentions_casting_observability_question,
            entity_markers=[],
            category_markers=["构材"],
            mechanic_markers=["看见施法", "辨识法术", "可观察施法"],
        ),
        _Concept(
            requirement=EvidenceRequirement(
                id="invisible_condition",
                label="隐形状态规则",
                query="隐形 隐身 状态 攻击检定 优势 劣势 看见",
                required_terms=["隐形", "攻击检定", "优势", "劣势"],
                preferred_categories=["conditions"],
                expected_titles=["隐形"],
                role="condition_rule",
            ),
            matcher=lambda query: "隐形" in query or "隐身" in query,
            entity_markers=["隐形", "隐身"],
            category_markers=["状态"],
            mechanic_markers=["攻击检定", "看见"],
        ),
        _Concept(
            requirement=EvidenceRequirement(
                id="blindsight_sense",
                label="盲视感官规则",
                query="盲视 不依赖视觉 感知 看见 隐形 生物",
                required_terms=["盲视", "不依赖视觉", "感知"],
                preferred_categories=["variantrules", "races", "optionalfeatures", "bestiary"],
                expected_titles=["盲视"],
                role="mechanic_rule",
            ),
            matcher=lambda query: "盲视" in query,
            entity_markers=["盲视"],
            category_markers=["感官"],
            mechanic_markers=["不依赖视觉", "看见"],
        ),
        _Concept(
            requirement=EvidenceRequirement(
                id="ready_spell_mechanic",
                label="准备法术机制",
                query="准备 法术 1个动作 施法时间 扣住 能量 反应 释放 专注",
                required_terms=["准备", "法术", "1个动作", "施法时间"],
                preferred_categories=["actions"],
                expected_titles=["准备"],
                role="mechanic_rule",
            ),
            matcher=_mentions_ready_spell,
            entity_markers=["准备"],
            category_markers=["动作", "法术"],
            mechanic_markers=["准备法术", "施法时间"],
        ),
        _Concept(
            requirement=EvidenceRequirement(
                id="bonus_action_spell_limit",
                label="附赠动作施法限制",
                query="附赠动作 施法 同一回合 戏法 1动作 法术 限制",
                required_terms=["附赠动作", "施法", "同一回合", "戏法"],
                preferred_categories=["book"],
                expected_titles=["附赠动作施法限制"],
                role="restriction_rule",
            ),
            matcher=_mentions_bonus_action_spell_limit,
            entity_markers=[],
            category_markers=["附赠动作"],
            mechanic_markers=["附赠动作施法", "同一回合", "戏法"],
        ),
        _Concept(
            requirement=EvidenceRequirement(
                id="concentration_damage_rule",
                label="专注受伤害维持规则",
                query="专注 受到伤害 体质豁免 维持专注 中断 DC",
                required_terms=["专注", "受到伤害", "体质豁免"],
                preferred_categories=["conditionsdiseases", "actions", "book"],
                expected_titles=["专注"],
                role="mechanic_rule",
            ),
            matcher=_mentions_concentration_damage,
            entity_markers=["专注"],
            category_markers=["状态"],
            mechanic_markers=["受到伤害", "体质豁免", "维持专注"],
        ),
        _Concept(
            requirement=EvidenceRequirement(
                id="silence_verbal_component_rule",
                label="沉默术与言语成分规则",
                query="沉默术 言语成分 声音构材 不可能 施放 法术",
                required_terms=["沉默术", "声音构材", "不可能"],
                preferred_categories=["spells"],
                expected_titles=["沉默术"],
                role="restriction_rule",
            ),
            matcher=_mentions_silence_verbal_component,
            entity_markers=["沉默术"],
            category_markers=["法术"],
            mechanic_markers=["言语成分", "声音构材", "施放法术"],
        ),
    ]


def _mentions_magic_item_casting(query: str) -> bool:
    has_item = "魔法物品" in query or "激活物品" in query or "用物品" in query or "物品" in query
    has_casting = "施法" in query or "施展法术" in query or "法术" in query
    return has_item and has_casting


def _mentions_subtle_spell(query: str) -> bool:
    if "微妙法术" in query or "subtle spell" in query or "静默施法" in query:
        return True
    return "超魔" in query and ("静默" in query or "言语" in query or "姿势" in query)


def _mentions_casting_observability_question(query: str) -> bool:
    has_counterspell = "反制法术" in query or "counterspell" in query
    has_hidden_component = _mentions_subtle_spell(query) or "构材" in query or "成分" in query
    return has_counterspell and has_hidden_component


def _mentions_ready_spell(query: str) -> bool:
    return "准备" in query and ("法术" in query or "施法" in query)


def _mentions_bonus_action_spell_limit(query: str) -> bool:
    has_bonus = "附赠动作" in query or "bonus action" in query
    has_spell = "施法" in query or "法术" in query or "spell" in query
    return has_bonus and has_spell


def _mentions_concentration_damage(query: str) -> bool:
    has_concentration = "专注" in query or "维持法术" in query
    has_damage = "受到伤害" in query or "受伤" in query or "挨打" in query or "被打" in query or "伤害" in query
    return has_concentration and has_damage


def _mentions_silence_verbal_component(query: str) -> bool:
    has_silence = "沉默术" in query or "沉默" in query
    has_verbal = "言语成分" in query or "声音构材" in query or "语言成分" in query or "有言语" in query
    return has_silence and has_verbal


def _matches_requirement(result: SearchResult, requirement: EvidenceRequirement) -> bool:
    title = result.chunk.citation.title or ""
    if title in requirement.expected_titles:
        return True
    corpus = " ".join([title, result.chunk.text, result.chunk.embedding_text, *result.chunk.aliases]).lower()
    if requirement.preferred_categories and result.chunk.category not in requirement.preferred_categories:
        return False
    return any(term.lower() in corpus for term in requirement.required_terms)


def _tag_evidence(evidence: Sequence[SearchResult], requirement: EvidenceRequirement) -> List[SearchResult]:
    tagged: List[SearchResult] = []
    for result in evidence:
        score = replace(result.score)
        score.reasons = [*score.reasons, f"证据需求：{requirement.label}"]
        tagged.append(SearchResult(chunk=result.chunk, score=score))
    return tagged


def _merge_requirement_evidence(groups: Sequence[RequirementEvidence], top_k: int) -> List[SearchResult]:
    selected: List[SearchResult] = []
    seen = set()

    for group in groups:
        if not group.covered or not group.evidence:
            continue
        first = group.evidence[0]
        if first.chunk.id in seen:
            continue
        selected.append(first)
        seen.add(first.chunk.id)

    leftovers = [result for group in groups for result in group.evidence]
    leftovers.sort(key=lambda result: result.score.final_score, reverse=True)
    for result in leftovers:
        if result.chunk.id in seen:
            continue
        selected.append(result)
        seen.add(result.chunk.id)
        if len(selected) >= top_k:
            break

    return selected[:top_k]


def _dedupe_requirements(requirements: Sequence[EvidenceRequirement]) -> List[EvidenceRequirement]:
    seen = set()
    deduped: List[EvidenceRequirement] = []
    for requirement in requirements:
        if requirement.id in seen:
            continue
        deduped.append(requirement)
        seen.add(requirement.id)
    return deduped


def _dedupe(values: Sequence[str]) -> List[str]:
    seen = set()
    deduped: List[str] = []
    for value in values:
        if not value or value in seen:
            continue
        deduped.append(value)
        seen.add(value)
    return deduped
