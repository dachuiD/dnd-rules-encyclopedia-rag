from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List


def evaluate_retrieval(service, questions: Iterable[Dict[str, Any]], top_k: int = 8) -> Dict[str, Any]:
    total = 0
    hits = 0
    primary_questions = 0
    primary_hits = 0
    reciprocal_rank_sum = 0.0
    details: List[Dict[str, Any]] = []
    for item in questions:
        total += 1
        question = item["question_zh"]
        scope = item.get("scope", "core")
        response = service.ask(question, scope=scope)
        expected_docs = set(item.get("expected_documents") or [])
        expected_terms = set(item.get("expected_terms") or [])
        expected_primary_terms = set(item.get("expected_primary_terms") or [])
        rank = _first_match_rank(response.evidence[:top_k], expected_docs, expected_terms)
        hit = rank is not None
        primary_hit = _top_result_matches(response.evidence[:1], expected_primary_terms)
        if expected_primary_terms:
            primary_questions += 1
            if primary_hit:
                primary_hits += 1
        if hit:
            hits += 1
            reciprocal_rank_sum += 1.0 / rank
        details.append(
            {
                "id": item.get("id", f"q{total}"),
                "question": question,
                "scope": scope,
                "reference_answer": item.get("reference_answer", ""),
                "expected_documents": list(item.get("expected_documents") or []),
                "expected_terms": list(item.get("expected_terms") or []),
                "expected_primary_terms": list(item.get("expected_primary_terms") or []),
                "must_include": list(item.get("must_include") or []),
                "must_not_include": list(item.get("must_not_include") or []),
                "difficulty": item.get("difficulty", ""),
                "question_type": item.get("question_type", ""),
                "hit": hit,
                "rank": rank,
                "primary_hit_at_1": primary_hit if expected_primary_terms else None,
                "top_titles": [result.chunk.citation.title for result in response.evidence[:top_k]],
                "top_evidence": [_evidence_detail(idx, result) for idx, result in enumerate(response.evidence[:top_k], 1)],
            }
        )
    return {
        "total": total,
        "top_k": top_k,
        "recall_at_k": hits / total if total else 0.0,
        "mrr": reciprocal_rank_sum / total if total else 0.0,
        "primary_hit_at_1": primary_hits / primary_questions if primary_questions else None,
        "details": details,
    }


def _first_match_rank(results, expected_docs: set, expected_terms: set) -> int | None:
    for idx, result in enumerate(results, 1):
        haystack = " ".join(
            [
                result.chunk.document_id,
                result.chunk.citation.title or "",
                result.chunk.text,
                result.chunk.embedding_text,
            ]
        )
        if expected_docs and result.chunk.document_id in expected_docs:
            return idx
        if expected_terms and any(term in haystack for term in expected_terms):
            return idx
    return None


def _top_result_matches(results, expected_terms: set) -> bool:
    if not results or not expected_terms:
        return False
    top = results[0]
    haystack = " ".join(
        [
            top.chunk.document_id,
            top.chunk.citation.title or "",
            top.chunk.text,
            top.chunk.embedding_text,
        ]
    )
    return any(term in haystack for term in expected_terms)


def _evidence_detail(rank: int, result) -> Dict[str, Any]:
    chunk = result.chunk
    score = result.score
    return {
        "rank": rank,
        "chunk_id": chunk.id,
        "document_id": chunk.document_id,
        "title": chunk.citation.title or "",
        "citation": chunk.citation.label(),
        "source_id": chunk.source_id,
        "page": chunk.citation.page,
        "category": chunk.category,
        "chunk_type": chunk.chunk_type,
        "chunk_level": chunk.chunk_level,
        "title_path": chunk.title_path,
        "score_parts": {
            "dense": round(score.dense_score, 4),
            "lexical": round(score.lexical_score, 4),
            "alias": round(score.alias_score, 4),
            "title": round(score.title_score, 4),
            "source": round(score.source_score, 4),
            "structure": round(score.structure_score, 4),
            "final": round(score.final_score, 4),
        },
        "reasons": list(score.reasons),
        "display_text": _truncate(chunk.display_text, 420),
    }


