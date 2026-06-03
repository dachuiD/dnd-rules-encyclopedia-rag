# 回答质量优化记录

生成时间：`2026-06-03`

## 问题

上一轮评测里，`rag_product` 还没有明显强于 `evidence_only`。原因不是检索完全无效，而是回答层没有充分利用产品侧结构：

- evidence pack 只有 TopK 证据，没有告诉模型“这道题需要哪些证据”。
- 法术的施法时间、射程、构材、持续时间等结构化字段没有进入 chunk，导致 `反制法术` 缺少“看见 60 尺内生物施法”的关键触发条件。
- 对缺失证据的复杂题，模型容易凭常识补完，或者 evidence-only 直接做过度推理。

## 改动

### 1. 法术结构化规则入 chunk

新增 `spell_metadata` 子 chunk，提取：

- 施法时间
- 反应触发条件
- 射程
- 构材
- 持续时间

代表例子：

```text
反制法术：
施法时间：1反应（在你看见一个距离你60尺以内的生物施放法术时进行）；
射程：60尺；
构材：姿势；
持续时间：立即
```

这让 `subtle counterspell` 这类问题能检索到真正关键的触发条件，而不是只有正文中的“中断施法过程”。

### 2. Evidence Requirements 写入 evidence pack

回答评测现在会把 planner 的需求覆盖表放在证据包顶部：

```text
Evidence Requirements:
- counterspell_trigger | 反制法术触发条件 | required | status=covered
- subtle_spell_mechanic | 微妙法术成分机制 | required | status=covered
```

如果 required requirement 是 `missing`，`rag_product` 必须输出证据不足，而不是补外部规则。

### 3. Prompt 收紧

`rag_product` prompt 新增规则：

- 必须先检查 Evidence Requirements。
- 存在 missing 的 required requirement 时，结论必须是证据不足。
- 适用条件只能写 evidence pack 明示的信息。
- 容易误判只能写 evidence pack 已经出现的误判点。
- 不得补写未被证据支持的 DC、距离、持续时间、职业能力、超魔、专长例外或房规。
- 简单问题优先给短结论，不为了“完整性”主动扩展到问题没有询问、证据需求也没有要求的其他规则边界。

本轮回归发现：如果只写“不要补外部规则”，模型仍会在简单题中主动补 `特殊感官`、`超魔` 等边界；继续收紧后，`Memory Contamination` 从 `0.75` 回升到 `1.75`。

### 4. conditionsdiseases.status 入库

本地数据 `conditionsdiseases.json` 除了 `condition`、`disease`，还有 `status` 键；其中包含 `专注`。

之前 adapter 没有读取 `status`，导致 `专注` 通用规则没有作为独立文档进入索引。现在已将 `status` 映射到 `conditionsdiseases`：

```text
conditionsdiseases.status -> RuleDocument(category=conditionsdiseases, domain=rules)
```

这让“法师挨打后专注会立刻断吗？”这类题可以直接召回 `专注` 规则，而不是被 `地震术`、`停止专注` 等相邻文本带偏。

### 5. 暴露数据缺口

`附赠动作施法 + 准备法术` 这类题需要 PHB 第十章的附赠动作施法限制。但当前授权数据里没有完整 PHB 章节正文，只有 `actions.json` 的简略“施法”动作。

planner 现在会把它标成：

```text
ready_spell_mechanic -> covered
bonus_action_spell_limit -> missing
```

这不是最终答案能力的上限，而是明确暴露数据覆盖缺口：需要后续补齐规则章节正文或授权来源。

## 评测结果

最新 8 题小样本自动评测：

| Variant | Avg Total | Wins | Ties | Losses |
| --- | ---: | ---: | ---: | ---: |
| closed_book | 11.75 | 7 | 0 | 1 |
| evidence_only | 11.38 | 5 | 0 | 3 |
| rag_product | 12.75 | 6 | 2 | 0 |

维度均分：

| Variant | Correctness | Completeness | Evidence | Citation | Caution | Clarity | Memory |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| evidence_only | 1.50 | 1.38 | 1.50 | 1.88 | 1.50 | 1.88 | 1.75 |
| rag_product | 1.75 | 1.75 | 1.88 | 2.00 | 1.88 | 2.00 | 1.75 |

当前结论：

- `rag_product` 已经在小样本上超过 `evidence_only`，但样本量仍小，不能当作最终宣传指标。
- 优势主要来自复杂题：RAG 能利用结构化证据和需求覆盖表，避免 evidence-only 的过度推理。
- `Memory` 分数已与 `evidence_only` 持平，但仍要继续做 `claim -> evidence` 审计，因为部分多跳题仍会出现证据外推理。

## 代表题

### `community-rpgse-subtle-counterspell`

改动后 evidence pack 同时包含：

- `反制法术` 的反应触发条件：需要看见 60 尺内生物施法。
- `精妙法术`：无需姿势或声音构材。

`rag_product` 当前得分：`9/14`。

原因不是检索完全失败，而是证据需求还不够细：现有证据包覆盖了 `反制法术` 和 `精妙法术`，但缺少“被移除构材后施法是否仍可被观察到”的支撑规则。下一轮应补充 `spell_component_observability` 或 `visible_casting_component` 类需求。

### `community-rpgse-ready-bonus-action-spell`

当前 evidence pack 明确显示：

- `准备法术机制`：covered
- `附赠动作施法限制`：missing

`rag_product` 没有硬答，而是指出证据不足；自动评测给出 `10/14`。这个分数低于上一轮，但产品行为更合理：缺少关键规则时宁可保守，也不凭模型记忆补答案。

### `core-concentration-not-auto-break`

`conditionsdiseases.status` 入库后，证据包直接覆盖：

- `专注`：受到伤害后进行体质豁免，成功维持，失败中断。

`rag_product` 当前得分：`14/14`。

### `core-silence-verbal-spell`

新增 `silence_verbal_component_rule` 后，证据包集中到：

- `沉默术`：范围内不可能施放需要声音构材的法术。

`rag_product` 当前得分：`14/14`。这说明“检索需求聚焦 + 回答克制”对简单规则裁定题有效。

## 后续

- 补齐 PHB 第十章规则章节正文，特别是施法、构材、附赠动作施法限制、可观察施法构材等内容。
- 为新增 `spell_metadata` chunk 重新跑 embedding，避免长期依赖 lexical fallback。
- 增加 `claim -> evidence` 自动审计，进一步降低 memory contamination。
- 扩大 answer eval 样本，单独统计简单查找题、复合裁定题、证据缺失题三类表现。
