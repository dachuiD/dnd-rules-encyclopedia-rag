#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dnd_rag.adapters import FiveEToolsCnAdapter
from dnd_rag.answer_eval import CachedLLMProvider, FixedLLMProvider, evaluate_answer_quality, render_answer_eval_markdown
from dnd_rag.audit import audit_source_tree
from dnd_rag.chunking import build_chunks
from dnd_rag.embedding_index import build_embedding_index, filter_fresh_rows, load_embedding_index, text_hash
from dnd_rag.eval import (
    evaluate_retrieval,
    render_retrieval_eval_comparison_summary_markdown,
    render_retrieval_eval_markdown,
    render_retrieval_eval_summary_markdown,
)
from dnd_rag.providers import DashScopeEmbeddingProvider, DeepSeekLLMProvider
from dnd_rag.service import RagService
from dnd_rag.settings import load_env_file


def main() -> None:
    load_env_file(ROOT / ".env")

    parser = argparse.ArgumentParser(description="D&D rules encyclopedia RAG utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("audit", help="Generate a data audit report")
    audit.add_argument("--data-dir", default="sample_data/5etools")
    audit.add_argument("--out", default="reports/data-audit.md")

    ask = sub.add_parser("ask", help="Ask a local RAG question")
    ask.add_argument("question")
    ask.add_argument("--data-dir", default="sample_data/5etools")
    ask.add_argument("--scope", choices=["core", "full"], default="core")

    evaluate = sub.add_parser("eval", help="Run retrieval eval")
    evaluate.add_argument("--data-dir", default="sample_data/5etools")
    evaluate.add_argument("--questions", default="eval/golden_sample.json")
    evaluate.add_argument("--out", default="reports/retrieval-eval.json")
    evaluate.add_argument("--embedding-index")

    eval_report = sub.add_parser("eval-report", help="Run retrieval eval and write an auditable Markdown report")
    eval_report.add_argument("--data-dir", default="sample_data/5etools")
    eval_report.add_argument("--questions", default="eval/golden_sample.json")
    eval_report.add_argument("--out", default="docs/evaluations/retrieval-eval.md")
    eval_report.add_argument("--embedding-index")
    eval_report.add_argument("--title", default="Retrieval Eval")
    eval_report.add_argument("--evidence-limit", type=int, default=3)

    eval_summary = sub.add_parser("eval-summary", help="Run retrieval eval and write a compact review Markdown report")
    eval_summary.add_argument("--data-dir", default="sample_data/5etools")
    eval_summary.add_argument("--questions", default="eval/golden_sample.json")
    eval_summary.add_argument("--out", default="docs/evaluations/retrieval-eval-summary.md")
    eval_summary.add_argument("--embedding-index")
    eval_summary.add_argument("--title", default="Retrieval Eval Summary")
    eval_summary.add_argument("--compare-baseline", action="store_true")

    answer_eval = sub.add_parser("answer-eval", help="Run answer-quality A/B/C eval with automatic scoring")
    answer_eval.add_argument("--data-dir", default="sample_data/5etools")
    answer_eval.add_argument("--questions", default="eval/golden_sample.json")
    answer_eval.add_argument("--out", default="docs/evaluations/answer-eval-small-sample.md")
    answer_eval.add_argument("--embedding-index")
    answer_eval.add_argument("--limit", type=int, default=8)
    answer_eval.add_argument("--top-k", type=int, default=6)
    answer_eval.add_argument("--cache", default="reports/answer-eval-cache.jsonl")
    answer_eval.add_argument("--mock-llm", action="store_true")
    answer_eval.add_argument("--title", default="RAG vs 通用大模型回答质量评测")

    embed = sub.add_parser("embed-sample", help="Build a small DashScope embedding index")
    embed.add_argument("--data-dir", default="sample_data/5etools")
    embed.add_argument("--out", default="storage/embedding-index/sample.jsonl")
    embed.add_argument("--scope", choices=["core", "full"], default="core")
    embed.add_argument("--limit", type=int, default=300)
    embed.add_argument("--batch-size", type=int, default=20)
    embed.add_argument("--max-segment-chars", type=int, default=4000)
    embed.add_argument("--model", default=os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4"))
    embed.add_argument("--dimensions", type=int, default=int(os.getenv("DASHSCOPE_EMBEDDING_DIMENSIONS", "1024")))

    args = parser.parse_args()
    if args.command == "audit":
        report = audit_source_tree(Path(args.data_dir))
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report.to_markdown(), encoding="utf-8")
        print(f"Wrote {out}")
    elif args.command == "ask":
        service = RagService.from_adapter(FiveEToolsCnAdapter(Path(args.data_dir)))
        response = service.ask(args.question, scope=args.scope)
        print(response.answer)
        print("\nCitations:")
        for citation in response.citations:
            print(f"- {citation['label']} ({citation['score']})")
    elif args.command == "eval":
        adapter = FiveEToolsCnAdapter(Path(args.data_dir))
        service = _service_from_adapter(adapter, embedding_index=Path(args.embedding_index) if args.embedding_index else None)
        questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
        report = evaluate_retrieval(service, questions)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {out}")
    elif args.command == "eval-report":
        adapter = FiveEToolsCnAdapter(Path(args.data_dir))
        questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
        if args.embedding_index:
            baseline_service = _service_from_adapter(adapter)
            baseline_report = evaluate_retrieval(baseline_service, questions)
            embedding_service = _service_from_adapter(adapter, embedding_index=Path(args.embedding_index))
            report = evaluate_retrieval(embedding_service, questions)
        else:
            baseline_report = None
            service = _service_from_adapter(adapter)
            report = evaluate_retrieval(service, questions)
        markdown = render_retrieval_eval_markdown(
            report,
            title=args.title,
            dataset_path=args.questions,
            data_dir=args.data_dir,
            embedding_index=args.embedding_index or "",
            baseline_report=baseline_report,
            baseline_label="Token Hybrid",
            report_label="Embedding Hybrid",
            evidence_limit=args.evidence_limit,
        )
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown, encoding="utf-8")
        print(f"Wrote {out}")
    elif args.command == "eval-summary":
        adapter = FiveEToolsCnAdapter(Path(args.data_dir))
        questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
        if args.compare_baseline:
            baseline_service = _service_from_adapter(adapter)
            baseline_report = evaluate_retrieval(baseline_service, questions)
            embedding_service = _service_from_adapter(
                adapter,
                embedding_index=Path(args.embedding_index) if args.embedding_index else None,
            )
            report = evaluate_retrieval(embedding_service, questions)
            markdown = render_retrieval_eval_comparison_summary_markdown(
                baseline_report,
                report,
                title=args.title,
                dataset_path=args.questions,
                data_dir=args.data_dir,
                embedding_index=args.embedding_index or "",
                baseline_label="Token Hybrid",
                embedding_label="Embedding Hybrid",
            )
        else:
            service = _service_from_adapter(adapter, embedding_index=Path(args.embedding_index) if args.embedding_index else None)
            report = evaluate_retrieval(service, questions)
            markdown = render_retrieval_eval_summary_markdown(
                report,
                title=args.title,
                dataset_path=args.questions,
                data_dir=args.data_dir,
                embedding_index=args.embedding_index or "",
                report_label="Embedding Hybrid" if args.embedding_index else "Token Hybrid",
            )
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown, encoding="utf-8")
        print(f"Wrote {out}")
    elif args.command == "answer-eval":
        adapter = FiveEToolsCnAdapter(Path(args.data_dir))
        service = _service_from_adapter(adapter, embedding_index=Path(args.embedding_index) if args.embedding_index else None)
        questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
        if args.limit > 0:
            questions = questions[: args.limit]
        if args.mock_llm:
            answer_llm = FixedLLMProvider("这是 mock 回答，用于测试 CLI，不代表真实模型表现。")
            judge_llm = FixedLLMProvider(
                '{"scores":{"correctness":1,"completeness":1,"evidence_support":1,'
                '"citation_accuracy":1,"caution":1,"clarity":1,"memory_contamination":1},'
                '"total":7,"verdict":"tie","reasons":["mock judge"]}'
            )
        else:
            answer_llm = CachedLLMProvider(
                DeepSeekLLMProvider(),
                Path(args.cache),
                namespace="answer-eval-answer",
            )
            judge_llm = CachedLLMProvider(
                DeepSeekLLMProvider(),
                Path(args.cache),
                namespace="answer-eval-judge-v2",
            )
        report = evaluate_answer_quality(
            service,
            questions,
            answer_llm=answer_llm,
            judge_llm=judge_llm,
            top_k=args.top_k,
            title=args.title,
        )
        markdown = render_answer_eval_markdown(report)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown, encoding="utf-8")
        print(f"Wrote {out}")
    elif args.command == "embed-sample":
        adapter = FiveEToolsCnAdapter(Path(args.data_dir))
        documents = adapter.load_documents()
        chunks = [chunk for doc in documents for chunk in build_chunks(doc)]
        chunks = _filter_chunks_for_scope(chunks, args.scope)
        provider = DashScopeEmbeddingProvider(model=args.model, dimensions=args.dimensions)
        report = build_embedding_index(
            chunks,
            provider=provider,
            out_path=Path(args.out),
            limit=args.limit,
            batch_size=args.batch_size,
            model=provider.model,
            dimensions=provider.dimensions,
            max_segment_chars=args.max_segment_chars,
        )
        print(json.dumps(report.__dict__, ensure_ascii=False, indent=2))


def _service_from_adapter(adapter: FiveEToolsCnAdapter, embedding_index: Path | None = None) -> RagService:
    documents = adapter.load_documents()
    chunks = [chunk for doc in documents for chunk in build_chunks(doc)]
    if not embedding_index:
        return RagService(documents, chunks)
    rows = load_embedding_index(embedding_index)
    if not rows:
        return RagService(documents, chunks)
    model = rows[0].model
    dimensions = rows[0].dimensions
    expected_hashes = {chunk.id: text_hash(chunk.embedding_text) for chunk in chunks}
    fresh_rows = filter_fresh_rows(rows, expected_hashes, model=model, dimensions=dimensions)
    chunk_embeddings = {chunk_id: row.embedding for chunk_id, row in fresh_rows.items()}
    provider = DashScopeEmbeddingProvider(model=model, dimensions=dimensions)
    return RagService(documents, chunks, chunk_embeddings=chunk_embeddings, embedding_provider=provider)


def _filter_chunks_for_scope(chunks, scope: str):
    if scope == "core":
        return [chunk for chunk in chunks if chunk.search_scope == "core"]
    return chunks


if __name__ == "__main__":
    main()