def render_retrieval_eval_markdown(
    report: Dict[str, Any],
    *,
    title: str = "Retrieval Evaluation Report",
    dataset_path: str = "",
    data_dir: str = "",
    embedding_index: str = "",
    baseline_report: Dict[str, Any] | None = None,
    baseline_label: str = "Baseline",
    report_label: str = "Embedding",
    evidence_limit: int = 3,
) -> str:
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    lines = [
        f"# {title}",
        "",
        "## Run Metadata",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Dataset: `{dataset_path or 'unknown'}`",
        f"- Data dir: `{data_dir or 'unknown'}`",
        f"- Embedding index: `{embedding_index or 'not used'}`",
        "",
        "## Metrics",
        "",
    ]
    if baseline_report:
        lines.extend(_comparison_metrics_table(baseline_report, report, baseline_label, report_label))
    else:
        lines.extend(_single_metrics_table(report, report_label))
    lines.extend(
        [
            "",
            "## Reading Notes",
            "",
            "- 分数是 chunk 级证据分，不是整本书或整篇来源的全局可信度。",
            "- 同一来源出现不同分数是正常现象：parent chunk、child chunk、结构类型、关键词重合、语义分和父子扩展倍率都可能不同。",
            "- `D/L/A/T/S/C` 分别代表 dense、lexical、alias、title、source、structure，用于解释最终分的组成。",
            "",
            "## Questions And Evidence",
            "",
        ]
    )

    baseline_details = {detail["id"]: detail for detail in baseline_report.get("details", [])} if baseline_report else {}
    for detail in report.get("details", []):
        lines.extend(_render_question_detail(detail, evidence_limit, report_label))
        if baseline_report:
            baseline_detail = baseline_details.get(detail["id"])
            if baseline_detail:
                lines.extend(_render_evidence_table(baseline_detail, evidence_limit, f"{baseline_label} Top 证据"))
                lines.extend(_render_evidence_table(detail, evidence_limit, f"{report_label} Top 证据"))
                lines.extend(["", _interpret_comparison(baseline_detail, detail, baseline_label, report_label), ""])
            else:
                lines.extend(_render_evidence_table(detail, evidence_limit, f"{report_label} Top 证据"))
        else:
            lines.extend(_render_evidence_table(detail, evidence_limit, "Top 证据"))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_retrieval_eval_summary_markdown(
    report: Dict[str, Any],
    *,
    title: str = "Retrieval Evaluation Summary",
    dataset_path: str = "",
    data_dir: str = "",
    embedding_index: str = "",
    report_label: str = "Embedding Hybrid",
) -> str:
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    top_k = report.get("top_k", 8)
    details = report.get("details", [])
    lines = [
        f"# {title}",
        "",
        "## Metadata",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Dataset: `{dataset_path or 'unknown'}`",
        f"- Data dir: `{data_dir or 'unknown'}`",
        f"- Embedding index: `{embedding_index or 'not used'}`",
        "",
        "## Metrics",
        "",
        "| Run | Total | Recall@{} | MRR | Primary@1 |".format(top_k),
        "| --- | ---: | ---: | ---: | ---: |",
        "| {} | {} | {} | {} | {} |".format(
            _md(report_label),
            report.get("total", 0),
            _pct(report.get("recall_at_k")),
            _num(report.get("mrr")),
            _metric(report.get("primary_hit_at_1")),
        ),
        "",
        "## Review Table",
        "",
        "| ID | 问题 | 参考答案 | Hit | Rank | Primary@1 | Top1 | Top3 |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for detail in details:
        evidence = detail.get("top_evidence", [])
        top1 = _compact_evidence(evidence[0]) if evidence else "-"
        top3 = "<br>".join(_compact_evidence(item) for item in evidence[:3]) if evidence else "-"
        primary = detail.get("primary_hit_at_1")
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} | {} |".format(
                _md(detail.get("id", "")),
                _md(detail.get("question", "")),
                _md(_truncate(detail.get("reference_answer", ""), 120)),
                "Y" if detail.get("hit") else "N",
                detail.get("rank") or "-",
                "-" if primary is None else ("Y" if primary else "N"),
                _md(top1),
                _md(top3),
            )
        )
    lines.extend(["", "## Needs Review", ""])
    review_items = [detail for detail in details if _needs_review(detail)]
    if not review_items:
        lines.append("- 暂无强制复核项。")
    for detail in review_items:
        evidence = detail.get("top_evidence", [])
        top1 = _compact_evidence(evidence[0]) if evidence else "-"
        reasons = []
        if not detail.get("hit"):
            reasons.append("未命中期望证据")
        if detail.get("primary_hit_at_1") is False:
            reasons.append("Top1 不是核心证据")
        rank = detail.get("rank")
        if rank and rank > 3:
            reasons.append(f"首个命中排在第 {rank}")
        lines.append(
            f"- `{detail.get('id', '')}`：{'；'.join(reasons)}。Top1: {top1}"
        )
    return "\n".join(lines).rstrip() + "\n"


