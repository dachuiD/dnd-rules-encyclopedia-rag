import unittest

from dnd_rag.chunking import build_chunks
from dnd_rag.models import SearchScope
from dnd_rag.normalize import FiveEToolsNormalizer
from dnd_rag.retrieval import HybridRetriever
from dnd_rag.text import clean_5etools_text, extract_5etools_refs


ACTION_ENTRY = {
    "name": "激活物品",
    "ENG_name": "Activate an Item",
    "source": "DMG",
    "page": 141,
    "srd": True,
    "entries": [
        "一些魔法物品需要其使用者做一些特别的事情才能激活。",
        "如果某物品需要用一个动作激活，则该动作本身并不作为{@action 使用物件}动作。",
        {
            "type": "entries",
            "name": "法术",
            "ENG_name": "Spells",
            "entries": [
                "一些魔法物品可以让其使用者从物品中施展{@spell 沉默术}。如果法术需要专注，则使用者还必须专注。"
            ],
        },
    ],
}


SPELL_ENTRY = {
    "name": "火球术",
    "ENG_name": "Fireball",
    "source": "PHB",
    "page": 241,
    "level": 3,
    "school": "V",
    "time": [{"number": 1, "unit": "action"}],
    "range": {"type": "point", "distance": {"type": "feet", "amount": 150}},
    "entries": [
        "一颗明亮的闪光从你的指尖射向射程内一点，并在该点爆发为火焰。",
        "每个生物必须进行一次敏捷豁免，豁免失败则受到8d6火焰伤害。",
    ],
    "entriesHigherLevel": [
        {
            "type": "entries",
            "name": "升环施法",
            "entries": ["你使用4环或更高环阶的法术位施展该法术时，每高于3环一环，伤害增加1d6。"],
        }
    ],
}


class TextParsingTests(unittest.TestCase):
    def test_clean_5etools_tags_keeps_human_text(self):
        text = "使用{@spell 沉默术}和{@action 使用物件}，以及{@subclassFeature 快手|Rogue||Thief||3}。"

        self.assertEqual(clean_5etools_text(text), "使用沉默术和使用物件，以及快手。")

    def test_extract_5etools_refs_preserves_relation_targets(self):
        refs = extract_5etools_refs("查看{@spell 沉默术}和{@action 使用物件}。")

        self.assertEqual(
            [(ref.ref_type, ref.label) for ref in refs],
            [("spell", "沉默术"), ("action", "使用物件")],
        )


class NormalizationTests(unittest.TestCase):
    def test_action_normalizes_to_core_rule_document(self):
        normalizer = FiveEToolsNormalizer()

        doc = normalizer.normalize_entry(ACTION_ENTRY, "actions")

        self.assertEqual(doc.title_zh, "激活物品")
        self.assertEqual(doc.title_en, "Activate an Item")
        self.assertEqual(doc.source_id, "DMG")
        self.assertEqual(doc.source_group, "core")
        self.assertEqual(doc.search_scope, "core")
        self.assertEqual(doc.knowledge_domain, "rules")
        self.assertIn("使用物件", doc.body_text)
        self.assertNotIn("{@action", doc.body_text)
        self.assertEqual(doc.citation.page, 141)


class ChunkingTests(unittest.TestCase):
    def test_spell_uses_parent_and_child_chunks(self):
        doc = FiveEToolsNormalizer().normalize_entry(SPELL_ENTRY, "spells")

        chunks = build_chunks(doc)

        self.assertGreaterEqual(len(chunks), 3)
        self.assertEqual(chunks[0].chunk_level, "parent")
        self.assertEqual(chunks[0].chunk_type, "spell_description")
        child_types = {chunk.chunk_type for chunk in chunks[1:]}
        self.assertIn("spell_description", child_types)
        self.assertTrue(any("分类：spells" in chunk.embedding_text for chunk in chunks))
        self.assertTrue(any("升环施法" in chunk.embedding_text for chunk in chunks))
        self.assertTrue(all(chunk.display_text for chunk in chunks))


class RetrievalTests(unittest.TestCase):
    def test_alias_and_scope_influence_transparent_scoring(self):
        normalizer = FiveEToolsNormalizer()
        docs = [
            normalizer.normalize_entry(
                {
                    "name": "借机攻击",
                    "ENG_name": "Opportunity Attack",
                    "source": "PHB",
                    "page": 195,
                    "entries": ["当敌对生物离开你的触及范围时，你可以使用反应发动一次借机攻击。"],
                },
                "actions",
            ),
            normalizer.normalize_entry(
                {
                    "name": "扩展反应选项",
                    "ENG_name": "Expanded Reactions",
                    "source": "XGE",
                    "page": 12,
                    "entries": ["这是一段拓展资料，描述额外的反应选项。"],
                },
                "variantrules",
            ),
        ]
        chunks = [chunk for doc in docs for chunk in build_chunks(doc)]
        retriever = HybridRetriever(chunks)

        results = retriever.search("机会攻击怎么触发？", scope=SearchScope.CORE, top_k=3)

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].chunk.document_id, docs[0].id)
        self.assertGreater(results[0].score.alias_score, 0)
        self.assertTrue(any("别名命中" in reason for reason in results[0].score.reasons))
        self.assertTrue(all(result.chunk.source_id in {"PHB", "DMG", "MM"} for result in results))


if __name__ == "__main__":
    unittest.main()
