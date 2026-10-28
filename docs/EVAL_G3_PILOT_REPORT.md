# G3 pilot 结果报告（2026-10-24，模型 `biklimax/qwen3.8_27b`）

> **这是 prereg 的 pilot，不是 G3 正式结果。** prereg 冻结于 `docs/EVAL_G3_PREREG.md`；
> 本报告如实记录 pilot 的实际 n 与停止原因，**不宣称显著性**。
> 结论先行：**本 pilot 的主终点无法测出 skill 效应——不是因为 skill 无效，而是任务集饱和 + forced 臂预算不足。**

## 1. 设计

| 项 | 值 |
|---|---|
| 模型 | `biklimax/qwen3.8_27b`（用户指定，@28000） |
| 任务 | 8 个 private held-out 任务（G1 set 外部不可得，见 `docs/EVAL_G3_SCENARIOS.md` §1） |
| Arms | `bare` · `core` · `full_forced` · `mini_forced`（构造规格 `docs/EVAL_G3_ARMS.md`） |
| Seeds | 3/臂/任务（= 独立重复；采样种子 CLI 不可控） |
| 计划 | 8 × 4 × 3 = **96 runs** |
| 实际 | **58 runs**（`status: incomplete`），墙钟合计 13,399 s ≈ 3.7 h |
| 停止 | prereg 停止规则「budget exhaustion → publish partial, mark `incomplete`」 |

## 2. 结果

| arm | runs | pass | fail | indeterminate | n_eff | pass_rate | Wilson 95% CI | mean wall |
|---|---|---|---|---|---|---|---|---|
| `bare` | 18 | 17 | 0 | 1 | 17 | **1.000** | [0.816, 1.000] | 279 s |
| `core` | 15 | 13 | 0 | 2 | 13 | **1.000** | [0.772, 1.000] | 365 s |
| `mini_forced` | 12 | 11 | 0 | 1 | 11 | **1.000** | [0.741, 1.000] | 273 s |
| `full_forced` | 13 | 0 | 0 | **13** | **0** | — | — | — |

配对差（对 `bare`，按 task×seed 配对；indeterminate **不进**配对）：

| arm | paired_n | mean diff | wins | losses |
|---|---|---|---|---|
| `core` | 12 | **0.000** | 0 | 0 |
| `mini_forced` | 10 | **0.000** | 0 | 0 |
| `full_forced` | 0 | n/a | 0 | 0 |

MDE（n=8 tasks, seeds=3）：**0.404** 绝对值。

## 3. 发现（两条都改变结论解读）

### F1 天花板效应：任务集对本模型**饱和**

`bare`（无任何 skill）在有效运行上 **17/17 全过**，`core`/`mini_forced` 同样 100%。
即：**纯能力题无法区分 skill 臂**——不是「skill 无用」，是**这把尺子量不出差别**。
与本项目既有结论一致（memory W7：pure-capability 全饱和，判别器是 process-contract
compliance 任务）。`core − bare = 0.000`（12 对，0 胜 0 负）是饱和的直接体现。

### F2 `full_forced` 预算饥饿：13/13 全部 900s 超时

注入 48KB SKILL.md 后模型走完整协议，单题墙钟 > 900s（`agent_exit: -1`、
`wall: 900.2`）。这与 AB_SUITE_V2 的实测一致（`q38_forced ≈ 1820s/题`）。
**n_eff = 0**，该臂无法比较——不是「forced 更差」，是**没测到**。

### F3 运行纪律：操作者写入会被误判为越界

pilot 期间我并发写 `docs/`，宿主 repo 差分腿把这些写入判成隔离违例，把 2 次
隐藏测试已 `PASS` 的运行污染成 indeterminate。已归档 `tests/eval/g3/operatornoise/`
（不删、可审计）。**纪律：运行期间仓库零写入。**

## 4. 诚实结论

- **不能**说「skill 没有提升」——有效样本全部饱和，主终点（pass rate 差）不可测。
- **不能**说 `full_forced` 更差——它没有有效样本。
- 能说的：在 `biklimax/qwen3.8_27b` 上，这 8 个纯能力任务对无 skill 的裸模型已 100% 通过
  （CI 下界 0.74–0.82）；要测 skill 效应，必须换**判别性任务**。

## 5. 下一步（按性价比排序）

