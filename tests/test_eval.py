import unittest

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


if __name__ == "__main__":
    unittest.main()
