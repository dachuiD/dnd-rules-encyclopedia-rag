# 社区真实候选题 Token vs Embedding 检索审阅

## Metadata

- Generated at: `2026-06-03T10:04:47+08:00`
- Dataset: `eval/community_real_seed.json`
- Data dir: `data/fvtt-cn-5etools/data`
- Embedding index: `storage/embedding-index/full.jsonl`

## 审计结论

这份报告目前只能作为候选压力测试，不能作为最终产品效果证明。

原因：

- 12 道题的 `source_status` 都是 `candidate_unverified`，社区来源还没有逐题人工核验。
- 当前 `Recall@8` 是宽松指标，只要 Top8 里出现预期文档或预期词，就会算命中。
- 因此可能出现 Top1 不理想但整体指标仍显示“改善”的情况。
- `community-rpgse-subtle-counterspell` 和 `community-rpgse-magic-item-counterspell` 就属于需要重点复核的案例：Top1 是 `反魔法结界`，但预期核心证据应包含 `反制法术`。

当前可接受的使用方式：观察 embedding 是否整体改善召回，并收集失败类型。

当前不可接受的使用方式：直接声明产品已经在社区真实题上显著优于通用大模型。

## Metrics

| Run | Total | Recall@8 | MRR | Primary@1 |
| --- | ---: | ---: | ---: | ---: |
| Token Hybrid | 12 | 83.33% | 0.7917 | 0.5000 |
| Embedding Hybrid | 12 | 91.67% | 0.8125 | 0.7500 |
| Delta | - | +8.33% | +0.0208 | +0.2500 |

## Changed Questions

| ID | 问题 | 变化 | Token Top1 | Embedding Top1 |
| --- | --- | --- | --- | --- |
| community-rpgse-ready-spell-concentration | 准备一个法术是不是要先开始专注？如果准备的是本来就需要专注的法术，会不会冲突？ | 变化：Top1 证据不同 | 准备 (PHB / actions / 准备 / p.193, 0.863) | 准备 (PHB / actions / 准备 / p.193, 0.869) |
| community-rpgse-ready-cantrip | 准备一个戏法也要专注吗？ | 改善：Top1 命中核心证据 | 巫妖 (MM / bestiary / 巫妖 / p.202, 0.775) | 准备 (PHB / actions / 准备 / p.193, 0.800) |
| community-rpgse-ready-bonus-action-spell | 如果我这回合已经用附赠动作施法，还能用动作准备另一个法术吗？ | 变化：Top1 证据不同 | 祭司 (MM / bestiary / 祭司 / p.348, 0.681) | 准备 (PHB / actions / 准备 / p.193, 0.836) |
| community-rpgse-blindsight-invisible-disadvantage | 有盲视的生物攻击隐形目标，还会因为看不见而有劣势吗？ | 改善：Top1 命中核心证据 | 降咒 (PHB / spells / 降咒 / p.218, 0.680) | 隐形 (PHB / conditions / 隐形 / p.291, 0.746) |
| community-rpgse-blindsight-detect-invisible | 盲视能不能发现隐形生物的位置？ | 变化：Top1 证据不同 | 隐形 (PHB / conditions / 隐形 / p.291, 0.815) | 隐形 (PHB / conditions / 隐形 / p.291, 0.882) |
| community-rpgse-silence-verbal-components | 沉默术范围里，带语言成分的法术是不是完全不能施放？ | 退步：从命中到未命中 | 触发术 (PHB / spells / 触发术 / p.227, 0.742) | 触发术 (PHB / spells / 触发术 / p.227, 0.719) |
| community-rpgse-subtle-counterspell | 法术被超魔静默施法处理后，还能被反制法术反制吗？ | 改善：从未命中到命中 | 反魔法结界 (PHB / spells / 反魔法结界 / p.213, 0.789) | 反魔法结界 (PHB / spells / 反魔法结界 / p.213, 0.766) |
| community-rpgse-magic-item-counterspell | 用魔法物品施法能被反制法术吗？ | 改善：从未命中到命中 | 反魔法结界 (PHB / spells / 反魔法结界 / p.213, 0.667) | 反魔法结界 (PHB / spells / 反魔法结界 / p.213, 0.769) |
| community-rpgse-grapple-shove-prone | 能不能先擒抱再推倒伏地，让目标站不起来？ | 变化：Top1 证据不同 | 水巨灵(玛利德) (MM / bestiary / 水巨灵(玛利德) / p.146, 0.711) | 擒抱 (PHB / actions / 擒抱 / p.195, 0.700) |
| community-rpgse-shove-out-of-grapple | 把擒抱者推开，能不能解除擒抱？ | 变化：Top1 证据不同 | 被擒 (PHB / conditions / 被擒 / p.290, 0.800) | 被擒 (PHB / conditions / 被擒 / p.290, 0.742) |
| community-rpgse-prone-ranged-attack | 攻击伏地目标时，远程攻击为什么经常反而有劣势？ | 改善：Top1 命中核心证据 | 闪电箭矢 (PHB / spells / 闪电箭矢 / p.255, 0.749) | 伏地 (PHB / conditions / 伏地 / p.292, 0.780) |
| community-rpgse-bonus-action-spell-order | 附赠动作施法的限制和施法顺序有关吗？ | 变化：Top1 证据不同 | 施法 (PHB / actions / 施法 / p.192, 0.665) | 施法 (PHB / actions / 施法 / p.192, 0.801) |

## Still Needs Review

- `community-rpgse-silence-verbal-components`：Embedding 仍需复核。Token Top1: 触发术 (PHB / spells / 触发术 / p.227, 0.742)；Embedding Top1: 触发术 (PHB / spells / 触发术 / p.227, 0.719)
- `community-rpgse-subtle-counterspell`：Embedding 仍需复核。Token Top1: 反魔法结界 (PHB / spells / 反魔法结界 / p.213, 0.789)；Embedding Top1: 反魔法结界 (PHB / spells / 反魔法结界 / p.213, 0.766)
- `community-rpgse-magic-item-counterspell`：Embedding 仍需复核。Token Top1: 反魔法结界 (PHB / spells / 反魔法结界 / p.213, 0.667)；Embedding Top1: 反魔法结界 (PHB / spells / 反魔法结界 / p.213, 0.769)
