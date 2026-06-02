#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dnd_rag.adapters import FiveEToolsCnAdapter
from dnd_rag.audit import audit_source_tree
from dnd_rag.eval import evaluate_retrieval
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
        service = RagService.from_adapter(FiveEToolsCnAdapter(Path(args.data_dir)))
        questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
        report = evaluate_retrieval(service, questions)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