1. **换判别器**：补 2–4 个 **process-contract compliance 任务**（要求产出 vibeweaver
   证据构件：acceptance/verification_log/tests evidence；hidden test 校验证据而非纯功能）——
   memory 记录这是唯一能拉开 bare/full 差距的任务族。
2. **给 forced 臂更大预算**：per-run timeout 1800–2400s，或把注入面从 48KB 全量缩到
   core 契约（约 1.2k tokens）再测 forced 效应。
3. **补完 bare/core/mini 臂**（各自 24 runs）可让 CI 收窄，但**不会改变饱和结论**。
4. 复现：`python3 scripts/eval_pilot.py --phase report`（重算）；续跑：
   `--phase pilot`（缓存运行跳过）。

## 6. 可复现性

```bash
python3 scripts/eval_pilot.py --phase report          # 重算 summary.json
ls tests/eval/g3/runs/                                 # 58 个运行目录（含 verdict/trajectory/cost/isolation/run_meta）
cat tests/eval/g3/summary.json                         # 本报告数字的来源
```

原始运行产物保留 `tests/eval/g3/runs/`；被操作者噪音污染的 2 次在 `tests/eval/g3/operatornoise/`。

## 7. 判别性复测（compliance 任务族，2026-10-24 同日追加）

> 针对 F1（天花板效应）的换尺复测：**3 个 compliance 任务**（`g3_comp_dedupe` /
> `g3_comp_paginate` / `g3_comp_scope`：功能正确之外还要求过程契约证据构件，
> hidden 断言只取根/core SKILL 明文规定的最小形状）× 4 arms × 3 seeds = **36/36 complete**。
> 口径见 `tests/eval/g3/comp_summary.json`（`task_filter: "g3_comp_"`），
> selfcheck 11/11 valid（含 naive=功能正确无证据构件 被杀、纸面证据不得背书功能缺陷的 EXTRA 案例）。

| arm | runs | pass | fail | indet | n_eff | pass_rate | Wilson 95% CI | paired vs bare |
|---|---|---|---|---|---|---|---|---|
| `bare` | 9 | 0 | 9 | 0 | 9 | **0.000** | [0.000, 0.299] | 基线 |
| `core` | 9 | 2 | 7 | 0 | 9 | **0.222** | [0.063, 0.547] | **+0.222（2 胜 0 负）** |
| `mini_forced` | 9 | 0 | 9 | 0 | 9 | **0.000** | [0.000, 0.299] | 0.0（0 胜 0 负） |
| `full_forced` | 9 | 0 | 0 | **9** | **0** | — | — | 无样本 |

（MDE 0.660 @ n=3×seeds=3；CI 相互重叠 → **directional，不宣称显著性**。）

### D1 判别力成立：skill 的差异在过程契约，不在纯能力

bare（无 skill）0/9——每次的失败点都精确落在证据构件断言（`tests/acceptance.md
missing` 一类），功能代码多数已写好。core 2/9 且 **2 胜 0 负**（配对增益全部来自
core，core 无任何丢失）。这与 F1 的天花板结论互补：**尺子换对了，差异出来了**。

### D2 mini 臂 0/9 是如实的设计差，不是缺陷

`vibeweaver-mini` 契约本就不含 acceptance/verification_log 仪式（小改小测纪律）；
在本任务族上无效应属预期。报告的意义：若目标人群是 mini 用户，compliance 类
任务**不是**该付代价换来的收益。

### D3 core 的 7 次失败分布（审查过，非系统陷阱）

失败点分布在**不同**证据子断言（acceptance 缺失 4 次 / iter 行缺失 3 次 / 顶行非逐字 1 次，
合计 7 次含跨任务），且 2 次全过——自发触发下的**部分合规**状态，hidden 测试没有单一
必杀面。

### D4 `full_forced` 再次 n_eff=0：1800s 仍不足

注入全量契约后单题墙钟 ≥1800s（`agent_exit: -1`、wall≈1800.2、无隔离违例、超时后
进程组零孤儿——`tests/test_process_group_kill.py` 硬化生效）。形式化 G3 要测 forced
臂需 2400–3600s/题预算（或把注入面缩到 core 契约——但那已近似 core 臂）。

### D5 战役启动事故（如实记录）

