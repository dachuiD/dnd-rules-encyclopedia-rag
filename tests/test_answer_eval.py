import unittest
import tempfile
from pathlib import Path

from dnd_rag.answer_eval import (
    CachedLLMProvider,
    FixedLLMProvider,
    build_evidence_pack,
    evaluate_answer_quality,
    parse_judgment_for_test,
    render_answer_eval_markdown,
)
from dnd_rag.service import RagService


class AnswerEvalTests(unittest.TestCase):
    def test_evidence_pack_includes_requirement_coverage(self):
        pack = build_evidence_pack(
            [],
            evidence_requirements=[
                {
                    "id": "counterspell_trigger",
                    "label": "反制法术触发条件",
                    "role": "trigger_rule",
                    "required": True,
                    "covered": True,
                    "evidence_titles": ["反制法术"],
                },
                {
                    "id": "magic_item_activation",
                    "label": "魔法物品激活与施法机制",
                    "role": "mechanic_rule",
                    "required": True,
                    "covered": False,
                    "evidence_titles": [],
                },
            ],
        )

        self.assertIn("Evidence Requirements", pack)
        self.assertIn("反制法术触发条件", pack)
        self.assertIn("covered", pack)
        self.assertIn("魔法物品激活与施法机制", pack)
        self.assertIn("missing", pack)

    def test_rag_product_prompt_requires_evidence_sufficiency_and_no_outside_rules(self):
        class CaptureProvider:
            def __init__(self):
                self.calls = []

            def answer(self, system_prompt, user_prompt):
                self.calls.append((system_prompt, user_prompt))
                return "captured answer"

        service = RagService.from_sample_data()
        answer_llm = CaptureProvider()
        judge = FixedLLMProvider(
            response='{"scores":{"correctness":1,"completeness":1,"evidence_support":1,'
            '"citation_accuracy":1,"caution":1,"clarity":1,"memory_contamination":1},'
            '"total":7,"verdict":"tie","reasons":["captured"]}'
        )

        evaluate_answer_quality(
            service,
            [
                {
                    "id": "q1",
                    "question_zh": "法师挨打后专注会立刻断吗？",
                    "scope": "core",
                    "reference_answer": "不会自动中断。",
                }
            ],
            answer_llm=answer_llm,
            judge_llm=judge,
            top_k=3,
        )

        rag_system_prompt = answer_llm.calls[2][0]
        self.assertIn("不能补充 evidence pack 之外", rag_system_prompt)
        self.assertIn("证据不足", rag_system_prompt)
        self.assertIn("不得编写未被证据支持的 DC", rag_system_prompt)
        self.assertIn("Evidence Requirements", rag_system_prompt)
        self.assertIn("missing 的 required requirement", rag_system_prompt)
        self.assertIn("适用条件和容易误判只能写 evidence pack 明示的信息", rag_system_prompt)

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
