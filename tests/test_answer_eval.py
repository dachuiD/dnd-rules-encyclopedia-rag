import unittest
import tempfile
from pathlib import Path

from dnd_rag.answer_eval import (
    CachedLLMProvider,
    FixedLLMProvider,
    evaluate_answer_quality,
    parse_judgment_for_test,
    render_answer_eval_markdown,
)
from dnd_rag.service import RagService


class AnswerEvalTests(unittest.TestCase):
    def test_answer_quality_eval_generates_three_variants_and_scores_them(self):
        service = RagService.from_sample_data()
        questions = [
            {
                "id": "q1",
                "question_zh": "隐身的人攻击有优势吗？",
                "scope": "core",
                "reference_answer": "通常有优势，但不是自动命中。",
                "expected_terms": ["隐形", "优势"],
                "must_include": ["优势"],
                "must_not_include": ["自动命中"],
                "difficulty": "easy",
                "question_type": "ruling",
            }
        ]
        llm = FixedLLMProvider()
        judge = FixedLLMProvider(
            response='{"scores":{"correctness":2,"completeness":1,"evidence_support":2,'
            '"citation_accuracy":2,"caution":1,"clarity":2,"memory_contamination":2},'
            '"total":12,"verdict":"win","reasons":["证据可追溯"]}'
        )

        report = evaluate_answer_quality(service, questions, answer_llm=llm, judge_llm=judge, top_k=4)

        self.assertEqual(report["total"], 1)
        detail = report["details"][0]
        self.assertEqual(set(detail["answers"]), {"closed_book", "evidence_only", "rag_product"})
        self.assertIn("[E1]", detail["evidence_pack"])
        self.assertEqual(detail["judgments"]["rag_product"]["scores"]["correctness"], 2)
        self.assertEqual(report["aggregate"]["rag_product"]["average_total"], 12.0)
        self.assertEqual(report["aggregate"]["rag_product"]["average_scores"]["memory_contamination"], 2.0)

    def test_answer_quality_markdown_contains_dimensions_and_memory_notes(self):
        report = {
            "title": "小样本回答质量评测",
            "total": 1,
            "generated_at": "2026-06-03T10:00:00+08:00",
            "aggregate": {
                "closed_book": {"average_total": 8.0, "wins": 0, "ties": 0, "losses": 1},
                "evidence_only": {"average_total": 10.0, "wins": 0, "ties": 1, "losses": 0},
                "rag_product": {"average_total": 12.0, "wins": 1, "ties": 0, "losses": 0},
            },
            "details": [
                {
                    "id": "q1",
                    "question": "隐身的人攻击有优势吗？",
                    "scope": "core",
                    "reference_answer": "通常有优势。",
                    "evidence_pack": "[E1] 隐形：攻击有优势。",
                    "answers": {
                        "closed_book": "有优势。",
                        "evidence_only": "根据证据，有优势。",
                        "rag_product": "结论：通常有优势。[E1]",
                    },
                    "judgments": {
                        "closed_book": {"total": 8, "verdict": "loss", "reasons": ["没有引用"]},
                        "evidence_only": {"total": 10, "verdict": "tie", "reasons": ["可用"]},
                        "rag_product": {
                        "total": 12,
                        "verdict": "win",
                        "reasons": ["引用准确", "没有明显记忆污染"],
                            "scores": {
                                "correctness": 2,
                                "completeness": 1,
                                "evidence_support": 2,
                                "citation_accuracy": 2,
                                "caution": 1,
                                "clarity": 2,
                                "memory_contamination": 2,
                            },
                        },
                    },
                }
            ],
        }

        markdown = render_answer_eval_markdown(report)

        self.assertIn("小样本回答质量评测", markdown)
        self.assertIn("Correctness", markdown)
        self.assertIn("Memory Contamination", markdown)
        self.assertIn("Dimension Averages", markdown)
        self.assertIn("C/M", markdown)
        self.assertIn("rag_product", markdown)
        self.assertIn("引用准确", markdown)

    def test_judgment_parser_accepts_list_scores(self):
        judgment = parse_judgment_for_test(
            '{"scores":[{"dimension":"correctness","score":2},{"dimension":"memory_contamination","score":0}],'
            '"verdict":"loss","reasons":"使用了证据外规则"}'
        )

        self.assertEqual(judgment["scores"]["correctness"], 2)
        self.assertEqual(judgment["scores"]["memory_contamination"], 0)
        self.assertEqual(judgment["total"], 2)
        self.assertEqual(judgment["reasons"], ["使用了证据外规则"])

    def test_cached_llm_provider_reuses_prior_response(self):
        class CountingProvider:
            def __init__(self):
                self.calls = 0

            def answer(self, system_prompt, user_prompt):
                self.calls += 1
                return f"response-{self.calls}"

        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.jsonl"
            provider = CountingProvider()
            cached = CachedLLMProvider(provider, cache_path, namespace="test")

            first = cached.answer("system", "user")
            second = cached.answer("system", "user")

        self.assertEqual(first, "response-1")
        self.assertEqual(second, "response-1")
        self.assertEqual(provider.calls, 1)


if __name__ == "__main__":
    unittest.main()
