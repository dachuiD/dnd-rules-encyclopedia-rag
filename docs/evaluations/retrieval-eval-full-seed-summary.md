# Full Seed Retrieval Review

## Metadata

- Generated at: `2026-06-02T23:31:46+08:00`
- Dataset: `eval/golden_full_seed.json`
- Data dir: `data/fvtt-cn-5etools/data`
- Embedding index: `storage/embedding-index/full.jsonl`

## Metrics

| Run | Total | Recall@8 | MRR | Primary@1 |
| --- | ---: | ---: | ---: | ---: |
| Embedding Hybrid | 31 | 93.55% | 0.8306 | 0.7419 |

## Review Table

| ID | 问题 | 参考答案 | Hit | Rank | Primary@1 | Top1 | Top3 |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| full-egw-fortunes-favor-extra-d20 | 命运宠儿能不能让一次检定多掷一个 d20？ | 可以。命运宠儿可以在攻击检定、属性检定或豁免检定时结束法术并掷一颗额外的 d20，再决定使用哪颗。 | Y | 1 | Y | 命运宠儿 (EGW / spells / 命运宠儿 / p.186, 0.886) | 命运宠儿 (EGW / spells / 命运宠儿 / p.186, 0.886)<br>命运宠儿 (EGW / spells / 命运宠儿 / p.186, 0.780)<br>命运宠儿 (EGW / spells / 命运宠儿 / p.186, 0.780) |
| full-egw-fortunes-favor-upcast-targets | 命运宠儿升环会增加什么？ | 使用三环或更高法术位施放命运宠儿时，每比二环高一环可以额外指定一个生物。 | Y | 1 | Y | 命运宠儿 (EGW / spells / 命运宠儿 / p.186, 0.834) | 命运宠儿 (EGW / spells / 命运宠儿 / p.186, 0.834)<br>命运宠儿 (EGW / spells / 命运宠儿 / p.186, 0.819)<br>命运宠儿 (EGW / spells / 命运宠儿 / p.186, 0.734) |
| full-egw-gift-of-alacrity-initiative | 有没有扩展法术能让先攻多加 1d8？ | 灵敏之赐让被触碰的自愿生物在法术持续时间内，先攻掷骰加入额外的 1d8。 | Y | 3 | N | 激活物品 (DMG / actions / 激活物品 / p.141, 0.741) | 激活物品 (DMG / actions / 激活物品 / p.141, 0.741)<br>激活物品 (DMG / actions / 激活物品 / p.141, 0.711)<br>西风打击 (XGE / spells / 西风打击 / p.171, 0.703) |
| full-egw-immovable-object-weight | 哪个法术能把一个 10 磅以内的小物件固定住？ | 不动物件的目标物件至多不超过 10 磅；若固定在空中，基础情况下可承载至多 4000 磅。 | Y | 1 | Y | 不动物件 (EGW / spells / 不动物件 / p.187, 0.686) | 不动物件 (EGW / spells / 不动物件 / p.187, 0.686)<br>法师之手 (PHB / spells / 法师之手 / p.256, 0.654)<br>地动术 (PHB / spells / 地动术 / p.263, 0.651) |
| full-egw-immovable-object-password | 不动物件能设置密码临时解除吗？ | 可以。你可以设置一串密码，在物件 5 尺内念出时，使不动物件暂时被压制 1 分钟。 | Y | 1 | Y | 不动物件 (EGW / spells / 不动物件 / p.187, 0.886) | 不动物件 (EGW / spells / 不动物件 / p.187, 0.886)<br>不动物件 (EGW / spells / 不动物件 / p.187, 0.815)<br>不动物件 (EGW / spells / 不动物件 / p.187, 0.803) |
| full-egw-magnify-gravity-save-damage | 扩大重力失败豁免会发生什么？ | 扩大重力要求体质豁免；失败会受到 2d8 力场伤害，并且移动速度到下个回合结束前减半。 | Y | 1 | Y | 扩大重力 (EGW / spells / 扩大重力 / p.188, 0.886) | 扩大重力 (EGW / spells / 扩大重力 / p.188, 0.886)<br>扩大重力 (EGW / spells / 扩大重力 / p.188, 0.835)<br>扩大重力 (EGW / spells / 扩大重力 / p.188, 0.780) |
| full-egw-pulse-wave-push-pull | 那个 30 尺锥形力场法术是把人推开还是拉近？ | 施放脉冲波动时由施法者选择推开或拉近。失败豁免的生物会被推开 15 尺或拉近 15 尺。 | Y | 1 | Y | 脉冲波动 (EGW / spells / 脉冲波动 / p.188, 0.669) | 脉冲波动 (EGW / spells / 脉冲波动 / p.188, 0.669)<br>恐惧魔杖 (DMG / items / 恐惧魔杖 / p.210, 0.638)<br>反魔法结界 (PHB / spells / 反魔法结界 / p.213, 0.635) |
| full-egw-reality-break-reactions | 崩坏现实会不会让目标不能用反应？ | 会。目标若未通过感知豁免，将无法执行任何反应直到法术结束。 | Y | 1 | Y | 崩坏现实 (EGW / spells / 崩坏现实 / p.189, 0.836) | 崩坏现实 (EGW / spells / 崩坏现实 / p.189, 0.836)<br>崩坏现实 (EGW / spells / 崩坏现实 / p.189, 0.820)<br>崩坏现实 (EGW / spells / 崩坏现实 / p.189, 0.804) |
| full-egw-dark-star-verbal-spells | 扩展里的魔法黑暗重力区域会不会阻止有语言成分的施法？ | 不能。黑暗星辰影响范围内没有办法施展需要语言成分的法术。 | Y | 1 | Y | 黑暗星辰 (EGW / spells / 黑暗星辰 / p.186, 0.711) | 黑暗星辰 (EGW / spells / 黑暗星辰 / p.186, 0.711)<br>圣居 (PHB / spells / 圣居 / p.249, 0.704)<br>圣居 (PHB / spells / 圣居 / p.249, 0.647) |
| full-egw-ravenous-void-restraint | 饕餮虚空会不会束缚进入力场的生物？ | 会。生物第一次进入力场或在力场内开始回合时会受到力场伤害并被束缚，直到离开力场范围。 | Y | 1 | Y | 饕餮虚空 (EGW / spells / 饕餮虚空 / p.188, 0.886) | 饕餮虚空 (EGW / spells / 饕餮虚空 / p.188, 0.886)<br>饕餮虚空 (EGW / spells / 饕餮虚空 / p.188, 0.815)<br>饕餮虚空 (EGW / spells / 饕餮虚空 / p.188, 0.769) |
| full-tce-chef-short-rest-healing | 哪个专长能在短休做饭，让花生命骰的人额外回血？ | 可以。短休结束时，吃了特制料理并花费生命骰恢复生命值的生物，会额外恢复 1d8 生命值。 | Y | 1 | N | 治疗师 (PHB / feats / 治疗师 / p.167, 0.720) | 治疗师 (PHB / feats / 治疗师 / p.167, 0.720)<br>大厨 (TCE / feats / 大厨 / p.79, 0.669)<br>疗愈 (DMG / actions / 疗愈 / p.266, 0.668) |
| full-tce-chef-treat-temp-hp | 厨艺相关专长做的小餐点给多少临时生命值？ | 大厨制作的餐点数量等同于熟练加值，食用者获得等同于熟练加值的临时生命值。 | Y | 1 | Y | 大厨 (TCE / feats / 大厨 / p.79, 0.736) | 大厨 (TCE / feats / 大厨 / p.79, 0.736)<br>摹造生命 (PHB / spells / 摹造生命 / p.239, 0.620)<br>黑刃 (DMG / items / 黑刃 / p.216, 0.594) |
| full-tce-crusher-move-target | 造成钝击伤害命中后，哪个专长能每回合把目标挪 5 尺？ | 每回合一次，用造成钝击伤害的攻击命中时，若目标体型没有比你大一级以上，可以将目标移动 5 尺到未被占据空间。 | Y | 2 | N | 突刺击 (PHB / optionalfeatures / 突刺击 / p.74, 0.653) | 突刺击 (PHB / optionalfeatures / 突刺击 / p.74, 0.653)<br>徒手格斗 (TCE / optionalfeatures / 徒手格斗 / p.42, 0.627)<br>祭司 (MM / bestiary / 祭司 / p.348, 0.610) |
| full-tce-crusher-critical-advantage | 钝击重击以后，其他人攻击这个目标会有优势吗？ | 有。用造成钝击伤害的攻击重击一个生物后，直到你的下一回合开始，所有针对该生物的攻击检定具有优势。 | N | - | N | 易伤护甲（钝击） (DMG / items / 易伤护甲（钝击） / p.152, 0.595) | 易伤护甲（钝击） (DMG / items / 易伤护甲（钝击） / p.152, 0.595)<br>攻击 (PHB / actions / 攻击 / p.192, 0.588)<br>攻击 (PHB / actions / 攻击 / p.192, 0.588) |
| full-xge-bountiful-luck-reaction | 半身人有没有专长可以用反应帮队友把 d20 的 1 重掷？ | 可以。30 尺内可见队友在攻击检定、能力检定或豁免检定的 d20 骰出 1 时，你可以用反应让其重掷。 | Y | 3 | N | 半身人 (PHB / races / 半身人 / p.26, 0.767) | 半身人 (PHB / races / 半身人 / p.26, 0.767)<br>胡狼人 (PSA / races / 胡狼人 / p.17, 0.588)<br>达文-纳之牙 (TCE / items / 达文-纳之牙 / p.135, 0.584) |
| full-tce-artificer-initiate-tool-focus | 奇械学徒选的工具能不能当施法法器？ | 可以。奇械学徒让你获得一项工匠工具熟练，并可将该工具作为施展任何以智力为施法关键属性法术的法器。 | Y | 1 | Y | 奇械学徒 (TCE / feats / 奇械学徒 / p.79, 0.881) | 奇械学徒 (TCE / feats / 奇械学徒 / p.79, 0.881)<br>+2 万能工具 (TCE / items / +2 万能工具 / p.119, 0.736)<br>+3 万能工具 (TCE / items / +3 万能工具 / p.119, 0.736) |
| full-tce-all-purpose-tool-transform | 奇械师那把魔法螺丝刀能不能变成别的工匠工具？ | 可以。以一个动作触摸万能工具，它会转换为你选择的一件工匠工具，并且你对它拥有熟练。 | Y | 1 | Y | +3 万能工具 (TCE / items / +3 万能工具 / p.119, 0.736) | +3 万能工具 (TCE / items / +3 万能工具 / p.119, 0.736)<br>+2 万能工具 (TCE / items / +2 万能工具 / p.119, 0.733)<br>+1 万能工具 (TCE / items / +1 万能工具 / p.119, 0.727) |
| full-tce-all-purpose-tool-cantrip | 万能工具可以临时学一个戏法吗？ | 可以。以一个动作凝神于万能工具，可以选择一个你不知道、来自任意职业的戏法，8 小时内如同奇械师戏法施展。 | Y | 1 | Y | +3 万能工具 (TCE / items / +3 万能工具 / p.119, 0.736) | +3 万能工具 (TCE / items / +3 万能工具 / p.119, 0.736)<br>+2 万能工具 (TCE / items / +2 万能工具 / p.119, 0.733)<br>+1 万能工具 (TCE / items / +1 万能工具 / p.119, 0.731) |
| full-tce-amulet-devout-channel-divinity | 虔信护符能额外用一次引导神力吗？ | 可以。穿戴虔信护符时，你可以使用一次引导神力而不消耗使用次数；使用后到下次黎明前不能再次使用。 | Y | 1 | Y | +1 虔信护符 (TCE / items / +1 虔信护符 / p.119, 0.736) | +1 虔信护符 (TCE / items / +1 虔信护符 / p.119, 0.736)<br>+3 虔信护符 (TCE / items / +3 虔信护符 / p.119, 0.735)<br>+2 虔信护符 (TCE / items / +2 虔信护符 / p.119, 0.733) |
| full-tce-bloodwell-vial-sorcery-points | 术士那个装血的小瓶怎么恢复术法点？ | 当你使用任意数量生命骰恢复生命值时，血源瓶可以让你恢复 5 点术法点；该特性到下个黎明前不能再次使用。 | Y | 4 | Y | 狗头人鳞术士 (VGM / bestiary / 狗头人鳞术士 / p.167, 0.792) | 狗头人鳞术士 (VGM / bestiary / 狗头人鳞术士 / p.167, 0.792)<br>狗头人鳞术士 (VGM / bestiary / 狗头人鳞术士 / p.167, 0.772)<br>狗头人鳞术士 (VGM / bestiary / 狗头人鳞术士 / p.167, 0.768) |
| full-tce-moon-sickle-healing-d4 | 月镰会增强治疗法术吗？ | 会。持握月镰施展恢复生命值的法术时，可以骰一枚 d4 并把结果加入回复的生命值。 | Y | 1 | Y | +1 月镰 (TCE / items / +1 月镰 / p.133, 0.736) | +1 月镰 (TCE / items / +1 月镰 / p.133, 0.736)<br>+3 月镰 (TCE / items / +3 月镰 / p.133, 0.733)<br>+2 月镰 (TCE / items / +2 月镰 / p.133, 0.730) |
| full-tce-bait-and-switch-no-opportunity | 战技里和队友互换位置的那招会吃借机攻击吗？ | 不会。诱饵战术让你与 5 尺内自愿且未无力的生物互换位置，这一移动不会引发借机攻击。 | Y | 1 | Y | 借机攻击 (PHB / actions / 借机攻击 / p.195, 0.800) | 借机攻击 (PHB / actions / 借机攻击 / p.195, 0.800)<br>借机攻击 (PHB / actions / 借机攻击 / p.195, 0.704)<br>借机攻击 (PHB / actions / 借机攻击 / p.195, 0.704) |
| full-tce-ambush-superiority-die | 突袭战技能把卓越骰加到什么检定？ | 突袭可在进行敏捷（隐匿）检定或先攻检定时消耗一枚卓越骰，并把它加入检定。 | Y | 1 | Y | 突袭 (TCE / optionalfeatures / 突袭 / p.42, 0.786) | 突袭 (TCE / optionalfeatures / 突袭 / p.42, 0.786)<br>精准击 (PHB / optionalfeatures / 精准击 / p.74, 0.740)<br>战术预估 (TCE / optionalfeatures / 战术预估 / p.42, 0.720) |
| full-xge-banishing-arrow-save-effect | 奥术射手把人暂时送去妖精荒野的箭，要目标过什么豁免？ | 放逐箭命中后，目标必须成功通过魅力豁免，否则被放逐；被放逐期间移动速度为 0 且陷入无力。 | Y | 1 | Y | 放逐箭 (XGE / optionalfeatures / 放逐箭 / p.29, 0.736) | 放逐箭 (XGE / optionalfeatures / 放逐箭 / p.29, 0.736)<br>暗影箭 (XGE / optionalfeatures / 暗影箭 / p.30, 0.604)<br>迷惑箭 (XGE / optionalfeatures / 迷惑箭 / p.29, 0.599) |
| full-tce-armor-magical-strength-charges | 哪个灌注盔甲有 6 发充能，可以加力量检定或防止被击倒？ | 魔法力量盔甲有 6 发充能，可为力量检定或力量豁免加入智力调整值，也可用反应避免被击倒伏地。 | Y | 1 | Y | 魔法力量盔甲 (TCE / optionalfeatures / 魔法力量盔甲 / p.20, 0.736) | 魔法力量盔甲 (TCE / optionalfeatures / 魔法力量盔甲 / p.20, 0.736)<br>贝希默的失落王冠 (POTA / items / 贝希默的失落王冠 / p.223, 0.572)<br>激活物品 (DMG / actions / 激活物品 / p.141, 0.561) |
| full-tce-arcane-propulsion-armor-gauntlets | 奥能动力甲的手套算什么武器？ | 奥能动力甲的手套在未持握物品时可视为魔法近战武器，造成 1d8 力场伤害，并具有投掷属性。 | Y | 1 | Y | 奥能动力甲 (TCE / optionalfeatures / 奥能动力甲 / p.20, 0.886) | 奥能动力甲 (TCE / optionalfeatures / 奥能动力甲 / p.20, 0.886)<br>避矢夺箭手套 (DMG / items / 避矢夺箭手套 / p.172, 0.508)<br>游泳攀爬手套 (DMG / items / 游泳攀爬手套 / p.172, 0.485) |
| full-tce-custom-lineage-feat | 塔莎的自定义种族在 1 级能直接选一个专长吗？ | 可以。自定血统在 1 级选择一个满足条件的专长，并从小型或中型中选择体型。 | Y | 1 | Y | 自定血统 (TCE / races / 自定血统 / p.8, 0.732) | 自定血统 (TCE / races / 自定血统 / p.8, 0.732)<br>魔法学徒 (PHB / feats / 魔法学徒 / p.168, 0.613)<br>塔莎心灵鞭 (TCE / spells / 塔莎心灵鞭 / p.115, 0.603) |
| full-vrgr-dhampir-no-breath | 范瑞ichten里的吸血鬼味儿族系还需要呼吸吗？ | 不需要。半血裔具有不死本质，不需要呼吸；它还拥有 60 尺黑暗视觉等特性。 | N | - | N | 吸血鬼 (MM / bestiary / 吸血鬼 / p.297, 0.767) | 吸血鬼 (MM / bestiary / 吸血鬼 / p.297, 0.767)<br>吸血鬼 (MM / bestiary / 吸血鬼 / p.297, 0.753)<br>吸血鬼 (MM / bestiary / 吸血鬼 / p.297, 0.750) |
| full-eepc-aarakocra-flight-armor | 那个鸟人种族穿中甲或重甲还能飞吗？ | 不能。EEPC 阿兰寇拉鹰人拥有 50 尺飞行速度，但要使用此速度不能穿着中甲或重甲。 | Y | 1 | Y | 阿兰寇拉鹰人 (EEPC / races / 阿兰寇拉鹰人 / p.5, 0.722) | 阿兰寇拉鹰人 (EEPC / races / 阿兰寇拉鹰人 / p.5, 0.722)<br>重甲大师 (PHB / feats / 重甲大师 / p.167, 0.609)<br>跑跳之靴 (DMG / items / 跑跳之靴 / p.156, 0.594) |
| full-mm-hydra-extra-reactions | 多头怪为什么可以有不止一个借机攻击反应？ | 海德拉的头每超过一颗，就获得一个额外反应；这些额外反应只能用于借机攻击。 | Y | 1 | N | 借机攻击 (PHB / actions / 借机攻击 / p.195, 0.877) | 借机攻击 (PHB / actions / 借机攻击 / p.195, 0.877)<br>借机攻击 (PHB / actions / 借机攻击 / p.195, 0.772)<br>借机攻击 (PHB / actions / 借机攻击 / p.195, 0.772) |
| full-vgm-flail-snail-antimagic-shell | 那个有反魔法壳的蜗牛会不会把单体法术弹回施法者？ | 可能会。当连枷蜗牛成功通过对抗法术的豁免或法术攻击失手时，d6 结果为 1-2 且法术只以它为目标时，法术会被反射给施术者。 | Y | 3 | N | 激活物品 (DMG / actions / 激活物品 / p.141, 0.751) | 激活物品 (DMG / actions / 激活物品 / p.141, 0.751)<br>激活物品 (DMG / actions / 激活物品 / p.141, 0.691)<br>连枷蜗牛 (VGM / bestiary / 连枷蜗牛 / p.144, 0.686) |