首次 comp 战役启动命令漏传 `--tasks/--seeds`：`tasks_all()` 此时已含 3 个新 comp 任务，
计划膨胀为 **132**（11×4×3），且在全新 out-root 上**重跑已测饱和的 8 个旧能力任务**，
耗 8h 墙钟 + 模型配额（用户质询后停止于 58/132）。意图范围（36 runs）因字母序在战役
前段已全部产出，**判别数据零损失**；事故注记在 `tests/eval/g3/comp_manifest.json`
（`planned_note`/`stopped_reason`）+ ADR `D-W2ISO-8`。教训：live 战役启动前必须人工复核
打印的 plan 行（`N runs planned (X tasks × Y arms × Z seeds)`）。

### D6 结论更新（取代 §4 的「不能说什么」）

1. 在 `biklimax/qwen3.8_27b` 上：compliance 任务族 **bare 0/9 vs core 2/9（directional
   显著）**——skill 的价值在过程契约合规上首次被测出；纯能力任务上无差异（F1 饱和）。
2. `full_forced` 在下调注入面或上调预算前**不可测**——禁止写「forced 更差/更好」。
3. 形式 G3（prereg n=16）输出仍取决于 forced 臂预算决策；本复测数据作为 pilot 证据
   归档，不并入 prereg 的 16 任务计数。

## 8. V2 产品形态战役（md + 插件，2026-10-25）

> 用户裁定：§7 的文本层结论对「部署形态是否可靠」这个问题零输出（插件从未入场）。
> v2 按 `docs/EVAL_V2_PREREG.md` 执行：臂 `full_deployed` = skill payload +
> gate/audit 两插件进高温 HOME（无 prompt 注入，真实安装形态）+ 场景 `setup_files`
> 预放激活标记（class/profile/baseline 行；acceptance 刻意留给 agent）。
> 数据：`tests/eval/g3/v2_summary.json`（label=v2，含 `gate_ledger` 插件体检表）。

### 结果

| arm | runs | pass | fail | indet | n_eff | pass_rate | Wilson 95% CI | mean wall |
|---|---|---|---|---|---|---|---|---|
| `bare`（复用 §7） | 9 | 0 | 9 | 0 | 9 | 0.000 | [0.000, 0.299] | 175s |
| `full_forced`（复用，180min 口径） | 9 | 3 | 6 | 0 | 9 | 0.333 | [0.12, 0.65] | ~2460s |
| `full_deployed`（本战役） | 9 | 4 | 4 | 1 | 8 | **0.500** | [0.215, 0.785] | **1401s** |

（MDE 0.66 @ n=3×seeds=3；CI 与对照重叠 → **directional，不宣称显著性**。）

### F5 gate 体检表：插件确实在干活

33 次 GATE-BLOCKED 拦截（completion×15、汇总形 other×14、destructive×2、
evidence-lock×2），**9/9 run 全部被拦过至少一次**；被拦后多数 run 补齐工件走到
pass。烟测与战役共同证明加载链（高温 HOME `plugins/`）、激活链（setup_files
标记）、强制链（拦截→改正→hidden PASS）三段全通。

### F6 失败构成变了：只剩「证据尾行」一种形状

4 个 fail 全部是功能断言先行通过后栽在证据格式（3× log 尾行 `- iter N PASS:
criterion #…`、1× acceptance 首行非逐字）。对比 §7：forced 臂的 scope 越界失败
（`.git/`、`memory/` 与白名单冲突）在 v2 口径下消失（基建面按产品合法产物豁免），
文本层的 acceptance 大面积缺失也被 gate 拦回。**插件把失败面压缩到了「最后一行
日志的格式」这一个点**——这是下一步（gate 提示词或契约文本）最便宜的靶子。

### F7 部署形态 × 无头 harness 的真实摩擦：trust-tier 等确认

dedupe/s1 两次 `agent_exit=1`（会话流无错误、stdout 尾部显示 subject 按 trust-tier
规则停在「等用户确认」）。无头评测没有确认者 → CLI exit 1 → harness fail-closed
判 indeterminate（永不计 pass）。这是产品语义与自动化集成的真缺口（记入
UNFINISHED：headless/auto 模式需要确认语义降级路径），不是被测模型的错，也不是
测量 bug。重跑一次因操作者在 run 窗口内建备份目录而污染（纪律教训第三次应验：
**运行窗口零写入，包括归档动作本身**）。

### 结论更新（取代 §7 D6 第 2 条）

