# 社区真实候选题 Token vs Embedding 检索审阅

## Metadata

- Generated at: `2026-06-03T15:47:00+08:00`
- Dataset: `eval/community_real_seed.json`
- Data dir: `data/fvtt-cn-5etools/data`
- Embedding index: `storage/embedding-index/full.jsonl`

## Dataset Caveat

- 本报告包含 `candidate_unverified` 来源题，只能用于压力测试和失败类型分析，不能作为最终产品宣传指标。
- 正式评测前需要逐题核验社区来源，并收紧 gold evidence。

## Metrics

| Run | Total | Recall@8 | MRR | StrictDoc@8 | StrictDocMRR | Primary@1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Token Hybrid | 12 | 100.00% | 0.8542 | 77.78% | 0.5370 | 0.6667 |
| Embedding Hybrid | 12 | 100.00% | 1.0000 | 100.00% | 0.9444 | 1.0000 |
| Delta | - | +0.00% | +0.1458 | +22.22% | +0.4074 | +0.3333 |

说明：`Recall@K` 是宽松命中；`StrictDoc@K` 只统计 gold document 命中，更适合判断证据是否真的找对。

## Changed Questions

| ID | 问题 | 变化 | Token Top1 | Embedding Top1 |
| --- | --- | --- | --- | --- |
| community-rpgse-ready-spell-concentration | 准备一个法术是不是要先开始专注？如果准备的是本来就需要专注的法术，会不会冲突？ | 变化：Top1 证据不同 | 准备 (PHB / actions / 准备 / p.193, 0.963) | 准备 (PHB / actions / 准备 / p.193, 0.969) |
| community-rpgse-ready-cantrip | 准备一个戏法也要专注吗？ | 改善：Top1 命中核心证据 | 巫妖 (MM / bestiary / 巫妖 / p.202, 0.775) | 准备 (PHB / actions / 准备 / p.193, 0.900) |
| community-rpgse-ready-bonus-action-spell | 如果我这回合已经用附赠动作施法，还能用动作准备另一个法术吗？ | 改善：命中严格 gold document | 铜墙铁壁 (PHB / spells / 铜墙铁壁 / p.248, 0.715) | 准备 (PHB / actions / 准备 / p.193, 0.936) |
| community-rpgse-blindsight-invisible-disadvantage | 有盲视的生物攻击隐形目标，还会因为看不见而有劣势吗？ | 变化：Top1 证据不同 | 隐形 (PHB / conditions / 隐形 / p.291, 0.900) | 隐形 (PHB / conditions / 隐形 / p.291, 0.956) |
| community-rpgse-blindsight-detect-invisible | 盲视能不能发现隐形生物的位置？ | 变化：Top1 证据不同 | 隐形 (PHB / conditions / 隐形 / p.291, 0.900) | 隐形 (PHB / conditions / 隐形 / p.291, 0.956) |
| community-rpgse-silence-verbal-components | 沉默术范围里，带语言成分的法术是不是完全不能施放？ | 改善：命中严格 gold document | 触发术 (PHB / spells / 触发术 / p.227, 0.777) | 沉默术 (PHB / spells / 沉默术 / p.275, 0.800) |
| community-rpgse-subtle-counterspell | 法术被超魔静默施法处理后，还能被反制法术反制吗？ | 变化：Top1 证据不同 | 反制法术 (PHB / spells / 反制法术 / p.228, 0.925) | 反制法术 (PHB / spells / 反制法术 / p.228, 0.963) |
| community-rpgse-magic-item-counterspell | 用魔法物品施法能被反制法术吗？ | 变化：Top1 证据不同 | 反制法术 (PHB / spells / 反制法术 / p.228, 0.925) | 反制法术 (PHB / spells / 反制法术 / p.228, 0.963) |
| community-rpgse-grapple-shove-prone | 能不能先擒抱再推倒伏地，让目标站不起来？ | 变化：Top1 证据不同 | 水巨灵(玛利德) (MM / bestiary / 水巨灵(玛利德) / p.146, 0.711) | 擒抱 (PHB / actions / 擒抱 / p.195, 0.800) |
| community-rpgse-shove-out-of-grapple | 把擒抱者推开，能不能解除擒抱？ | 变化：Top1 证据不同 | 被擒 (PHB / conditions / 被擒 / p.290, 0.800) | 被擒 (PHB / conditions / 被擒 / p.290, 0.742) |
| community-rpgse-prone-ranged-attack | 攻击伏地目标时，远程攻击为什么经常反而有劣势？ | 改善：Top1 命中核心证据 | 攻击 (PHB / actions / 攻击 / p.192, 0.830) | 伏地 (PHB / conditions / 伏地 / p.292, 0.880) |
| community-rpgse-bonus-action-spell-order | 附赠动作施法的限制和施法顺序有关吗？ | 变化：Top1 证据不同 | 施法 (PHB / actions / 施法 / p.192, 0.765) | 施法 (PHB / actions / 施法 / p.192, 0.901) |

## Still Needs Review

- 暂无强制复核项。