## Needs Review

- `full-egw-gift-of-alacrity-initiative`：Top1 不是核心证据。Top1: 激活物品 (DMG / actions / 激活物品 / p.141, 0.741)
- `full-tce-chef-short-rest-healing`：Top1 不是核心证据。Top1: 治疗师 (PHB / feats / 治疗师 / p.167, 0.720)
- `full-tce-crusher-move-target`：Top1 不是核心证据。Top1: 突刺击 (PHB / optionalfeatures / 突刺击 / p.74, 0.653)
- `full-tce-crusher-critical-advantage`：未命中期望证据；Top1 不是核心证据。Top1: 易伤护甲（钝击） (DMG / items / 易伤护甲（钝击） / p.152, 0.595)
- `full-xge-bountiful-luck-reaction`：Top1 不是核心证据。Top1: 半身人 (PHB / races / 半身人 / p.26, 0.767)
- `full-tce-bloodwell-vial-sorcery-points`：首个命中排在第 4。Top1: 狗头人鳞术士 (VGM / bestiary / 狗头人鳞术士 / p.167, 0.792)
- `full-vrgr-dhampir-no-breath`：未命中期望证据；Top1 不是核心证据。Top1: 吸血鬼 (MM / bestiary / 吸血鬼 / p.297, 0.767)
- `full-mm-hydra-extra-reactions`：Top1 不是核心证据。Top1: 借机攻击 (PHB / actions / 借机攻击 / p.195, 0.877)
- `full-vgm-flail-snail-antimagic-shell`：Top1 不是核心证据。Top1: 激活物品 (DMG / actions / 激活物品 / p.141, 0.751)
