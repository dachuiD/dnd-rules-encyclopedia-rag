import unittest
import json
from pathlib import Path

from dnd_rag.eval import evaluate_retrieval
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
        }
        for question in questions:
            self.assertTrue(required_fields.issubset(question), question.get("id"))
            self.assertTrue(question["expected_terms"], question["id"])
            self.assertTrue(question["expected_primary_terms"], question["id"])
            self.assertIn(question["difficulty"], {"easy", "medium", "hard"})
            self.assertIn(question["scope"], {"core", "full"})
        self.assertEqual(
            {question["question_type"] for question in questions},
            {"lookup", "ruling", "comparison", "edge_case", "encyclopedia"},
        )


if __name__ == "__main__":
    unittest.main()
