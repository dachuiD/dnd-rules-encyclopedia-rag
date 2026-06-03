# 多跳检索优化记录

生成时间：`2026-06-03`

## 为什么做

单次混合检索适合“查一个规则/条目”的问题，但遇到复合裁定题会不稳定。

典型问题不是只需要一个最相似 chunk，而是需要同时找齐多组证据。例如：

- `用魔法物品施法能被反制法术吗？`
- `法术被超魔静默施法处理后，还能被反制法术反制吗？`
- `有盲视的生物攻击隐形目标，还会因为看不见而有劣势吗？`

这些题的共同结构是：

```text
显式规则实体 + 机制概念 + 条件/例外关系
```

因此这轮不是为某一道题写规则，而是新增一个通用的 `Evidence Planner`：先判断问题需要哪些证据，再分别检索和合并。

## 实现方式

新增模块：`dnd_rag.planner`

核心对象：

- `QueryAnalysis`：识别显式实体、类别词、机制词，以及是否可能是多跳题。
- `EvidenceRequirement`：描述一组必须找到的证据需求。
- `RequirementEvidence`：记录某个需求是否被覆盖，以及对应证据。
- `MultiHopSearchResult`：合并后的证据包、覆盖率、缺失需求。

检索流程从：

```text
query -> hybrid top 8
```

变成：

```text
query
-> QueryAnalysis
-> EvidenceRequirement[]
-> requirement-level hybrid retrieval
-> coverage-aware evidence merge
-> answer/evidence/citation
```

## 当前支持的复合题型

V1 支持以下规则概念，不绑定具体题号：

| 概念 | 触发信号 | 目标证据 |
| --- | --- | --- |
| 反制法术触发条件 | `反制法术` / `counterspell` | `反制法术` |
| 魔法物品激活与施法机制 | `魔法物品` + `施法/法术` | `激活物品` |
| 微妙法术成分机制 | `微妙法术` / `静默施法` / `超魔+静默` | `微妙法术` |
| 隐形状态规则 | `隐形` / `隐身` | `隐形` |
| 盲视感官规则 | `盲视` | `盲视` |

这意味着系统能把一类问题拆开，而不是只修一个句子：

```text
魔法物品 + 反制法术 -> 反制法术触发条件 + 魔法物品激活机制
微妙法术 + 反制法术 -> 反制法术触发条件 + 微妙法术成分机制
盲视 + 隐形 -> 隐形状态规则 + 盲视感官规则
```

## 产品效果

`RagService.ask()` 现在会返回：

- `is_multi_hop`
- `coverage_score`
- `missing_requirements`
- `evidence_requirements`

如果必需证据缺失，直接回答会变保守：

```text
当前证据不足，缺少必要证据：...。不能可靠完成这个复合裁定。
```

这为后续前端的“检索解释面板”提供了更好的材料：用户不仅能看到 Top 证据，还能看到系统认为这道题需要哪些证据，以及哪些证据已经覆盖。

## 评测观察

社区真实候选题重新评测后：

| Run | Recall@8 | MRR | StrictDoc@8 | StrictDocMRR | Primary@1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Token Hybrid | 100.00% | 0.8542 | 77.78% | 0.5370 | 66.67% |
| Embedding Hybrid | 100.00% | 1.0000 | 100.00% | 0.9444 | 100.00% |

代表修复：

- `community-rpgse-magic-item-counterspell` 不再被 `反魔法结界` 抢占；证据包中同时出现 `反制法术` 与 `激活物品`。
- `community-rpgse-subtle-counterspell` 能稳定保留 `反制法术`，并通过 planner 引入 `微妙法术` 作为并列证据需求。
- `community-rpgse-blindsight-invisible-*` 能被识别为 `隐形状态规则 + 盲视感官规则` 的复合题。

全量种子题指标没有回落：

| Run | Recall@8 | MRR | StrictDoc@8 | StrictDocMRR | Primary@1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Embedding Hybrid | 96.77% | 0.8532 | 96.77% | 0.7349 | 74.19% |

这说明 planner 目前触发较克制，没有明显破坏普通单跳题。

## 新指标口径

后续多跳题不能只看 Top1，应增加两类指标：

- `Requirement Coverage@K`：一道题的每个必需证据需求，在 TopK 证据内是否至少命中一条。
- `Complete Case Rate`：一道多跳题的所有必需证据需求是否都被覆盖。

例如：

```text
问题：用魔法物品施法能被反制法术吗？
需求 A：反制法术触发条件 -> covered
需求 B：魔法物品激活机制 -> covered
Complete Case -> yes
```

如果只命中 `反制法术`，但没有命中 `激活物品`，这道题不应算完整通过。

## 后续优化

- 把 `EvidenceRequirement` 写入评测明细，自动计算 `Requirement Coverage@K`。
- 扩展概念库：专长效果、怪物特性、职业能力、状态交互。
- 增加前端展示：折叠的“证据需求覆盖”面板。
- 在回答生成前做 `claim -> evidence` 审计，避免 evidence pack 已覆盖但模型仍凭记忆补充。