def render_retrieval_eval_comparison_summary_markdown(
    baseline_report: Dict[str, Any],
    embedding_report: Dict[str, Any],
    *,
    title: str = "Retrieval Evaluation Comparison",
    dataset_path: str = "",
    data_dir: str = "",
    embedding_index: str = "",
    baseline_label: str = "Token Hybrid",
    embedding_label: str = "Embedding Hybrid",
) -> str:
    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    top_k = embedding_report.get("top_k", baseline_report.get("top_k", 8))
    lines = [
        f"# {title}",
        "",
        "## Metadata",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Dataset: `{dataset_path or 'unknown'}`",
        f"- Data dir: `{data_dir or 'unknown'}`",
        f"- Embedding index: `{embedding_index or 'not used'}`",
        "",
        "## Metrics",
        "",
        "| Run | Total | Recall@{} | MRR | Primary@1 |".format(top_k),
        "| --- | ---: | ---: | ---: | ---: |",
        _summary_metric_row(baseline_label, baseline_report),
        _summary_metric_row(embedding_label, embedding_report),
        "| Delta | - | {} | {} | {} |".format(
            _delta_pct(baseline_report.get("recall_at_k"), embedding_report.get("recall_at_k")),
            _delta_num(baseline_report.get("mrr"), embedding_report.get("mrr")),
            _delta_num(baseline_report.get("primary_hit_at_1"), embedding_report.get("primary_hit_at_1")),
        ),
        "",
        "## Changed Questions",
        "",
        "| ID | 问题 | 变化 | Token Top1 | Embedding Top1 |",
        "| --- | --- | --- | --- | --- |",
    ]
    baseline_by_id = {detail.get("id"): detail for detail in baseline_report.get("details", [])}
    embedding_details = embedding_report.get("details", [])
    changed_rows = []
    for detail in embedding_details:
        baseline = baseline_by_id.get(detail.get("id"))
        if not baseline:
            continue
        change = _question_change_label(baseline, detail)
        if change == "不变":
            continue
        changed_rows.append((detail, baseline, change))
        lines.append(
            "| {} | {} | {} | {} | {} |".format(
                _md(detail.get("id", "")),
                _md(detail.get("question", "")),
                change,
                _md(_top1(baseline)),
                _md(_top1(detail)),
            )
        )
    if not changed_rows:
        lines.append("| - | - | 无明显变化 | - | - |")

    lines.extend(["", "## Still Needs Review", ""])
    review_items = [detail for detail in embedding_details if _needs_review(detail)]
    if not review_items:
        lines.append("- 暂无强制复核项。")
    for detail in review_items:
        baseline = baseline_by_id.get(detail.get("id"), {})
        lines.append(
            "- `{}`：Embedding 仍需复核。Token Top1: {}；Embedding Top1: {}".format(
                detail.get("id", ""),
                _top1(baseline),
                _top1(detail),
            )
        )
    return "\n".join(lines).rstrip() + "\n"


