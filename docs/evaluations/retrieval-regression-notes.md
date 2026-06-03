# 检索反向优化与噪声记录

这份记录用于归档：全量 embedding 提升了整体指标，但在部分问题上仍然出现 Top1 证据变差、命中证据靠后或语义漂移的情况。

来源报告：

- `docs/evaluations/retrieval-eval-full-seed-comparison.md`
- `docs/evaluations/retrieval-eval-community-real-seed-comparison.md`

## 当前整体结果

| 评测集 | 检索方式 | Recall@8 | MRR | StrictDoc@8 | StrictDocMRR | Primary@1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 全量种子题 | Token Hybrid | 70.97% | 0.5393 | 38.71% | 0.3353 | 45.16% |
| 全量种子题 | Embedding Hybrid | 93.55% | 0.8306 | 87.10% | 0.6847 | 74.19% |
| 社区真实候选题 | Token Hybrid | 83.33% | 0.7917 | 55.56% | 0.3000 | 50.00% |
| 社区真实候选题 | Embedding Hybrid | 91.67% | 0.8125 | 88.89% | 0.6667 | 75.00% |

结论：embedding 整体有效，但不是每道题都变好。后续不能只看聚合指标调参，而要把失败模式归类后一起处理。

补充口径：

- `Recall@8` 是宽松命中：预期文档或预期词任一出现即可命中。
- `StrictDoc@8` 是严格文档命中：只统计命中 gold document 的题目。
- 当 `Recall@8` 高但 `StrictDoc@8` 低时，说明可能存在“语义上挨着了，但证据没真正找对”的问题。

## 全量种子题中的反向或噪声案例

| ID | 现象 | 可能原因 | 下一步 |
| --- | --- | --- | --- |
| `full-egw-gift-of-alacrity-initiative` | Embedding Top1 是 `激活物品`，预期是 `灵敏之赐`。 | 问题描述了效果但没有点名法术，通用动作 chunk 被语义召回。 | 对“先攻 + 1d8”做查询改写，给法术标题和实体候选加权。 |
| `full-tce-chef-short-rest-healing` | Token 和 embedding 都偏向 `治疗师`，`大厨` 在 embedding 中排第 2。 | “短休/回血/生命骰”与核心治疗专长高度重叠。 | 当问题询问“哪个专长”时提升专长类别权重。 |
| `full-tce-crusher-move-target` | Embedding Top1 是 `突刺击`，预期是 `粉碎者`。 | “把目标挪 5 尺”与战技和强制移动规则重叠。 | 对 `钝击` + 专长标题/别名增加精确加权。 |
| `full-tce-crusher-critical-advantage` | 两种方法 Top8 都没有召回 `粉碎者`。 | 自然问法没有出现专长标题，且是条件交互问题。 | 为专长效果生成合成别名，先评估查询扩展再考虑 reranker。 |
| `full-xge-bountiful-luck-reaction` | Embedding 排名改善，但 Top1 是 `半身人`，不是 `慷慨吉运`。 | 问题提到半身人身份，种族页和专长页竞争。 | 当问题询问“专长”时提升专长类别，降低纯种族页权重。 |
| `full-tce-bloodwell-vial-sorcery-points` | 预期证据命中，但第一个命中在第 4。 | “术士/术法点/小瓶”与怪物施法者文本重叠。 | 对装备/物品类名词做类别加权。 |
| `full-vrgr-dhampir-no-breath` | Embedding 从弱命中退化为未命中，Top1 是 `吸血鬼`。 | 用户说法接近“吸血鬼味儿族系”，语义漂移到怪物条目。 | 增加 `吸血鬼味儿族系 -> 半血裔` 这类口语别名。 |
| `full-mm-hydra-extra-reactions` | Embedding Top1 是 `借机攻击`，预期实体是 `海德拉`。 | 问题问“为什么有多个反应”，动作规则压过怪物实体。 | 对“某怪物为什么...”类型保留怪物实体证据。 |
| `full-vgm-flail-snail-antimagic-shell` | Embedding 改善排名，但 Top1 是 `激活物品`，`连枷蜗牛` 在第 3。 | “单体法术弹回施法者”和物品激活、魔法语言相似。 | 增加 `反魔法壳/蜗牛 -> 连枷蜗牛` 别名，并提升怪物 feature chunk。 |

## 社区真实候选题审计状态

第一批社区题：`eval/community_real_seed.json`

这批题目前只能作为压力测试和失败模式发现，不能作为最终产品质量 benchmark。原因如下：

- `source_status` 仍是 `candidate_unverified`，说明来源还没有逐题人工核验。
- 当前 `Recall@8` 是宽松指标：Top8 中任一候选包含预期文档或预期词，就会计为命中。
- 当前已增加 `StrictDoc@8`，用来单独观察 gold document 是否真的被召回。
- 因此可能出现 Top1 明显不理想，但 Recall@8 仍然命中的情况。
- 部分早期 `expected_terms` 过宽，例如施法、反应、构材、激活等词，会匹配到相邻但不充分的证据。

当前解释口径：

- 可以说：这批题暴露了真实社区问法下的检索噪声。
- 不能说：这批题已经证明产品最终回答质量显著优于通用大模型。

## 社区题代表问题

| ID | 现象 | 可能原因 | 下一步 |
| --- | --- | --- | --- |
| `community-rpgse-silence-verbal-components` | 两种系统都召回 `触发术`，但预期应是 `沉默术`。 | 问题包含“语言成分/不能施放”，但标题召回没有强制命中 `沉默术`。 | 增加 `沉默/无声/声音/语言成分 -> 沉默术` 的标题和别名触发。 |
| `community-rpgse-subtle-counterspell` | 预期 `反制法术`，但 Top1 是 `反魔法结界`。 | “反制/静默/施法”语义与反魔法概念重叠。 | 增加 `counterspell -> 反制法术`、`subtle spell -> 微妙法术/静默施法` 的别名表。 |
| `community-rpgse-magic-item-counterspell` | 预期 `反制法术` + `激活物品`，但 Top1 是 `反魔法结界`。 | 魔法物品激活和反魔法语义竞争。 | 将多跳问题拆成两个证据需求：法术规则 + 物品激活规则。 |

## 下一轮调参原则

先扩充并核验社区真实题，再统一调参。不要为了单个案例手工修一条权重。

优先处理：

- 类别路由：法术、专长、物品、种族、怪物、动作。
- 中文别名和口语昵称。
- 标题/实体召回先于 dense scoring。
- 父子 chunk 扩展权重。
- 在透明加权稳定后，再评估是否引入 reranker。
