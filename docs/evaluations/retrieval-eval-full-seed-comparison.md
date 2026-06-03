# 全量种子题 Token vs Embedding 检索审阅

## Metadata

- Generated at: `2026-06-03T15:49:50+08:00`
- Dataset: `eval/golden_full_seed.json`
- Data dir: `data/fvtt-cn-5etools/data`
- Embedding index: `storage/embedding-index/full.jsonl`

## Metrics

| Run | Total | Recall@8 | MRR | StrictDoc@8 | StrictDocMRR | Primary@1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Token Hybrid | 31 | 74.19% | 0.5815 | 51.61% | 0.4116 | 0.4516 |
| Embedding Hybrid | 31 | 96.77% | 0.8532 | 96.77% | 0.7349 | 0.7419 |
| Delta | - | +22.58% | +0.2717 | +45.16% | +0.3233 | +0.2903 |

说明：`Recall@K` 是宽松命中；`StrictDoc@K` 只统计 gold document 命中，更适合判断证据是否真的找对。

## Changed Questions

| ID | 问题 | 变化 | Token Top1 | Embedding Top1 |
| --- | --- | --- | --- | --- |
| full-egw-fortunes-favor-extra-d20 | 命运宠儿能不能让一次检定多掷一个 d20？ | 变化：Top1 证据不同 | 命运宠儿 (EGW / spells / 命运宠儿 / p.186, 0.906) | 命运宠儿 (EGW / spells / 命运宠儿 / p.186, 0.986) |
| full-egw-fortunes-favor-upcast-targets | 命运宠儿升环会增加什么？ | 变化：Top1 证据不同 | 命运宠儿 (EGW / spells / 命运宠儿 / p.186, 0.919) | 命运宠儿 (EGW / spells / 命运宠儿 / p.186, 0.934) |
| full-egw-immovable-object-weight | 哪个法术能把一个 10 磅以内的小物件固定住？ | 改善：命中严格 gold document | 法术无效结界 (PHB / spells / 法术无效结界 / p.245, 0.752) | 不动物件 (EGW / spells / 不动物件 / p.187, 0.739) |
| full-egw-pulse-wave-push-pull | 那个 30 尺锥形力场法术是把人推开还是拉近？ | 改善：命中严格 gold document | Madness (DMG / variantrules / Madness / p.258, 0.605) | 脉冲波动 (EGW / spells / 脉冲波动 / p.188, 0.722) |
| full-egw-dark-star-verbal-spells | 扩展里的魔法黑暗重力区域会不会阻止有语言成分的施法？ | 改善：命中严格 gold document | 劣魔 (MM / bestiary / 劣魔 / p.76, 0.670) | 施法 (PHB / actions / 施法 / p.192, 0.744) |
| full-egw-ravenous-void-restraint | 饕餮虚空会不会束缚进入力场的生物？ | 变化：Top1 证据不同 | 饕餮虚空 (EGW / spells / 饕餮虚空 / p.188, 0.906) | 饕餮虚空 (EGW / spells / 饕餮虚空 / p.188, 0.986) |
| full-tce-chef-short-rest-healing | 哪个专长能在短休做饭，让花生命骰的人额外回血？ | 改善：命中严格 gold document | 治疗师 (PHB / feats / 治疗师 / p.167, 0.719) | 治疗师 (PHB / feats / 治疗师 / p.167, 0.773) |
| full-tce-chef-treat-temp-hp | 厨艺相关专长做的小餐点给多少临时生命值？ | 改善：命中严格 gold document | 摹造生命 (PHB / spells / 摹造生命 / p.239, 0.700) | 大厨 (TCE / feats / 大厨 / p.79, 0.788) |
| full-tce-crusher-move-target | 造成钝击伤害命中后，哪个专长能每回合把目标挪 5 尺？ | 改善：命中严格 gold document | 蟹 (MM / bestiary / 蟹 / p.320, 0.653) | 突刺击 (PHB / optionalfeatures / 突刺击 / p.74, 0.653) |
| full-tce-crusher-critical-advantage | 钝击重击以后，其他人攻击这个目标会有优势吗？ | 变化：Top1 证据不同 | 海豚 (VGM / bestiary / 海豚 / p.208, 0.636) | 攻击 (PHB / actions / 攻击 / p.192, 0.688) |
| full-xge-bountiful-luck-reaction | 半身人有没有专长可以用反应帮队友把 d20 的 1 重掷？ | 改善：命中严格 gold document | 扁瓶 (PHB / items / 扁瓶 / p.153, 0.617) | 半身人 (PHB / races / 半身人 / p.26, 0.867) |
| full-tce-artificer-initiate-tool-focus | 奇械学徒选的工具能不能当施法法器？ | 变化：Top1 证据不同 | 奇械学徒 (TCE / feats / 奇械学徒 / p.79, 0.752) | 奇械学徒 (TCE / feats / 奇械学徒 / p.79, 0.981) |
| full-tce-all-purpose-tool-transform | 奇械师那把魔法螺丝刀能不能变成别的工匠工具？ | 改善：命中严格 gold document | 玻璃匠工具 (PHB / items / 玻璃匠工具 / p.154, 0.683) | +3 万能工具 (TCE / items / +3 万能工具 / p.119, 0.736) |
| full-tce-all-purpose-tool-cantrip | 万能工具可以临时学一个戏法吗？ | 改善：命中严格 gold document | 甲虫群 (MM / bestiary / 甲虫群 / p.338, 0.649) | +3 万能工具 (TCE / items / +3 万能工具 / p.119, 0.736) |
| full-tce-amulet-devout-channel-divinity | 虔信护符能额外用一次引导神力吗？ | 改善：Rank 4 -> 2 | 护符 (PHB / items / 护符 / p.151, 0.900) | 护符 (PHB / items / 护符 / p.151, 0.784) |
| full-tce-bloodwell-vial-sorcery-points | 术士那个装血的小瓶怎么恢复术法点？ | 改善：命中严格 gold document | 术士 (PHB / class / 术士 / p.99, 0.900) | 狗头人鳞术士 (VGM / bestiary / 狗头人鳞术士 / p.167, 0.792) |
| full-tce-moon-sickle-healing-d4 | 月镰会增强治疗法术吗？ | 改善：Top1 命中核心证据 | 治愈精魂 (XGE / spells / 治愈精魂 / p.157, 0.788) | +1 月镰 (TCE / items / +1 月镰 / p.133, 0.736) |
| full-tce-bait-and-switch-no-opportunity | 战技里和队友互换位置的那招会吃借机攻击吗？ | 变化：Top1 证据不同 | 诱饵战术 (TCE / optionalfeatures / 诱饵战术 / p.42, 0.744) | 借机攻击 (PHB / actions / 借机攻击 / p.195, 0.900) |
| full-tce-ambush-superiority-die | 突袭战技能把卓越骰加到什么检定？ | 改善：命中严格 gold document | 领导风范 (TCE / optionalfeatures / 领导风范 / p.42, 0.788) | 突袭 (TCE / optionalfeatures / 突袭 / p.42, 0.886) |
| full-xge-banishing-arrow-save-effect | 奥术射手把人暂时送去妖精荒野的箭，要目标过什么豁免？ | 改善：命中严格 gold document | 妖精龙(蓝) (MM / bestiary / 妖精龙(蓝) / p.133, 0.683) | 放逐箭 (XGE / optionalfeatures / 放逐箭 / p.29, 0.736) |
| full-tce-custom-lineage-feat | 塔莎的自定义种族在 1 级能直接选一个专长吗？ | 改善：Top1 命中核心证据 | 塑水 (XGE / spells / 塑水 / p.164, 0.669) | 自定血统 (TCE / races / 自定血统 / p.8, 0.784) |
| full-vrgr-dhampir-no-breath | 范瑞ichten里的吸血鬼味儿族系还需要呼吸吗？ | 变化：Top1 证据不同 | 半血裔 (VRGR / races / 半血裔 / p.16, 0.836) | 半血裔 (VRGR / races / 半血裔 / p.16, 0.986) |
| full-eepc-aarakocra-flight-armor | 那个鸟人种族穿中甲或重甲还能飞吗？ | 改善：Top1 命中核心证据 | 重度着甲 (PHB / feats / 重度着甲 / p.167, 0.650) | 阿兰寇拉鹰人 (EEPC / races / 阿兰寇拉鹰人 / p.5, 0.774) |
| full-mm-hydra-extra-reactions | 多头怪为什么可以有不止一个借机攻击反应？ | 改善：命中严格 gold document | 借机攻击 (PHB / actions / 借机攻击 / p.195, 0.755) | 借机攻击 (PHB / actions / 借机攻击 / p.195, 0.977) |
| full-vgm-flail-snail-antimagic-shell | 那个有反魔法壳的蜗牛会不会把单体法术弹回施法者？ | 改善：命中严格 gold document | 魔法飞弹 (PHB / spells / 魔法飞弹 / p.257, 0.656) | 施法 (PHB / actions / 施法 / p.192, 0.772) |

