# PHB 章节数据覆盖审计

生成时间：`2026-06-03`

## 背景

本轮优化原本计划补强 PHB 第十章相关规则，因为多跳评测中出现了典型缺口：

- `附赠动作施法 + 准备法术`
- `静默施法 + 反制法术`
- `专注受伤害是否自动中断`

审计目标是区分两类问题：

- 数据源里有规则，但 adapter 没读到。
- 当前本地授权数据确实缺少完整章节正文。

## 本地数据发现

当前 `data/fvtt-cn-5etools/data` 下没有完整 `book-phb` 或 PHB 章节文件。本地只发现了 PHB 相关分类文件：

```text
data/fvtt-cn-5etools/data/bestiary/bestiary-phb.json
data/fvtt-cn-5etools/data/spells/spells-phb.json
```

`conditionsdiseases.json` 的结构为：

```text
condition: 15
disease: 13
status: 1 -> 专注
```

这说明 `专注` 不是数据缺失，而是 adapter 漏读 `status` 键。

## 已修复

### conditionsdiseases.status

已将 `status` 映射为 `conditionsdiseases` 类规则文档。

影响：

- `专注` 作为独立规则文档进入规范化流程。
- “法师挨打后专注会立刻断吗？”现在能召回 `专注` 规则。
- 回答评测中该题 `rag_product` 得分为 `14/14`。

## 仍缺失

### 附赠动作施法限制

当前本地数据中有 `actions.json` 的 `施法` 动作，但没有完整 PHB 第十章中“附赠动作施法后，同一回合其他施法受限”的正文。

当前产品行为：

```text
ready_spell_mechanic -> covered
bonus_action_spell_limit -> missing
```

这是正确的证据缺失暴露，不应让模型凭记忆补答案。

### 可观察施法构材

`静默施法 + 反制法术` 题目前能找到：

- `反制法术`：看见 60 尺内生物施法时触发。
- `精妙法术`：无需姿势或声音构材。

但仍缺少支撑“构材被移除后，施法是否仍可被观察到”的规则证据。下一轮应补充或抽取更细的需求：

```text
spell_component_observability
visible_casting_component
material_component_visibility
```

## 对产品的影响

这次审计的产品意义是：不要把所有失败都归因于 embedding 或模型。

- `专注`：数据存在，读取策略有 bug，应该修 adapter。
- `附赠动作施法限制`：当前本地数据缺少章节正文，应该补数据或保持证据不足。
- `静默施法 + 反制法术`：证据有一部分，但需求拆解还不够细，应该扩展 planner。

## 下一步

- 获取并确认可授权展示的 PHB 章节正文数据。
- 对补入章节做规则章节 chunk，而不是简单长文本切块。
- 重建 full embedding index。
- 将 `bonus_action_spell_limit` 和 `spell_component_observability` 加入多跳回归题。