def _single_metrics_table(report: Dict[str, Any], label: str) -> List[str]:
    top_k = report.get("top_k", 8)
    return [
        "| Run | Total | Recall@{} | MRR | Primary@1 |".format(top_k),
        "| --- | ---: | ---: | ---: | ---: |",
        "| {} | {} | {} | {} | {} |".format(
            _md(label),
            report.get("total", 0),
            _pct(report.get("recall_at_k")),
            _num(report.get("mrr")),
            _metric(report.get("primary_hit_at_1")),
        ),
    ]


def _comparison_metrics_table(
    baseline: Dict[str, Any],
    report: Dict[str, Any],
    baseline_label: str,
    report_label: str,
) -> List[str]:
    top_k = report.get("top_k", baseline.get("top_k", 8))
    return [
        "| Run | Total | Recall@{} | MRR | Primary@1 |".format(top_k),
        "| --- | ---: | ---: | ---: | ---: |",
        "| {} | {} | {} | {} | {} |".format(
            _md(baseline_label),
            baseline.get("total", 0),
            _pct(baseline.get("recall_at_k")),
            _num(baseline.get("mrr")),
            _metric(baseline.get("primary_hit_at_1")),
        ),
        "| {} | {} | {} | {} | {} |".format(
            _md(report_label),
            report.get("total", 0),
            _pct(report.get("recall_at_k")),
            _num(report.get("mrr")),
            _metric(report.get("primary_hit_at_1")),
        ),
    ]


def _render_question_detail(detail: Dict[str, Any], evidence_limit: int, label: str) -> List[str]:
    del evidence_limit, label
    rank = detail.get("rank")
    primary = detail.get("primary_hit_at_1")
    status_bits = [
        "命中" if detail.get("hit") else "未命中",
        f"首个命中排名：{rank}" if rank else "首个命中排名：-",
    ]
    if primary is not None:
        status_bits.append(f"Primary@1：{'是' if primary else '否'}")
    return [
        f"### {detail.get('id', '')}",
        "",
        f"- 问题：{detail.get('question', '')}",
        f"- 范围/类型/难度：`{detail.get('scope', '')}` / `{detail.get('question_type', '')}` / `{detail.get('difficulty', '')}`",
        f"- 参考答案：{detail.get('reference_answer') or '未填写'}",
        f"- 期望命中词：{_join(detail.get('expected_terms'))}",
        f"- 核心命中词：{_join(detail.get('expected_primary_terms'))}",
        f"- 期望文档：{_join(detail.get('expected_documents'))}",
        f"- 必须包含：{_join(detail.get('must_include'))}",
        f"- 禁止误答点：{_join(detail.get('must_not_include'))}",
        f"- 检索判定：{'；'.join(status_bits)}",
        "",
    ]


