# 检索反向优化与噪声记录

这份记录用于归档：全量 embedding 提升了整体指标，但在部分问题上仍然出现 Top1 证据变差、命中证据靠后或语义漂移的情况。

最近更新：`2026-06-03` 新增多跳 `Evidence Planner` 后，复合裁定题可以按证据需求分别检索并合并证据包；社区真实候选题里 `魔法物品 + 反制法术` 这类问题已不再依赖单个 Top1 相似度。

来源报告：

- `docs/evaluations/retrieval-eval-full-seed-comparison.md`
- `docs/evaluations/retrieval-eval-community-real-seed-comparison.md`

## 当前整体结果

| 评测集 | 检索方式 | Recall@8 | MRR | StrictDoc@8 | StrictDocMRR | Primary@1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 全量种子题 | Token Hybrid | 74.19% | 0.5815 | 51.61% | 0.4116 | 45.16% |
| 全量种子题 | Embedding Hybrid | 96.77% | 0.8532 | 96.77% | 0.7349 | 74.19% |
| 社区真实候选题 | Token Hybrid | 100.00% | 0.8542 | 77.78% | 0.5370 | 66.67% |
| 社区真实候选题 | Embedding Hybrid | 100.00% | 1.0000 | 100.00% | 0.9444 | 100.00% |

结论：embedding 整体有效，精确条目名保护修复了 `沉默术`、`反制法术` 这类显式实体被相邻语义压过的问题；多跳 planner 进一步修复了“需要两组以上规则证据”的复合裁定题。后续不能只看聚合指标调参，而要把失败模式归类后一起处理。

补充口径：

- `Recall@8` 是宽松命中：预期文档或预期词任一出现即可命中。
- `StrictDoc@8` 是严格文档命中：只统计命中 gold document 的题目。
- 当 `Recall@8` 高但 `StrictDoc@8` 低时，说明可能存在“语义上挨着了，但证据没真正找对”的问题。

## 全量种子题中的反向或噪声案例

| ID | 现象 | 可能原因 | 下一步 |
| --- | --- | --- | --- |
| `full-tce-chef-short-rest-healing` | Embedding 命中严格 gold，但 Top1 仍是 `治疗师`，不是 `大厨`。 | “短休/回血/生命骰”与核心治疗专长高度重叠；问题没有明确出现“大厨”。 | 增加效果别名，如“做饭/小餐点/厨艺/额外回血 -> 大厨”，并观察是否误伤治疗类问题。 |
| `full-tce-crusher-move-target` | Embedding 命中严格 gold，但 Top1 是 `突刺击`，预期是 `粉碎者`。 | “把目标挪 5 尺”与战技和强制移动规则重叠。 | 对 `钝击` + “哪个专长”做组合特征，提升专长效果 chunk。 |
| `full-tce-crusher-critical-advantage` | 两种方法 Top8 都没有召回 `粉碎者`。 | 自然问法没有出现专长标题，且是条件交互问题。 | 为专长效果生成合成别名，先评估查询扩展再考虑 reranker。 |
| `full-xge-bountiful-luck-reaction` | Embedding 命中严格 gold，但 Top1 是 `半身人`，不是 `慷慨吉运`。 | 问题提到半身人身份，种族页和专长页竞争。 | 当问题询问“专长”时提升专长类别，降低纯种族页权重。 |
| `full-tce-bloodwell-vial-sorcery-points` | 预期证据命中，但 Top1 是相近怪物施法者文本。 | “术士/术法点/小瓶”与怪物施法者文本重叠。 | 对装备/物品类名词做类别加权，并加入“血井瓶/小瓶/术法点恢复”别名。 |
| `full-mm-hydra-extra-reactions` | Embedding Top1 是 `借机攻击`，预期实体是 `海德拉`。 | 问题问“为什么有多个反应”，动作规则压过怪物实体。 | 对“某怪物为什么...”类型保留怪物实体证据。 |
| `full-vgm-flail-snail-antimagic-shell` | Embedding 命中严格 gold，但 Top1 仍是通用施法规则。 | “单体法术弹回施法者”和通用魔法规则相似。 | 增加 `反魔法壳/蜗牛 -> 连枷蜗牛` 别名，并提升怪物 feature chunk。 |

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
| `community-rpgse-silence-verbal-components` | 已修复，Embedding Top1 为 `沉默术`。 | 精确条目名保护和标题召回起效。 | 保留为回归测试，避免后续权重调整再次退化。 |
| `community-rpgse-subtle-counterspell` | 已修复，Embedding Top1 为 `反制法术`，planner 同时要求 `微妙法术` 证据。 | `counterspell`/反制相关别名、精确标题保护和多跳需求合并起效。 | 保留为“超魔机制 + 触发规则”类回归测试。 |
| `community-rpgse-magic-item-counterspell` | 已修复，证据包同时覆盖 `反制法术` 与 `激活物品`。 | 多跳 planner 将问题拆成“反制法术触发条件 + 魔法物品激活机制”。 | 后续用 `Requirement Coverage@K` 和 `Complete Case Rate` 作为正式多跳指标。 |

## 多跳检索补充

来源报告：`docs/evaluations/multihop-retrieval-optimization.md`

新增 `Evidence Planner` 后，系统会先识别复合裁定题中的规则实体和机制概念，再按需求分别检索。例如：

```text
魔法物品 + 反制法术 -> 反制法术触发条件 + 魔法物品激活机制
微妙法术 + 反制法术 -> 反制法术触发条件 + 微妙法术成分机制
盲视 + 隐形 -> 隐形状态规则 + 盲视感官规则
```

这不是单题定制，而是题型级优化：同一套需求生成、需求检索、覆盖率合并逻辑用于多类复合问题。

## 回答质量观察

来源报告：`docs/evaluations/answer-eval-small-sample.md`

| Variant | Avg Total | Wins | Ties | Losses |
| --- | ---: | ---: | ---: | ---: |
| closed_book | 9.62 | 4 | 1 | 3 |
| evidence_only | 12.50 | 5 | 0 | 3 |
| rag_product | 11.75 | 4 | 1 | 3 |

观察：

- `evidence_only` 暂时最高，说明“证据足够时，少发挥反而更稳”。
- `rag_product` 的引用准确度和谨慎性较好，但仍会在部分题目中加入 evidence pack 之外的规则细节。
- `closed_book` 有时回答更完整，但记忆污染明显，不适合作为可追溯规则产品的主要形态。

下一步：

- 回答生成前增加证据覆盖检查：每个关键结论必须能映射到 evidence id。
- 对检索证据不足的问题，强制输出“证据不足 + 需要补充的证据”，而不是让模型凭记忆补完。
- 增加 `claim -> evidence` 自动审计，作为 answer eval 之外的更细粒度指标。

## 下一轮调参原则

先扩充并核验社区真实题，再统一调参。不要为了单个案例手工修一条权重。

优先处理：

- 类别路由：法术、专长、物品、种族、怪物、动作。
- 中文别名和口语昵称。
- 标题/实体召回先于 dense scoring。
- 父子 chunk 扩展权重。
- 在透明加权稳定后，再评估是否引入 reranker。