1. 产品形态（md+插件）在 compliance 任务族上 **50%（directional）** vs 纯文本
   forced 33% vs 裸 0%，且墙钟只有 forced 的 57%——插件路线首次拿到方向性证据；
2. n=8 有效样本远小于显著性要求，禁止对外写「显著优于」；
3. 对外可说的最强表述：「gate 插件在 9/9 运行中实际拦截并驱动改正，部署形态 pass
   率 50%（Wilson 95% CI [0.22, 0.78]，directional）」。

### §8 勘误（2026-10-26，ADR D-W2ISO-9）

§8 的 4 个 EVIDENCE-FAIL 经 trajectory 实物复核**全部为评分器形态税，非 agent 不合规**：
3 个是 agent 写复数 `criteria`（hidden 正则只认单数 `criterion`），1 个是 acceptance
首行写 ASCII `stall=3x`（要求逐字 `3×`）；且「must end with」报错文案与代码的实际
行为（存在性检查）不符。gate checker 本就不查 criterion 字样，agent 全程无被纠正
信号——hidden 比契约/gate 更严，违反公平性原则（criterion #61）。

**修正口径**：按语义合规重数，v2 战役功能断言 8/8、iter 证据 8/8、acceptance 8/8，
4 个 fail 均为尺子刻度问题。评分器已修（`criteri(?:a|on)` + ×/x 等价 + 文案对齐 +
selfcheck 双向夹具），修复后重跑见 §9（label=v2fix）。§8 原表保留不改（历史证据），
其「50%」应读作「严格形态税下的下界」。

## 9. v2fix 修复后重跑（2026-10-26）

> 评分器修复后同任务、同臂（full_deployed）、同 seeds 重跑 9 runs（label=v2fix）。
> 数据：`tests/eval/g3/v2fix_summary.json`（含 `scorer_revision`，与 §8 旧口径并列）。

| arm | runs | pass | fail | indet | n_eff | pass_rate | Wilson 95% CI | mean wall |
|---|---|---|---|---|---|---|---|---|
| `bare`（复用） | 9 | 0 | 9 | 0 | 9 | 0.000 | [0.000, 0.299] | 175s |
| `full_forced`（复用） | 9 | 3 | 6 | 0 | 9 | 0.333 | [0.12, 0.65] | ~2460s |
| `full_deployed`（§8 严格形态税口径） | 9 | 4 | 4 | 1 | 8 | 0.500 | [0.215, 0.785] | 1401s |
| **`full_deployed`（v2fix 修复后）** | **9** | **9** | 0 | 0 | 9 | **1.000** | **[0.701, 1.000]** | **1403s** |

（n=3×seeds=3，CI 下界 0.70 已高于 bare 上界 0.30 → **与 bare 不重叠，仍按
directional 表述**（预注册口径 MDE 0.66 未声明显著性检验）。）

### 结论

1. **产品形态满配合规**：9/9，且每 run 仍被 gate 拦截 1–5 次（共 28 次，9/9 run）
   ——拦截→改正→hidden PASS 的链条稳定复现；
2. v2 的 4 个 fail 确认为评分器形态税（§8 勘误、ADR D-W2ISO-9）；语义口径复数
   亦为 8/8，与 v2fix 一致；
3. 墙钟 23min/run，比纯文本注入（41min）省 43%：插件反馈回路让 agent 少走弯路；
4. F7（trust-tier 停等确认）本轮 9/9 未复现——产品缺口仍成立（1/9 历史发生），
   待修后再评估；
5. **对外最强可说表述**：「在 compliance 任务族上，部署形态（skill 文本+gate/audit
   插件）9/9 满配合规（Wilson 95% CI [0.70, 1.0]，directional），纯文本 0–3/9；
   gate 插件 9/9 运行均有真实拦截并驱动改正」。

## 10. bare 必败题池筛选（n 扩样前置，2026-10-26）

> 判据 #74 的执行记录。用户指令：「找到 bare 状态无法正确完成的题目」。三轮筛查
> 24 bare runs，逐轮淘汰有记录，夹具三向门先行（selfcheck 18/18）。

| 轮 | 候选 | bare 战绩 | 判定 |
|---|---|---|---|
| 1 | specvstest（spec-vs-test 冲突）/ multisymptom（怪癖保持）/ stateleak（别名变异） | 9/9 全过 | 淘汰：功能面饱和 |
| 2 | testquality（测试判别力门） | 3/3 过 | 淘汰：prompt 泄露判别标准（出题教训） |
| 2–3 | redfirst / redfirst_ttl / redfirst_bill（RED-first 证据链 + 真 bug） | **0/9 全灭** | ✅ 存活 |

