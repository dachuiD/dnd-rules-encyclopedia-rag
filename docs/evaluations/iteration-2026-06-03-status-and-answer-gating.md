# 2026-06-03 迭代记录：状态规则入库与回答克制性优化

## 本轮目标

继续优化 RAG 产品在规则裁定题上的可靠性，重点处理三类问题：

- 简单题答案不够直接，容易主动扩展到问题外边界。
- `专注` 通用规则召回不稳定。
- 多跳题能找到部分证据，但缺失证据时需要明确保守回答。

## 做了什么

### 1. 修复 `专注` 数据入库

审计发现本地 `conditionsdiseases.json` 中有：

```text
status -> 专注
```

之前 adapter 只读取 `condition` 和 `disease`，漏掉 `status`。本轮新增：

```text
status -> conditionsdiseases
```

影响：

- `专注` 作为规则文档进入规范化和 chunk 流程。
- “法师挨打后专注会立刻断吗？”可直接召回 `专注` 证据。

### 2. 增加两类证据需求

新增 planner concepts：

- `concentration_damage_rule`：专注期间受到伤害后的体质豁免规则。
- `silence_verbal_component_rule`：沉默术与声音构材/言语成分限制。

这不是单题定制，而是题型级需求拆解：遇到同类问法时都走同一套 evidence requirement 逻辑。

### 3. 收紧 RAG 回答提示词

上一轮评测显示，模型即使拿到正确证据，也会主动补 `特殊感官`、`超魔`、`房规` 等问题外边界，导致记忆污染。

本轮提示词改为：

- 适用条件只能写 evidence pack 明示的信息。
- 容易误判只能写 evidence pack 已出现的误判点。
- 简单问题优先短结论。
- 不为了完整性扩展到其他规则。
- required evidence missing 时必须说证据不足。

### 4. 更新产品模板

本地模板答案里的泛化句：

```text
特殊能力、特殊感官或房规
```

改成更中性的：

```text
额外例外
```

目的是减少简单题里的无端扩写，让用户先获得清晰裁定。

## 评测结果

### 回答质量小样本

报告：`docs/evaluations/answer-eval-small-sample.md`

| Variant | Avg Total | Wins | Ties | Losses |
| --- | ---: | ---: | ---: | ---: |
| closed_book | 11.75 | 7 | 0 | 1 |
| evidence_only | 11.38 | 5 | 0 | 3 |
| rag_product | 12.75 | 6 | 2 | 0 |

关键观察：

- `rag_product` 重新明显超过 `evidence_only`。
- `Memory Contamination` 从 `0.75` 回升到 `1.75`，与 `evidence_only` 持平。
- `专注` 和 `沉默术` 两类简单裁定题均达到 `14/14`。

### 检索对比

社区真实候选题：

| Run | Recall@8 | MRR | StrictDoc@8 | StrictDocMRR | Primary@1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Token Hybrid | 100.00% | 0.9583 | 100.00% | 0.7444 | 83.33% |
| Embedding Hybrid | 100.00% | 1.0000 | 100.00% | 0.9444 | 100.00% |

全量种子题：

| Run | Recall@8 | MRR | StrictDoc@8 | StrictDocMRR | Primary@1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Token Hybrid | 74.19% | 0.5808 | 51.61% | 0.4108 | 45.16% |
| Embedding Hybrid | 96.77% | 0.8532 | 96.77% | 0.7349 | 74.19% |

## 仍然存在的问题

- 本地数据没有完整 `book-phb` 或 PHB 第十章章节正文。
- `附赠动作施法限制` 仍是 required missing，RAG 应保持证据不足，而不是硬答。
- `静默施法 + 反制法术` 还缺“构材被移除后是否仍可观察到施法”的证据需求。
- 全量种子题中仍有 Top1 噪声，尤其是专长、物品、怪物 feature 与通用规则竞争。

## 下一步

- 获取并确认可授权展示的 PHB 章节正文数据。
- 增加 `spell_component_observability` 类多跳需求。
- 对专长、物品、怪物 feature 做类别路由和别名增强。
- 引入 `claim -> evidence` 审计，检查答案每个关键判断是否真的有证据支撑。

## 验证

```text
python3 -m unittest discover -s tests -v
Ran 58 tests in 0.253s
OK

git diff --check
no output
```
