# Retrieval Regression Notes

This note records cases where adding full embedding improved aggregate retrieval metrics but produced worse or still-noisy Top 1 evidence on specific questions.

Source report: `docs/evaluations/retrieval-eval-full-seed-comparison.md`

Additional community-real seed report: `docs/evaluations/retrieval-eval-community-real-seed-comparison.md`

## Current Aggregate Result

| Run | Recall@8 | MRR | Primary@1 |
| --- | ---: | ---: | ---: |
| Token Hybrid | 70.97% | 0.5393 | 45.16% |
| Embedding Hybrid | 93.55% | 0.8306 | 74.19% |

Embedding is clearly useful overall, but not uniformly better. We should not tune weights based only on aggregate gains.

## Reverse Or Noisy Cases

| ID | Symptom | Likely Cause | Next Action |
| --- | --- | --- | --- |
| `full-egw-gift-of-alacrity-initiative` | Embedding Top 1 is `激活物品`, while expected evidence is `灵敏之赐`. | Query asks for an effect without naming the spell; generic action/chunk text can over-score. | Add query rewrite/title candidate step for “先攻 + 1d8”; consider title/entity boost for spell-like questions. |
| `full-tce-chef-short-rest-healing` | Both token and embedding prefer `治疗师`; `大厨` is rank 2 under embedding. | Question contains “短休/回血/生命骰”, which overlaps strongly with core healing feat. | Add category-sensitive boost when query asks “哪个专长”; improve expected answer entity detection. |
| `full-tce-crusher-move-target` | Embedding Top 1 is `突刺击`; expected `粉碎者` appears lower. | “把目标挪 5 尺” overlaps with maneuvers and forced movement. | Add exact damage-type term boost for `钝击` + feat title/alias candidates. |
| `full-tce-crusher-critical-advantage` | Neither method retrieves `粉碎者` in Top 8. | Natural query lacks feat title and asks a conditional interaction. | Add synthetic aliases for feat effects; evaluate query expansion before reranker. |
| `full-xge-bountiful-luck-reaction` | Embedding improves rank but Top 1 is `半身人`, not `慷慨吉运`. | Query mentions halfing identity, so race page competes with feat. | When question asks “专长”, boost feat category and downweight race-only matches. |
| `full-tce-bloodwell-vial-sorcery-points` | Expected evidence is hit, but first hit is rank 4. | “术士/术法点/小瓶” overlaps with monster spellcaster text. | Add item category boost for equipment-like noun phrases. |
| `full-vrgr-dhampir-no-breath` | Embedding regresses from a weak token hit to no expected hit; Top 1 is `吸血鬼`. | Query uses colloquial “吸血鬼味儿族系” instead of `半血裔`; semantic match drifts to monster entry. | Add alias `吸血鬼味儿族系 -> 半血裔`; boost race category for “族系/种族”. |
| `full-mm-hydra-extra-reactions` | Embedding Top 1 is `借机攻击`, while expected entity is `海德拉`. | Question asks the action reason but not monster name; action evidence dominates. | For “为什么某怪物有…” queries, detect creature hints and preserve entity evidence. |
| `full-vgm-flail-snail-antimagic-shell` | Embedding improves rank but Top 1 is `激活物品`; expected `连枷蜗牛` rank 3. | “单体法术弹回施法者” shares activation/magic wording with generic item action. | Add aliases `反魔法壳/蜗牛 -> 连枷蜗牛`; boost monster feature chunks when query mentions creature nickname. |

## Tuning Rule

Do not tune after one or two examples. First expand the community-real question set, rerun comparison reports, then tune once against patterns:

- category routing: spell / feat / item / race / monster / action;
- Chinese aliases and colloquial nicknames;
- title/entity recall before dense scoring;
- parent-child expansion weights;
- optional reranker after transparent scoring is stable.

## Community-Real Seed Result

First batch: `eval/community_real_seed.json`

The community-real batch is still small and its source URLs are marked `candidate_unverified`; it is useful for retrieval stress testing, not yet for final benchmark claims.

| Run | Recall@8 | MRR | Primary@1 |
| --- | ---: | ---: | ---: |
| Token Hybrid | 83.33% | 0.7917 | 50.00% |
| Embedding Hybrid | 91.67% | 0.8125 | 75.00% |

Community questions are harder than generated seed questions because they use indirect phrasing and combine multiple rules. The first batch shows embedding still helps, but the failures are more diagnostic:

| ID | Symptom | Likely Cause | Next Action |
| --- | --- | --- | --- |
| `community-rpgse-silence-verbal-components` | Both systems retrieve `触发术` instead of `沉默术`. | Query includes “带语言成分/不能施放”, but current title/entity recall does not force `沉默术`. | Add title/alias trigger for `沉默/无声/声音/语言成分`; boost spell title match. |
| `community-rpgse-subtle-counterspell` | Expected `反制法术`, but Top 1 is `反魔法结界`. | “反制/静默/施法” overlaps with anti-magic concept. | Add exact Chinese/English alias table: `counterspell -> 反制法术`, `subtle spell -> 静默施法/微妙法术`. |
| `community-rpgse-magic-item-counterspell` | Expected `反制法术` + `激活物品`, but Top 1 is `反魔法结界`. | Magic item activation and anti-magic language compete with spell title. | Query routing should split multi-hop questions into evidence needs: spell rule + item activation rule. |

Do not fix these one by one yet. Expand community questions first, then tune against recurring categories.