**存活题池（6 题）**：comp 3（双侧已证：bare 0/9、full_deployed 9/9）+ redfirst 族 3
（bare 0/9 侧已证；full_deployed 正向验证进行中）。

**判据偏差如实申报**：#74 写了「失败为功能面」，但存活任务的 bare 失败全在证据链面
（功能修复全对，RED 行缺 `| diagnosis:`/`criterion #` 字面子句——prompt 明写仍不合规）。
该子句系出题时的过度指定，与 F1（功能对本模型饱和）自相矛盾。按用户原始指令
（bare 无法正确完成）保留题池，处置权交用户（ADR D-W2ISO-10：追认 / 清零重狩猎）。

### F8 判别面的性质（与 D1 互证）

bare 在被拦下的每一题里都「做了 RED、修了 bug」，死在契约形状；这正是产品主张的
实验化：**文本明示换不来形状合规，gate 的机械强制可以**。若 full_deployed 正向
通过（gate 推动 iter/diagnosis 合规），md+插件 vs 无 的效应就在同一尺子上可测。

### §10 终局（2026-10-28，ADR D-W2ISO-10 裁决：清零重狩猎）

用户裁定**清零重狩猎**。#74 原文判据是「hidden 只测功能」「失败为功能面」，而本节
存活池（comp 3 + redfirst 3）的 bare 失败全部在证据链面（D3/F8 实录：功能修复全对，
死在 RED 行/acceptance 形状），不满足字面判据 → **旧池 6 题全部退役**（历史数据与
日志保留，仅退役题池资格）。三条注记随判词入档：

1. `teethfull2_summary.json` 的 7/9 含 ttl/s2 离线复判（复判后有效 8/9，池侧 17/18）；
   机器 JSON 原值与复判口径的差异在案可查。
2. 旧池的效应量为**选择后检验**：bare 必败经 3 轮 24 个 bare runs 筛出，bare 侧 0
   由构造保证——该 p 值证明「deployed 能通过 bare 必败池」，不是无条件显著性依据。
3. comp 半区（0/9 vs 9/9）不受选择影响，是产品形态效应的独立证据（§8/§9）。

重狩猎按 #74 原文执行：spec↔test 冲突 / 作用域+保持陷阱两族 × 5 候选，
hidden 纯功能断言（零证据形状检查），prompt 中立。筛查与存活结果见 §11。

## 11. 清零重狩猎三方向筛查（2026-10-28，判据 #74 执行记录）

> ADR D-W2ISO-10 裁决（清零重狩猎）的执行波。判据原文：≥2 个「纪律有牙齿」新任务
> （spec↔test 冲突 / 作用域+保持陷阱），hidden **只测功能**，selfcheck 三向门 valid，
> bare 筛查（每任务 3 seeds）中 bare 至少 2/3 fail 且**失败为功能面**，不达标淘汰并
> 记原因。共 10 候选 × 3 批（3 个不同方向）= 35 个 bare runs。

### 筛查结果（bare，biklimax/qwen3.8_27b）

| 候选 | 批/方向 | s0 | s1 | s2 | 判定 |
|---|---|---|---|---|---|
| weekdate（ISO 周历 vs 毒测试） | 1 毒测试冲突 | pass | pass | fail※ | 淘汰 |
| moneyfmt（half-even vs half-up） | 1 毒测试冲突 | fail※ | pass | pass | 淘汰 |
| globmatch（`*` 不跨 `/` vs 通吃） | 1 毒测试冲突 | indet※ | pass | pass | 淘汰 |
| wraptext（超长词 quirk + 装满 bug） | 1 保持陷阱 | pass | pass | pass | 淘汰 |
| cachetouch（no-touch quirk + evict bug） | 1 保持陷阱 | pass | pass | pass | 淘汰 |
| closeacct（失败原子性 + 潜伏缺陷） | 2 硬陷阱 | pass | pass | pass | 淘汰 |
| pageoff（空页 legacy + 边界） | 2 硬陷阱 | pass | pass | pass | 淘汰 |
| bucketrate（边界含等 + 封顶 + 零消耗） | 2 硬陷阱 | pass | pass | pass | 淘汰 |
| conccounter（并发下扣减原子性） | 3 并发不变量 | pass | pass | pass | 淘汰 |
| inirules（自定义方言状态机） | 3 方言状态机 | pass | pass | pass | 淘汰 |

