import unittest
import json
from pathlib import Path

from dnd_rag.eval import (
    evaluate_retrieval,
    render_retrieval_eval_comparison_summary_markdown,
    render_retrieval_eval_markdown,
    render_retrieval_eval_summary_markdown,
)
from dnd_rag.service import RagService


class EvalTests(unittest.TestCase):
    def test_retrieval_eval_reports_recall_and_mrr(self):
        service = RagService.from_sample_data()
        questions = [
            {
                "id": "q1",
                "question_zh": "隐身攻击是否有优势？",
                "scope": "core",
                "expected_terms": ["隐形"],
                "expected_documents": [],
            }
        ]

        report = evaluate_retrieval(service, questions, top_k=8)

        self.assertEqual(report["total"], 1)
        self.assertEqual(report["recall_at_k"], 1.0)
        self.assertGreater(report["mrr"], 0)

    def test_retrieval_eval_reports_primary_hit_at_1_when_primary_terms_are_present(self):
        service = RagService.from_sample_data()
        questions = [
            {
                "id": "q1",
                "question_zh": "打一个看不见的目标是不是有劣势？",
                "scope": "core",
                "expected_terms": ["隐形", "目盲"],
                "expected_primary_terms": ["隐形"],
                "expected_documents": [],
            }
        ]

        report = evaluate_retrieval(service, questions, top_k=8)

        self.assertIn("primary_hit_at_1", report)
        self.assertIn(report["primary_hit_at_1"], {0.0, 1.0})
        self.assertIn("primary_hit_at_1", report["details"][0])

    def test_retrieval_eval_details_include_auditable_expected_answer_and_evidence(self):
        service = RagService.from_sample_data()
        questions = [
            {
                "id": "q1",
                "question_zh": "隐身的人攻击有优势吗？",
                "scope": "core",
                "reference_answer": "通常有优势，但不是自动命中。",
                "expected_terms": ["隐形", "优势"],
                "expected_primary_terms": ["隐形"],
                "must_include": ["优势"],
                "must_not_include": ["自动命中"],
                "difficulty": "easy",
                "question_type": "ruling",
            }
        ]

        report = evaluate_retrieval(service, questions, top_k=3)
        detail = report["details"][0]

        self.assertEqual(detail["reference_answer"], "通常有优势，但不是自动命中。")
        self.assertEqual(detail["expected_terms"], ["隐形", "优势"])
        self.assertEqual(detail["must_include"], ["优势"])
        self.assertEqual(detail["must_not_include"], ["自动命中"])
        self.assertEqual(detail["difficulty"], "easy")
        self.assertEqual(detail["question_type"], "ruling")
        self.assertTrue(detail["top_evidence"])
        top = detail["top_evidence"][0]
        self.assertIn("citation", top)
        self.assertIn("source_id", top)
        self.assertIn("score_parts", top)
        self.assertIn("final", top["score_parts"])
        self.assertIn("reasons", top)
        self.assertIn("display_text", top)

    def test_retrieval_eval_markdown_renders_dataset_metrics_and_evidence(self):
        service = RagService.from_sample_data()
        questions = [
            {
                "id": "q1",
                "question_zh": "隐身的人攻击有优势吗？",
                "scope": "core",
                "reference_answer": "通常有优势；隐形不是自动命中。",
                "expected_terms": ["隐形", "优势"],
                "expected_primary_terms": ["隐形"],
                "must_include": ["优势"],
                "must_not_include": ["自动命中"],
                "difficulty": "easy",
                "question_type": "ruling",
            }
        ]
        report = evaluate_retrieval(service, questions, top_k=3)

        markdown = render_retrieval_eval_markdown(
            report,
            title="Retrieval Eval Test",
            dataset_path="eval/golden_test.json",
            evidence_limit=2,
        )

        self.assertIn("# Retrieval Eval Test", markdown)
        self.assertIn("eval/golden_test.json", markdown)
        self.assertIn("Recall@3", markdown)
        self.assertIn("同一来源出现不同分数", markdown)
        self.assertIn("q1", markdown)
        self.assertIn("隐身的人攻击有优势吗？", markdown)
        self.assertIn("通常有优势；隐形不是自动命中。", markdown)
        self.assertIn("期望命中词", markdown)
        self.assertIn("禁止误答点", markdown)
        self.assertIn("Top 证据", markdown)
        self.assertIn("最终分", markdown)

    def test_retrieval_eval_summary_markdown_is_compact_for_review(self):
        service = RagService.from_sample_data()
        questions = [
            {
                "id": "q1",
                "question_zh": "隐身的人攻击有优势吗？",
                "scope": "core",
                "reference_answer": "通常有优势；隐形不是自动命中。",
                "expected_terms": ["隐形", "优势"],
                "expected_primary_terms": ["隐形"],
                "must_include": ["优势"],
                "must_not_include": ["自动命中"],
                "difficulty": "easy",
                "question_type": "ruling",
            }
        ]
        report = evaluate_retrieval(service, questions, top_k=3)

        markdown = render_retrieval_eval_summary_markdown(
            report,
            title="Full Seed Review",
            dataset_path="eval/golden_full_seed.json",
            embedding_index="storage/embedding-index/full.jsonl",
        )

        self.assertIn("# Full Seed Review", markdown)
        self.assertIn("eval/golden_full_seed.json", markdown)
        self.assertIn("Recall@3", markdown)
        self.assertIn("## Review Table", markdown)
        self.assertIn("q1", markdown)
        self.assertIn("隐身的人攻击有优势吗？", markdown)
        self.assertIn("通常有优势；隐形不是自动命中。", markdown)
        self.assertIn("Top1", markdown)
        self.assertIn("## Needs Review", markdown)
        self.assertNotIn("#### Top 证据", markdown)
        self.assertNotIn("display_text", markdown)

    def test_retrieval_eval_comparison_summary_shows_embedding_delta(self):
        baseline = {
            "total": 2,
            "top_k": 8,
            "recall_at_k": 0.5,
            "mrr": 0.25,
            "primary_hit_at_1": 0.0,
            "details": [
                {
                    "id": "q1",
                    "question": "哪个法术能让先攻加骰？",
                    "reference_answer": "灵敏之赐让先攻加入 1d8。",
                    "hit": True,
                    "rank": 4,
                    "primary_hit_at_1": False,
                    "top_evidence": [{"title": "激活物品", "citation": "DMG / actions", "score_parts": {"final": 0.7}}],
                },
                {
                    "id": "q2",
                    "question": "半血裔需要呼吸吗？",
                    "reference_answer": "不需要呼吸。",
                    "hit": False,
                    "rank": None,
                    "primary_hit_at_1": False,
                    "top_evidence": [{"title": "吸血鬼", "citation": "MM / bestiary", "score_parts": {"final": 0.8}}],
                },
            ],
        }
        embedding = {
            "total": 2,
            "top_k": 8,
            "recall_at_k": 1.0,
            "mrr": 1.0,
            "primary_hit_at_1": 0.5,
            "details": [
                {
                    "id": "q1",
                    "question": "哪个法术能让先攻加骰？",
                    "reference_answer": "灵敏之赐让先攻加入 1d8。",
                    "hit": True,
                    "rank": 1,
                    "primary_hit_at_1": True,
                    "top_evidence": [{"title": "灵敏之赐", "citation": "EGW / spells", "score_parts": {"final": 0.9}}],
                },
                {
                    "id": "q2",
                    "question": "半血裔需要呼吸吗？",
                    "reference_answer": "不需要呼吸。",
                    "hit": True,
                    "rank": 6,
                    "primary_hit_at_1": False,
                    "top_evidence": [{"title": "吸血鬼", "citation": "MM / bestiary", "score_parts": {"final": 0.8}}],
                },
            ],
        }

        markdown = render_retrieval_eval_comparison_summary_markdown(
            baseline,
            embedding,
            title="Embedding Comparison",
            dataset_path="eval/golden_full_seed.json",
            embedding_index="storage/embedding-index/full.jsonl",
        )

        self.assertIn("# Embedding Comparison", markdown)
        self.assertIn("Token Hybrid", markdown)
        self.assertIn("Embedding Hybrid", markdown)
        self.assertIn("Delta", markdown)
        self.assertIn("+50.00%", markdown)
        self.assertIn("## Changed Questions", markdown)
        self.assertIn("q1", markdown)
        self.assertIn("改善", markdown)
        self.assertIn("灵敏之赐", markdown)
        self.assertIn("## Still Needs Review", markdown)
        self.assertIn("q2", markdown)
        self.assertNotIn("display_text", markdown)

    def test_golden_v1_has_schema_and_question_type_coverage(self):
        questions = json.loads(Path("eval/golden_v1.json").read_text(encoding="utf-8"))

        self.assertEqual(len(questions), 20)
        required_fields = {
            "id",
            "question_zh",
            "source_language",
            "provenance",
            "scope",
            "expected_documents",
            "expected_terms",
            "must_include",
            "must_not_include",
            "difficulty",
            "question_type",
            "reference_answer",
        }
        for question in questions:
            self.assertTrue(required_fields.issubset(question), question.get("id"))
            self.assertTrue(question["expected_terms"], question["id"])
            self.assertTrue(question["expected_primary_terms"], question["id"])
            self.assertTrue(question["reference_answer"], question["id"])
            self.assertIn(question["difficulty"], {"easy", "medium", "hard"})
            self.assertIn(question["scope"], {"core", "full"})
        self.assertEqual(
            {question["question_type"] for question in questions},
            {"lookup", "ruling", "comparison", "edge_case", "encyclopedia"},
        )

    def test_golden_full_seed_has_schema_and_all_questions_are_full_scope(self):
        questions = json.loads(Path("eval/golden_full_seed.json").read_text(encoding="utf-8"))

        self.assertGreaterEqual(len(questions), 25)
        required_fields = {
            "id",
            "question_zh",
            "reference_answer",
            "source_language",
            "provenance",
            "scope",
            "expected_documents",
            "expected_terms",
            "expected_primary_terms",
            "must_include",
            "must_not_include",
            "difficulty",
            "question_type",
        }
        categories = set()
        for question in questions:
            self.assertTrue(required_fields.issubset(question), question.get("id"))
            self.assertEqual(question["scope"], "full", question["id"])
            self.assertTrue(question["reference_answer"], question["id"])
            self.assertTrue(question["expected_terms"], question["id"])
            self.assertTrue(question["expected_primary_terms"], question["id"])
            categories.add(question["question_type"])
        self.assertGreaterEqual(len(categories), 4)

    def test_community_real_seed_has_sources_and_reference_answers(self):
        questions = json.loads(Path("eval/community_real_seed.json").read_text(encoding="utf-8"))

        self.assertGreaterEqual(len(questions), 10)
        required_fields = {
            "id",
            "question_zh",
            "question_original",
            "source_language",
            "provenance",
            "community_source",
            "source_url",
            "source_status",
            "scope",
            "expected_terms",
            "expected_primary_terms",
            "reference_answer",
            "must_include",
            "must_not_include",
            "difficulty",
            "question_type",
        }
        for question in questions:
            self.assertTrue(required_fields.issubset(question), question.get("id"))
            self.assertEqual(question["provenance"], "community_en_real", question["id"])
            self.assertTrue(question["source_url"].startswith("https://"), question["id"])
            self.assertIn(question["source_status"], {"candidate_unverified", "verified"}, question["id"])
            self.assertTrue(question["reference_answer"], question["id"])
            self.assertTrue(question["expected_terms"], question["id"])


if __name__ == "__main__":
    unittest.main()
