from __future__ import annotations

from typing import Any, Dict, Iterable, List


def evaluate_retrieval(service, questions: Iterable[Dict[str, Any]], top_k: int = 8) -> Dict[str, Any]:
    total = 0
    hits = 0
    reciprocal_rank_sum = 0.0
    details: List[Dict[str, Any]] = []
    for item in questions:
        total += 1
        question = item["question_zh"]
        scope = item.get("scope", "core")
        response = service.ask(question, scope=scope)
        expected_docs = set(item.get("expected_documents") or [])
        expected_terms = set(item.get("expected_terms") or [])
        rank = _first_match_rank(response.evidence[:top_k], expected_docs, expected_terms)
        hit = rank is not None
        if hit:
            hits += 1
            reciprocal_rank_sum += 1.0 / rank
        details.append(
            {
                "id": item.get("id", f"q{total}"),
                "question": question,
                "hit": hit,
                "rank": rank,
                "top_titles": [result.chunk.citation.title for result in response.evidence[:top_k]],
            }
        )
    return {
        "total": total,
        "recall_at_k": hits / total if total else 0.0,
        "mrr": reciprocal_rank_sum / total if total else 0.0,
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