def _render_evidence_table(detail: Dict[str, Any], evidence_limit: int, heading: str) -> List[str]:
    lines = [
        f"#### {heading}",
        "",
        "| Rank | 条目 | 来源 | Chunk | 最终分 | 分数组成 | 命中原因 | 摘要 |",
        "| ---: | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for item in detail.get("top_evidence", [])[:evidence_limit]:
        scores = item.get("score_parts", {})
        parts = ", ".join(
            [
                f"D {scores.get('dense', 0):.2f}",
                f"L {scores.get('lexical', 0):.2f}",
                f"A {scores.get('alias', 0):.2f}",
                f"T {scores.get('title', 0):.2f}",
                f"S {scores.get('source', 0):.2f}",
                f"C {scores.get('structure', 0):.2f}",
            ]
        )
        lines.append(
            "| {} | {} | {} | {} / {} | {:.4f} | {} | {} | {} |".format(
                item.get("rank", ""),
                _md(item.get("title") or item.get("document_id", "")),
                _md(item.get("citation") or item.get("source_id", "")),
                _md(item.get("chunk_level", "")),
                _md(item.get("chunk_type", "")),
                scores.get("final", 0),
                _md(parts),
                _md("；".join(item.get("reasons") or [])),
                _md(item.get("display_text", "")),
            )
        )
    if not detail.get("top_evidence"):
        lines.append("| - | - | - | - | - | - | - | - |")
    return lines


def _interpret_comparison(
    baseline_detail: Dict[str, Any],
    detail: Dict[str, Any],
    baseline_label: str,
    report_label: str,
) -> str:
    base_primary = baseline_detail.get("primary_hit_at_1")
    new_primary = detail.get("primary_hit_at_1")
    base_rank = baseline_detail.get("rank")
    new_rank = detail.get("rank")
    if base_primary is False and new_primary is True:
        return f"解释：`{report_label}` 将核心证据推到 Top 1，是相对 `{baseline_label}` 的明确改进。"
    if base_primary is True and new_primary is False:
        return f"解释：`{report_label}` 的 Top 1 主证据退步，需要检查权重或 query embedding。"
    if base_rank and new_rank and new_rank < base_rank:
        return f"解释：`{report_label}` 的首个命中排名从 {base_rank} 提升到 {new_rank}。"
    if base_rank and new_rank and new_rank > base_rank:
        return f"解释：`{report_label}` 的首个命中排名从 {base_rank} 下降到 {new_rank}，需要复盘。"
    return "解释：两组检索在该题上的命中状态基本一致，差异主要看 Top 证据排序和噪声。"


def _compact_evidence(item: Dict[str, Any]) -> str:
    scores = item.get("score_parts", {})
    title = item.get("title") or item.get("document_id", "")
    citation = item.get("citation") or item.get("source_id", "")
    final = scores.get("final", 0)
    return f"{title} ({citation}, {final:.3f})"


def _summary_metric_row(label: str, report: Dict[str, Any]) -> str:
    return "| {} | {} | {} | {} | {} |".format(
        _md(label),
        report.get("total", 0),
        _pct(report.get("recall_at_k")),
        _num(report.get("mrr")),
        _metric(report.get("primary_hit_at_1")),
    )


def _delta_pct(before, after) -> str:
    if before is None or after is None:
        return "-"
    return f"{after - before:+.2%}"


def _delta_num(before, after) -> str:
    if before is None or after is None:
        return "-"
    return f"{after - before:+.4f}"


def _top1(detail: Dict[str, Any]) -> str:
    evidence = detail.get("top_evidence", [])
    return _compact_evidence(evidence[0]) if evidence else "-"


def _question_change_label(baseline: Dict[str, Any], detail: Dict[str, Any]) -> str:
    base_primary = baseline.get("primary_hit_at_1")
    new_primary = detail.get("primary_hit_at_1")
    if base_primary is False and new_primary is True:
        return "改善：Top1 命中核心证据"
    if base_primary is True and new_primary is False:
        return "退步：Top1 丢失核心证据"
    base_hit = baseline.get("hit")
    new_hit = detail.get("hit")
    if not base_hit and new_hit:
        return "改善：从未命中到命中"
    if base_hit and not new_hit:
        return "退步：从命中到未命中"
    base_rank = baseline.get("rank")
    new_rank = detail.get("rank")
    if base_rank and new_rank and new_rank < base_rank:
        return f"改善：Rank {base_rank} -> {new_rank}"
    if base_rank and new_rank and new_rank > base_rank:
        return f"退步：Rank {base_rank} -> {new_rank}"
    if _top1(baseline) != _top1(detail):
        return "变化：Top1 证据不同"
    return "不变"


def _needs_review(detail: Dict[str, Any]) -> bool:
    if not detail.get("hit"):
        return True
    if detail.get("primary_hit_at_1") is False:
        return True
    rank = detail.get("rank")
    return bool(rank and rank > 3)


def _join(items) -> str:
    items = [str(item) for item in (items or [])]
    return "、".join(items) if items else "-"


def _pct(value) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.2f}%"


def _num(value) -> str:
    if value is None:
        return "-"
    return f"{value:.4f}"


def _metric(value) -> str:
    if value is None:
        return "-"
    return _num(value)


def _truncate(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _md(value: Any) -> str:
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")
