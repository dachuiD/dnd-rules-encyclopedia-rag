from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .providers import LLMProvider


ANSWER_VARIANTS = ["closed_book", "evidence_only", "rag_product"]
SCORE_DIMENSIONS = [
    "correctness",
    "completeness",
    "evidence_support",
    "citation_accuracy",
    "caution",
    "clarity",
    "memory_contamination",
]


@dataclass
class FixedLLMProvider:
    response: str = "这是一个用于测试的固定回答。"

    def answer(self, system_prompt: str, user_prompt: str) -> str:
        del system_prompt, user_prompt
        return self.response


class CachedLLMProvider:
    def __init__(self, provider: LLMProvider, cache_path: Path, namespace: str) -> None:
        self.provider = provider
        self.cache_path = cache_path
        self.namespace = namespace
        self.cache = self._load_cache(cache_path)

    def answer(self, system_prompt: str, user_prompt: str) -> str:
        key = self._cache_key(system_prompt, user_prompt)
        if key in self.cache:
            return self.cache[key]
        response = self.provider.answer(system_prompt, user_prompt)
        self.cache[key] = response
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"key": key, "response": response}, ensure_ascii=False) + "\n")
        return response

    def _cache_key(self, system_prompt: str, user_prompt: str) -> str:
        payload = json.dumps(
            {"namespace": self.namespace, "system": system_prompt, "user": user_prompt},
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _load_cache(cache_path: Path) -> Dict[str, str]:
        if not cache_path.exists():
            return {}
        cache: Dict[str, str] = {}
        for line in cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = item.get("key")
            response = item.get("response")
            if isinstance(key, str) and isinstance(response, str):
                cache[key] = response
        return cache


def evaluate_answer_quality(
    service,
    questions: Iterable[Dict[str, Any]],
    *,
    answer_llm: LLMProvider,
    judge_llm: LLMProvider,
    top_k: int = 6,
    title: str = "RAG vs 通用大模型回答质量评测",
) -> Dict[str, Any]:
    details: List[Dict[str, Any]] = []
    for item in questions:
        question = item["question_zh"]
        scope = item.get("scope", "core")
        response = service.ask(question, scope=scope)
        evidence = response.evidence[:top_k]
        evidence_pack = build_evidence_pack(evidence)
        answers = {
            "closed_book": _generate_closed_book_answer(answer_llm, item),
            "evidence_only": _generate_evidence_only_answer(answer_llm, item, evidence_pack),
            "rag_product": _generate_rag_product_answer(answer_llm, item, evidence_pack),
        }
        judgments = {
            variant: _judge_answer(judge_llm, item, variant, answer, evidence_pack)
            for variant, answer in answers.items()
        }
        details.append(
            {
                "id": item.get("id", ""),
                "question": question,
                "scope": scope,
                "reference_answer": item.get("reference_answer", ""),
                "difficulty": item.get("difficulty", ""),
                "question_type": item.get("question_type", ""),
                "evidence_pack": evidence_pack,
                "answers": answers,
                "judgments": judgments,
            }
        )
    return {
        "title": title,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "total": len(details),
        "aggregate": _aggregate_judgments(details),
        "details": details,
    }


def build_evidence_pack(evidence) -> str:
    lines = []
    for idx, result in enumerate(evidence, 1):
        chunk = result.chunk
        citation = chunk.citation.label()
        text = " ".join(chunk.display_text.split())
        lines.append(
            "[E{}] {} | {} | document_id={} | score={:.3f}\n{}".format(
                idx,
                chunk.citation.title or chunk.document_id,
                citation,
                chunk.document_id,
                result.score.final_score,
                text,
            )
        )
    return "\n\n".join(lines)


def render_answer_eval_markdown(report: Dict[str, Any]) -> str:
    lines = [
        f"# {report.get('title', 'RAG vs 通用大模型回答质量评测')}",
        "",
        "## Metadata",
        "",
        f"- Generated at: `{report.get('generated_at', '')}`",
        f"- Total questions: `{report.get('total', 0)}`",
        "",
        "## Scoring Caveat",
        "",
        "- 自动评分用于第一轮 triage，不能替代人工规则复核。",
        "- `Memory Contamination` 专门标记答案是否加入 evidence pack 之外的规则细节。",
        "- 当检索证据缺失时，RAG 答案应该保守；若强行补全，即使结论正确也要扣分。",
        "",
        "## Dimensions",
        "",
        "| Dimension | 中文含义 |",
        "| --- | --- |",
        "| Correctness | 规则裁定是否正确 |",
        "| Completeness | 是否覆盖关键条件和例外 |",
        "| Evidence Support | 关键结论是否由证据支持 |",
        "| Citation Accuracy | 引用是否支持对应结论 |",
        "| Caution | 证据不足时是否保守 |",
        "| Clarity | 是否直接清晰可执行 |",
        "| Memory Contamination | 是否避免 evidence pack 之外的记忆补完 |",
        "",
        "## Aggregate",
        "",
        "| Variant | Avg Total | Wins | Ties | Losses |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    aggregate = report.get("aggregate", {})
    for variant in ANSWER_VARIANTS:
        row = aggregate.get(variant, {})
        lines.append(
            "| {} | {:.2f} | {} | {} | {} |".format(
                variant,
                float(row.get("average_total", 0.0)),
                row.get("wins", 0),
                row.get("ties", 0),
                row.get("losses", 0),
            )
        )
    lines.extend(
        [
            "",
            "## Dimension Averages",
            "",
            "| Variant | Correctness | Completeness | Evidence | Citation | Caution | Clarity | Memory |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for variant in ANSWER_VARIANTS:
        scores = aggregate.get(variant, {}).get("average_scores", {})
        lines.append(
            "| {} | {:.2f} | {:.2f} | {:.2f} | {:.2f} | {:.2f} | {:.2f} | {:.2f} |".format(
                variant,
                float(scores.get("correctness", 0.0)),
                float(scores.get("completeness", 0.0)),
                float(scores.get("evidence_support", 0.0)),
                float(scores.get("citation_accuracy", 0.0)),
                float(scores.get("caution", 0.0)),
                float(scores.get("clarity", 0.0)),
                float(scores.get("memory_contamination", 0.0)),
            )
        )
    lines.extend(["", "## Questions", ""])
    for detail in report.get("details", []):
        lines.extend(_render_answer_detail(detail))
    return "\n".join(lines).rstrip() + "\n"


def _generate_closed_book_answer(llm: LLMProvider, item: Dict[str, Any]) -> str:
    return llm.answer(
        "你是 D&D 5e 规则问答助手。你不能联网，也没有检索证据。请直接回答，不确定时说明不确定。",
        _question_prompt(item),
    )


def _generate_evidence_only_answer(llm: LLMProvider, item: Dict[str, Any], evidence_pack: str) -> str:
    return llm.answer(
        "你是 D&D 5e 规则问答助手。只能使用用户提供的 evidence pack；不要使用外部知识。",
        f"{_question_prompt(item)}\n\nEvidence Pack:\n{evidence_pack}",
    )


def _generate_rag_product_answer(llm: LLMProvider, item: Dict[str, Any], evidence_pack: str) -> str:
    return llm.answer(
        "你是中文 D&D 规则百科 RAG 产品的回答器。只能基于 evidence pack 回答。"
        "输出结构：结论、依据、适用条件、容易误判、引用。每个关键结论必须带 [E编号]。",
        f"{_question_prompt(item)}\n\nEvidence Pack:\n{evidence_pack}",
    )


def _judge_answer(
    judge_llm: LLMProvider,
    item: Dict[str, Any],
    variant: str,
    answer: str,
    evidence_pack: str,
) -> Dict[str, Any]:
    prompt = {
        "variant": variant,
        "question": item.get("question_zh", ""),
        "reference_answer": item.get("reference_answer", ""),
        "must_include": item.get("must_include", []),
        "must_not_include": item.get("must_not_include", []),
        "evidence_pack": evidence_pack,
        "answer": answer,
        "instructions": (
            "Return JSON only with keys scores,total,verdict,reasons. "
            "Score each dimension 0-2: correctness, completeness, evidence_support, citation_accuracy, "
            "caution, clarity, memory_contamination. total is the sum. verdict must be win, tie, or loss. "
            "For evidence_only and rag_product, evidence_support=0 if any key claim is not supported by the evidence pack, "
            "citation_accuracy=0 if citations point to evidence that does not support the cited claim, and "
            "memory_contamination=0 if the answer adds outside rule details not present in the evidence pack, even if true in D&D. "
            "For closed_book, score correctness against the reference answer, but memory_contamination should reflect whether "
            "the answer gives unverifiable specifics that cannot be traced to supplied evidence. "
            "Reasons must be 1-3 short Chinese strings and must mention unsupported memory use when present."
        ),
    }
    raw = judge_llm.answer(
        "你是严格的 D&D 5e 回答质量评审。只输出 JSON，不要输出 Markdown。",
        json.dumps(prompt, ensure_ascii=False),
    )
    return _parse_judgment(raw)


def _parse_judgment(raw: str) -> Dict[str, Any]:
    data = _loads_json_object(raw)
    scores = _normalize_scores_object(data.get("scores") or {})
    normalized_scores = {
        dimension: _clamp_score(scores.get(dimension, 0))
        for dimension in SCORE_DIMENSIONS
    }
    total = int(data.get("total", sum(normalized_scores.values())) or sum(normalized_scores.values()))
    verdict = data.get("verdict", "tie")
    if verdict not in {"win", "tie", "loss"}:
        verdict = "tie"
    reasons = data.get("reasons") or data.get("reason") or []
    if isinstance(reasons, str):
        reasons = [reasons]
    return {
        "scores": normalized_scores,
        "total": total,
        "verdict": verdict,
        "reasons": [str(reason) for reason in reasons],
    }


def parse_judgment_for_test(raw: str) -> Dict[str, Any]:
    return _parse_judgment(raw)


def _normalize_scores_object(scores: Any) -> Dict[str, Any]:
    if isinstance(scores, dict):
        return scores
    if not isinstance(scores, list):
        return {}
    normalized = {}
    for idx, item in enumerate(scores):
        if isinstance(item, dict):
            dimension = item.get("dimension") or item.get("name") or item.get("key")
            score = item.get("score") if "score" in item else item.get("value")
            if dimension in SCORE_DIMENSIONS:
                normalized[dimension] = score
        elif idx < len(SCORE_DIMENSIONS):
            normalized[SCORE_DIMENSIONS[idx]] = item
    return normalized


def _loads_json_object(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {}
    return data if isinstance(data, dict) else {}


def _clamp_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 0
    return max(0, min(2, score))


def _aggregate_judgments(details: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    aggregate: Dict[str, Dict[str, float]] = {}
    for variant in ANSWER_VARIANTS:
        totals = [detail["judgments"][variant]["total"] for detail in details]
        verdicts = [detail["judgments"][variant]["verdict"] for detail in details]
        average_scores = {}
        for dimension in SCORE_DIMENSIONS:
            values = [detail["judgments"][variant]["scores"].get(dimension, 0) for detail in details]
            average_scores[dimension] = sum(values) / len(values) if values else 0.0
        aggregate[variant] = {
            "average_total": sum(totals) / len(totals) if totals else 0.0,
            "average_scores": average_scores,
            "wins": verdicts.count("win"),
            "ties": verdicts.count("tie"),
            "losses": verdicts.count("loss"),
        }
    return aggregate


def _render_answer_detail(detail: Dict[str, Any]) -> List[str]:
    lines = [
        f"### {detail.get('id', '')}",
        "",
        f"- 问题：{detail.get('question', '')}",
        f"- 范围：`{detail.get('scope', '')}`",
        f"- 参考答案：{detail.get('reference_answer', '')}",
        "",
        "#### Scores",
        "",
        "| Variant | Total | Verdict | Reasons |",
        "| --- | ---: | --- | --- |",
    ]
    for variant in ANSWER_VARIANTS:
        judgment = detail.get("judgments", {}).get(variant, {})
        scores = judgment.get("scores", {})
        compact_scores = "C/M/E/Cit/Cau/Clr/Mem = {}/{}/{}/{}/{}/{}/{}".format(
            scores.get("correctness", 0),
            scores.get("completeness", 0),
            scores.get("evidence_support", 0),
            scores.get("citation_accuracy", 0),
            scores.get("caution", 0),
            scores.get("clarity", 0),
            scores.get("memory_contamination", 0),
        )
        lines.append(
            "| {} | {} | {} | {} |".format(
                variant,
                judgment.get("total", 0),
                judgment.get("verdict", ""),
                _md(compact_scores + "；" + "；".join(judgment.get("reasons") or [])),
            )
        )
    lines.extend(["", "#### Answers", ""])
    for variant in ANSWER_VARIANTS:
        lines.extend([f"**{variant}**", "", _truncate(detail.get("answers", {}).get(variant, ""), 900), ""])
    lines.extend(["#### Evidence Pack", "", _truncate(detail.get("evidence_pack", ""), 1000), ""])
    return lines


def _question_prompt(item: Dict[str, Any]) -> str:
    return "问题：{}\n范围：{}\n请用中文回答。".format(item.get("question_zh", ""), item.get("scope", "core"))


def _truncate(text: str, limit: int) -> str:
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
