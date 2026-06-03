import unittest

from dnd_rag.adapters import FiveEToolsNormalizer
from dnd_rag.chunking import build_chunks
from dnd_rag.models import SearchScope
from dnd_rag.planner import MultiHopEvidencePlanner
from dnd_rag.retrieval import HybridRetriever


class MultiHopPlannerTests(unittest.TestCase):
    def test_plans_compound_requirements_from_general_signals(self):
        planner = MultiHopEvidencePlanner(HybridRetriever([]))

        plan = planner.plan("用魔法物品施法能被反制法术吗？")

        self.assertTrue(plan.analysis.likely_multi_hop)
        self.assertIn("counterspell_trigger", [req.id for req in plan.requirements])
        self.assertIn("magic_item_activation", [req.id for req in plan.requirements])
        self.assertIn("反制法术", plan.analysis.explicit_entities)
        self.assertIn("魔法物品", plan.analysis.category_mentions)

    def test_simple_lookup_keeps_single_requirement(self):
        planner = MultiHopEvidencePlanner(HybridRetriever([]))

        plan = planner.plan("隐形的人攻击有优势吗？")

        self.assertFalse(plan.analysis.likely_multi_hop)
        self.assertEqual([req.id for req in plan.requirements], ["invisible_condition"])

    def test_magic_item_counterspell_requires_both_rule_evidence_groups(self):
        retriever = HybridRetriever(_chunks_for_entries([
            (
                {
                    "name": "反制法术",
                    "ENG_name": "Counterspell",
                    "source": "PHB",
                    "page": 228,
                    "entries": ["你试图中断一个生物施展法术的过程。"],
                },
                "spells",
            ),
            (
                {
                    "name": "激活物品",
                    "source": "DMG",
                    "page": 141,
                    "entries": ["一些魔法物品允许使用者从物品中施展法术。该法术无需构材。"],
                },
                "actions",
            ),
            (
                {
                    "name": "反魔法结界",
                    "source": "PHB",
                    "page": 213,
                    "entries": ["一个反魔法区域会压制法术和其他魔法效果。"],
                },
                "spells",
            ),
        ]))
        planner = MultiHopEvidencePlanner(retriever)

        result = planner.search("用魔法物品施法能被反制法术吗？", scope=SearchScope.CORE, top_k=4)

        self.assertTrue(result.is_multi_hop)
        self.assertEqual(result.coverage_score, 1.0)
        self.assertEqual(result.missing_requirements, [])
        self.assertEqual(
            {group.requirement.id for group in result.requirement_evidence if group.covered},
            {"counterspell_trigger", "magic_item_activation"},
        )
        self.assertIn("反制法术", [item.chunk.citation.title for item in result.evidence[:3]])
        self.assertIn("激活物品", [item.chunk.citation.title for item in result.evidence[:3]])

    def test_subtle_counterspell_requires_metamagic_and_trigger_rule(self):
        retriever = HybridRetriever(_chunks_for_entries([
            (
                {
                    "name": "反制法术",
                    "ENG_name": "Counterspell",
                    "source": "PHB",
                    "page": 228,
                    "entries": ["你试图中断一个生物施展法术的过程。"],
                },
                "spells",
            ),
            (
                {
                    "name": "微妙法术",
                    "ENG_name": "Subtle Spell",
                    "source": "PHB",
                    "page": 102,
                    "entries": ["你施展法术时，可以花费1点术法点，使其无需姿势或言语成分。"],
                },
                "optionalfeatures",
            ),
            (
                {
                    "name": "反魔法结界",
                    "source": "PHB",
                    "page": 213,
                    "entries": ["一个反魔法区域会压制法术和其他魔法效果。"],
                },
                "spells",
            ),
            (
                {
                    "name": "施法构材",
                    "source": "PHB",
                    "page": 85,
                    "entries": ["如果一个角色感知到了施法、法术效果，或者两者都感知到了，该角色可以尝试识别法术。"],
                },
                "actions",
            ),
        ]))
        planner = MultiHopEvidencePlanner(retriever)

        result = planner.search("法术被超魔静默施法处理后，还能被反制法术反制吗？", scope=SearchScope.CORE, top_k=4)

        self.assertEqual(result.coverage_score, 1.0)
        self.assertEqual(
            {group.requirement.id for group in result.requirement_evidence if group.covered},
            {"counterspell_trigger", "subtle_spell_mechanic", "spell_component_observability"},
        )
        self.assertIn("反制法术", [item.chunk.citation.title for item in result.evidence[:3]])
        self.assertIn("微妙法术", [item.chunk.citation.title for item in result.evidence[:3]])
        self.assertIn("施法构材", [item.chunk.citation.title for item in result.evidence[:3]])

    def test_subtle_counterspell_marks_observability_missing_without_spellcasting_evidence(self):
        retriever = HybridRetriever(_chunks_for_entries([
            (
                {
                    "name": "反制法术",
                    "source": "PHB",
                    "page": 228,
                    "entries": ["施法时间：1反应，在你看见一个距离你60尺以内的生物施放法术时进行。"],
                },
                "spells",
            ),
            (
                {
                    "name": "微妙法术",
                    "source": "PHB",
                    "page": 102,
                    "entries": ["你施展法术时，可以花费1点术法点，使其无需姿势或言语成分。"],
                },
                "optionalfeatures",
            ),
            (
                {
                    "name": "施法",
                    "source": "PHB",
                    "page": 192,
                    "entries": ["每个法术都有着自己的施法时间，指定了施法者必须使用一个动作、反应、数分钟、或甚至数小时的时间才能施放该法术。"],
                },
                "actions",
            ),
        ]))
        planner = MultiHopEvidencePlanner(retriever)

        result = planner.search("法术被超魔静默施法处理后，还能被反制法术反制吗？", scope=SearchScope.CORE, top_k=4)

        self.assertEqual(
            {group.requirement.id for group in result.requirement_evidence},
            {"counterspell_trigger", "subtle_spell_mechanic", "spell_component_observability"},
        )
        self.assertEqual(
            [requirement.id for requirement in result.missing_requirements],
            ["spell_component_observability"],
        )

    def test_subtle_counterspell_covers_observability_with_spell_identification_evidence(self):
        retriever = HybridRetriever(_chunks_for_entries([
            (
                {
                    "name": "反制法术",
                    "source": "PHB",
                    "page": 228,
                    "entries": ["施法时间：1反应，在你看见一个距离你60尺以内的生物施放法术时进行。"],
                },
                "spells",
            ),
            (
                {
                    "name": "微妙法术",
                    "source": "PHB",
                    "page": 102,
                    "entries": ["你施展法术时，可以花费1点术法点，使其无需姿势或言语成分。"],
                },
                "optionalfeatures",
            ),
            (
                {
                    "name": "施法构材",
                    "source": "PHB",
                    "page": 85,
                    "entries": ["如果一个角色感知到了施法、法术效果，或者两者都感知到了，该角色可以尝试识别法术。"],
                },
                "actions",
            ),
        ]))
        planner = MultiHopEvidencePlanner(retriever)

        result = planner.search("法术被超魔静默施法处理后，还能被反制法术反制吗？", scope=SearchScope.CORE, top_k=4)

        self.assertEqual(result.coverage_score, 1.0)
        self.assertEqual(result.missing_requirements, [])
        self.assertIn("施法构材", [item.chunk.citation.title for item in result.evidence[:3]])

    def test_special_sense_invisible_question_requires_both_sense_and_condition(self):
        retriever = HybridRetriever(_chunks_for_entries([
            (
                {
                    "name": "隐形",
                    "source": "PHB",
                    "page": 291,
                    "entries": ["隐形生物的攻击检定具有优势，对其攻击检定具有劣势。"],
                },
                "conditions",
            ),
            (
                {
                    "name": "盲视",
                    "source": "PHB",
                    "page": 183,
                    "entries": ["具有盲视的生物可以在特定半径内不依赖视觉感知周围环境。"],
                },
                "variantrules",
            ),
        ]))
        planner = MultiHopEvidencePlanner(retriever)

        result = planner.search("有盲视的生物攻击隐形目标，还会因为看不见而有劣势吗？", scope=SearchScope.CORE, top_k=4)

        self.assertEqual(result.coverage_score, 1.0)
        self.assertEqual(
            {group.requirement.id for group in result.requirement_evidence if group.covered},
            {"invisible_condition", "blindsight_sense"},
        )
        self.assertIn("隐形", [item.chunk.citation.title for item in result.evidence[:3]])
        self.assertIn("盲视", [item.chunk.citation.title for item in result.evidence[:3]])

    def test_bonus_action_ready_spell_marks_missing_limit_rule_without_book_evidence(self):
        retriever = HybridRetriever(_chunks_for_entries([
            (
                {
                    "name": "准备",
                    "source": "PHB",
                    "page": 193,
                    "entries": ["当你准备一个法术时，你仍如常施放它但扣住其能量。一个法术必须具有1个动作的施法时间才能被准备。"],
                },
                "actions",
            ),
            (
                {
                    "name": "施法",
                    "source": "PHB",
                    "page": 192,
                    "entries": ["每个法术都有自己的施法时间，可能需要动作、反应或更长时间。"],
                },
                "actions",
            ),
        ]))
        planner = MultiHopEvidencePlanner(retriever)

        result = planner.search("如果我这回合已经用附赠动作施法，还能用动作准备另一个法术吗？", scope=SearchScope.CORE, top_k=4)

        self.assertTrue(result.is_multi_hop)
        self.assertEqual(
            [requirement.id for requirement in result.missing_requirements],
            ["bonus_action_spell_limit"],
        )
        self.assertIn("ready_spell_mechanic", [group.requirement.id for group in result.requirement_evidence if group.covered])

    def test_concentration_damage_question_requires_general_concentration_rule(self):
        retriever = HybridRetriever(_chunks_for_entries([
            (
                {
                    "name": "专注",
                    "source": "PHB",
                    "page": 203,
                    "entries": [
                        "每当你在专注于一个法术的期间受到伤害，你都必须进行一次体质豁免，成功则继续维持你的专注。若失败则专注被中断。"
                    ],
                },
                "conditionsdiseases",
            ),
            (
                {
                    "name": "地震术",
                    "source": "PHB",
                    "page": 236,
                    "entries": ["区域内地面上正专注于法术的生物必须进行体质豁免，失败则专注中断。"],
                },
                "spells",
            ),
        ]))
        planner = MultiHopEvidencePlanner(retriever)

        result = planner.search("法师挨打后专注会立刻断吗？", scope=SearchScope.CORE, top_k=4)

        self.assertEqual(result.coverage_score, 1.0)
        self.assertEqual(result.missing_requirements, [])
        self.assertEqual(
            [group.requirement.id for group in result.requirement_evidence if group.covered],
            ["concentration_damage_rule"],
        )
        self.assertEqual(result.evidence[0].chunk.citation.title, "专注")

    def test_silence_verbal_question_focuses_on_silence_evidence(self):
        retriever = HybridRetriever(_chunks_for_entries([
            (
                {
                    "name": "沉默术",
                    "source": "PHB",
                    "page": 275,
                    "entries": ["在里面不可能施放需要声音构材的法术。"],
                },
                "spells",
            ),
            (
                {
                    "name": "激活物品",
                    "source": "DMG",
                    "page": 141,
                    "entries": ["一些魔法物品可以让其使用者从物品中施展法术，且不需要任何构材。"],
                },
                "actions",
            ),
        ]))
        planner = MultiHopEvidencePlanner(retriever)

        result = planner.search("沉默术范围里还能施展有言语成分的法术吗？", scope=SearchScope.CORE, top_k=4)

        self.assertEqual(result.coverage_score, 1.0)
        self.assertEqual(result.missing_requirements, [])
        self.assertEqual(
            [group.requirement.id for group in result.requirement_evidence if group.covered],
            ["silence_verbal_component_rule"],
        )
        self.assertTrue(all(item.chunk.citation.title == "沉默术" for item in result.evidence))


def _chunks_for_entries(entries):
    normalizer = FiveEToolsNormalizer()
    docs = [normalizer.normalize_entry(entry, category) for entry, category in entries]
    return [chunk for doc in docs for chunk in build_chunks(doc)]


if __name__ == "__main__":
    unittest.main()
