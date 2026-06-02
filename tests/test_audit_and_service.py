import tempfile
import unittest
from pathlib import Path

from dnd_rag.adapters import FiveEToolsCnAdapter
from dnd_rag.audit import audit_source_tree
from dnd_rag.service import RagService


class AuditAndServiceTests(unittest.TestCase):
    def test_audit_excludes_adventure_roll20_and_utility_from_v1_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data" / "roll20-module").mkdir(parents=True)
            (root / "data" / "adventure").mkdir(parents=True)
            (root / "data" / "spells").mkdir(parents=True)
            (root / "data" / "roll20-module" / "huge.json").write_text("{}", encoding="utf-8")
            (root / "data" / "adventure" / "adventure-demo.json").write_text("{}", encoding="utf-8")
            (root / "data" / "spells" / "spells-phb.json").write_text('{"spell":[]}', encoding="utf-8")

            report = audit_source_tree(root / "data")

            self.assertEqual(report.total_files, 3)
            self.assertEqual(report.excluded_files, 2)
            self.assertEqual(report.indexable_files, 1)
            self.assertIn("roll20-module", report.excluded_reasons)
            self.assertIn("adventure", report.excluded_reasons)

    def test_service_answers_with_citations_and_related_entries(self):
        service = RagService.from_sample_data()

        response = service.ask("隐身的人攻击有优势吗？", scope="core")

        self.assertIn("通常有优势", response.direct_answer)
        self.assertIn("判定", response.answer)
        self.assertGreaterEqual(len(response.citations), 1)
        self.assertEqual(len({citation["document_id"] for citation in response.citations}), len(response.citations))
        self.assertTrue(any(len(citation["passages"]) >= 1 for citation in response.citations))
        self.assertGreaterEqual(len(response.supporting_points), 1)
        self.assertGreaterEqual(len(response.caveats), 1)
        self.assertGreaterEqual(len(response.evidence), 1)
        self.assertTrue(any(item.score.reasons for item in response.evidence))
        self.assertTrue(any(entry.title_zh == "隐形" for entry in response.related_entries))

    def test_service_gives_direct_concentration_ruling(self):
        service = RagService.from_sample_data()

        response = service.ask("法师被打了专注会不会立刻断？", scope="core")

        self.assertIn("不会自动中断", response.direct_answer)
        self.assertTrue(any("体质豁免" in point for point in response.supporting_points))


class AdapterTests(unittest.TestCase):
    def test_sample_adapter_loads_documents_and_chunks(self):
        adapter = FiveEToolsCnAdapter.sample()

        documents = adapter.load_documents()

        self.assertTrue(any(doc.title_zh == "隐形" for doc in documents))
        self.assertTrue(all(doc.knowledge_domain in {"rules", "entity"} for doc in documents))


if __name__ == "__main__":
    unittest.main()