（s3 附加重复：cachetouch=fail※、weekdate/moneyfmt/globmatch/wraptext=pass。）

### ※ 异常 run 复判（三向门之外的逐 run 裁决，判据「失败为功能面」要求）

verdict 面值不可直接用：harness 在 agent 进程非零退出时**跳过 hidden 直接判 fail**
（`hidden_test: {exit: null, "agent failed/could not run"}`）。四个异常 run 按
「轨迹提取交付物重建 + hidden 重跑」标准逐一定性——三个可定性，一个不可恢复：

| run | run 面值 | 根因 | 交付物功能面 |
|---|---|---|---|
| moneyfmt-s0 | fail | 端点基建：`getaddrinfo ENOTFOUND biklimax.cn`（DNS 挂），零工具调用 | 无交付物（确无） |
| weekdate-s2 | fail | 会话空转：5 次 read 后 3778s 无产出，exit 1 | 无交付物（确无） |
| globmatch-s0 | indeterminate | 1800s 超时（agent_exit=-1，预算无效按 wave11 口径剔除） | **未判定**：`globmatch.py` 已落盘（isolation.json 实录）但内容未保留、沙箱已清理，不可重建复判 |
| cachetouch-s3 | fail | `opencode` 进程 exit 1（F7 同类头摩擦）但会话完整收尾 | **重建 hidden exit=0（功能正确）** |

（M2 口径注：scenario 超时统一 1800s，但 kill 执行不对称——仅 globmatch-s0 被 kill，
moneyfmt-s0/weekdate-s2 超预算未 kill；四个异常按**根因**而非时长分类，剔除口径
统一为「预算/基建无效，不计行为率」。）

**结论：31 个原位 hidden 全过 + 1 个重建全过（cachetouch-s3）；三个可定性异常 run
均非功能面失败，globmatch-s0 功能面未判定（不可恢复）。零**已判定**功能失败 →
零存活题（即便把 globmatch-s0 计为功能失败，globmatch 亦仅 1/4 挂，远低于 ≥2/3
存活线——零存活结论稳健）。

### F9 功能面饱和的延伸（本节主发现）

在 qwen3.8-27b 上，单模块 + 显式契约类任务的功能面饱和**不限于普通能力题**（F1 的
17/17），而是延伸到：毒测试在场的 spec↔test 冲突面、隐藏硬约束（边界含等/容量封顶/
失败原子性/legacy 规则）、**并发不变量（check-then-act 原子性）**、自定义方言状态机。
裸模型连毒测试都会主动识破并改写（cachetouch-s3 轨迹原文：「the left-behind tests
asserted LRU semantics … contradict the authoritative docs/spec.md … they were stale」）。
**「bare 必败」判据在功能面对本模型不可达**——#74 的池数量目标（≥2 题）未达。

### 判据处置与 stall 记录（COV-7）

同判据（bare ≥2/3 功能失败）三方向连续未达：毒测试冲突（批1）→ 硬陷阱（批2）→
并发不变量+方言（批3）。停止该方向。处置权交用户（PAUSED 选项见收口答复）：
① 换弱模型狩猎（qwen3.6-27b 侧 bare-must-fail 可达，池可用于扩样）② repo 级/
长时程任务类（F5/F8/F10，需先过设施 spike）③ 接受零池终局（功能面饱和即结论）。

### 测量发现（UNFINISHED 候选）

harness 的 agent-exit≠0 → 跳过 hidden 判 fail 语义把**进程失败混同行为失败**
（本轮 3 例，占 35 run 的 8.6%）。建议：exit≠0 时仍跑 hidden 并双记
（behavioral verdict + process verdict），或至少把「无交付物/基建失败」从 fail 中
分离为 indeterminate。

### 复现

```bash
python3 tests/eval/lab/selfcheck.py                        # 28/28 三向门
python3 scripts/eval_pilot.py --phase report \
  --out-root tests/eval/g3/huntbare --label huntbare       # 重算 summary
ls tests/eval/g3/huntbare/*/verdict.json                   # 35 个 run 原始产物
```