## Still Needs Review

- `full-egw-dark-star-verbal-spells`：Embedding 仍需复核。Token Top1: 劣魔 (MM / bestiary / 劣魔 / p.76, 0.670)；Embedding Top1: 施法 (PHB / actions / 施法 / p.192, 0.744)
- `full-tce-chef-short-rest-healing`：Embedding 仍需复核。Token Top1: 治疗师 (PHB / feats / 治疗师 / p.167, 0.719)；Embedding Top1: 治疗师 (PHB / feats / 治疗师 / p.167, 0.773)
- `full-tce-crusher-move-target`：Embedding 仍需复核。Token Top1: 蟹 (MM / bestiary / 蟹 / p.320, 0.653)；Embedding Top1: 突刺击 (PHB / optionalfeatures / 突刺击 / p.74, 0.653)
- `full-tce-crusher-critical-advantage`：Embedding 仍需复核。Token Top1: 海豚 (VGM / bestiary / 海豚 / p.208, 0.636)；Embedding Top1: 攻击 (PHB / actions / 攻击 / p.192, 0.688)
- `full-xge-bountiful-luck-reaction`：Embedding 仍需复核。Token Top1: 扁瓶 (PHB / items / 扁瓶 / p.153, 0.617)；Embedding Top1: 半身人 (PHB / races / 半身人 / p.26, 0.867)
- `full-tce-amulet-devout-channel-divinity`：Embedding 仍需复核。Token Top1: 护符 (PHB / items / 护符 / p.151, 0.900)；Embedding Top1: 护符 (PHB / items / 护符 / p.151, 0.784)
- `full-tce-bloodwell-vial-sorcery-points`：Embedding 仍需复核。Token Top1: 术士 (PHB / class / 术士 / p.99, 0.900)；Embedding Top1: 狗头人鳞术士 (VGM / bestiary / 狗头人鳞术士 / p.167, 0.792)
- `full-mm-hydra-extra-reactions`：Embedding 仍需复核。Token Top1: 借机攻击 (PHB / actions / 借机攻击 / p.195, 0.755)；Embedding Top1: 借机攻击 (PHB / actions / 借机攻击 / p.195, 0.977)
- `full-vgm-flail-snail-antimagic-shell`：Embedding 仍需复核。Token Top1: 魔法飞弹 (PHB / spells / 魔法飞弹 / p.257, 0.656)；Embedding Top1: 施法 (PHB / actions / 施法 / p.192, 0.772)
