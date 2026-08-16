# vibeweaver Skill A/B 评测报告

- **模型**: qwen3.6_27b @ OpenAI 兼容端点 (vllm, 262k ctx, thinking 开启)
- **Agent**: opencode 1.18.10 headless (`opencode run --auto --model <endpoint>/qwen3.6-27b`)
- **日期**: 2026-08-01
- **环境**: macOS, Python 3.9, 无 Docker（全部评测在无容器环境完成）

## 三臂设计

| 臂 | 说明 |
|---|---|
| baseline | 隔离配置（XDG_CONFIG_HOME 独立），**无任何 skill** |
| with_skill | 同隔离配置 + vibeweaver skill 可用（描述注入 available_skills，模型自主决定是否加载） |
| with_skill_forced | vibeweaver SKILL.md 全文注入 system prompt，强制遵循 |

## 评测集

1. **Aider polyglot（Python 子集 10 题）**: phone-number, grade-school, list-ops, variable-length-quantity, simple-linked-list, transpose, pig-latin, robot-name, two-bucket, bowling。隐藏测试，pytest 评分（与 aider 官方 harness 同法）。
2. **SWE-bench Lite 6 实例**: pallets/flask-4045, pallets/flask-4992, psf/requests-3362, pytest-dev/pytest-6116, pytest-dev/pytest-9359, sympy/sympy-21627。真实仓库 issue 修复，FAIL_TO_PASS + P2P 回归守卫（gold 验证 6/6 环境正确：base 必挂、gold 必过）。

## 结果

### 通过率（benchmark 隐藏测试）

| 评测集 | baseline | with_skill（未触发） | with_skill_forced（强制） |
|---|---|---|---|
| polyglot 10 题 | 4/10 (40%) | 3/10 (30%) | 5/10 (50%) |
| SWE-bench Lite 6 题 | 3/6 (50%) | 3/6 (50%) | 4/6 (67%) |
| **合计 16 题** | **7/16 (44%)** | **6/16 (38%)** | **9/16 (56%)** |

### 耗时

| 臂 | 平均 | 中位数 |
|---|---|---|
| baseline | 69s | 50s |
| with_skill | 86s | 34s |
| with_skill_forced | 153s | 142s |

## 关键发现

1. **触发层失败（最重要）**: 32 个运行中 skill 工具调用 **0 次**。验证了 skill 工具可用、vibeweaver 在 available_skills 列表中（探测确认），但 qwen3.6-27B 从不为这些任务自主加载它。**被动加载模式下 vibeweaver 的收益 = 0**（with_skill ≈ baseline，差异在噪声内）。

2. **强制加载有小幅收益**: 强制遵循后 9/16 (56%) vs baseline 7/16 (44%)，+12.5pp。主要赢在 SWE-bench（+1 题：pytest-9359 双臂 baseline 均失败、强制轮通过）和 polyglot（+1 题）。16 题样本下统计上不显著，但方向为正。

3. **成本翻倍**: 强制轮平均耗时 153s vs baseline 69s（+122%）。skill 的验证循环、研究步骤、产物要求全部转化为 token 和时间开销。

4. **遵循度低**: 即使强制注入全文，模型的遵循是"选择性"的——大量走豁免路径（"COV-3 skipped / minor change / backend-only"），产物极少（无 acceptance.md、verification_log.md、script/、memory/，16 个强制轮几乎全部无产物）。71KB 的复杂 skill 对 27B 模型负荷过大，模型倾向于只取其中"显性规则感"最强的部分（搜索验证、测试先行意识）。

## 对 vibeweaver 的启示

- **描述触发对 27B 失效**: 需要更强的触发机制（例如把核心规则下沉到 AGENTS.md 级别的常驻指令，而不是 71KB 按需加载的 skill 文件），或者依赖用户手动要求。
- **体积 vs 遵循度**: 27B 模型对超长指令的遵循是降级的；核心不可协商规则（NO TEST NO DONE、验证循环）若想在小模型上生效，需要压缩、分层（规则越短越可能被执行）。
- **收益集中在真实仓库任务**: SWE-bench 类任务上强制 skill 的增益更明显（67% vs 50%），小型函数任务上收益不明显——skill 的设计目标（工程纪律）只在任务复杂度足够时才兑现。

## 复现

```bash
# 任务准备
python3 harness/prepare_polyglot.py
python3 harness/prepare_swebench.py
python3 harness/validate_gold.py   # 6/6 gold 验证
# 运行（两臂）
python3 harness/run_eval.py --arm both --concurrency 3
python3 harness/run_eval.py --arm with_skill --force-skill --concurrency 3
# 评分与聚合
# 见 harness/grade_*.py, harness/aggregate.py
```

所有原始数据: `workspace/iteration-1/{tasks,runs,graded}/`

---

# 第二轮：描述优化 + 压缩版 skill（2026-08-01）

## 实验设计

| 臂 | 说明 |
|---|---|
| with_skill_v2 | 完整 71KB skill，仅改 frontmatter 描述（更强制："ALWAYS LOAD BEFORE WRITING ANY CODE" + 具体触发词），不强制 |
| with_skill_mini | **vibeweaver-mini**：2.2KB 压缩版（同款激进描述 + 核心规则 7 条：研究先行/测试先行/NO TEST NO DONE/脚本化/修复循环/产物+报告），不强制 |
| with_skill_mini_forced | 同上，SKILL.md 全文注入 prompt 强制遵循 |

## 触发率（skill 是否被模型主动加载）

| 臂 | 触发/16 | 触发率 |
|---|---|---|
| with_skill（71KB，v1 描述） | 0/16 | **0%** |
| with_skill_v2（71KB，新描述） | 2/16 | 12.5% |
| with_skill_mini（2.2KB） | 10/16 | **62.5%** |

## 通过率（16 题 = 10 polyglot + 6 SWE-bench Lite）

| 臂 | polyglot | SWE-bench | 合计 |
|---|---|---|---|
| baseline | 4/10 (40%) | 3/6 (50%) | 7/16 (44%) |
| with_skill（未触发） | 3/10 (30%) | 3/6 (50%) | 6/16 (38%) |
| with_skill_forced（完整版强制） | 5/10 (50%) | 4/6 (67%) | 9/16 (56%) |
| with_skill_v2（描述优化） | 5/10 (50%) | 4/6 (67%) | 9/16 (56%) |
| **with_skill_mini（未触发）** | 5/10 (50%) | **5/6 (83%)** | **10/16 (62.5%)** |
| with_skill_mini_forced | 5/10 (50%) | 3/6 (50%) | 8/16 (50%) |

## 耗时

| 臂 | 平均 |
|---|---|
| baseline | 69s |
| with_skill_mini | 113s (+63%) |
| with_skill_v2 | 134s |
| with_skill_forced | 153s |
| with_skill_mini_forced | 156s |

## 关键发现

1. **体积是 27B 触发率的决定性变量**：71KB → 0%，描述改激进也只到 12.5%；压到 2.2KB → 62.5%。小模型对"看一眼就觉得不划算"的大 skill 直接忽略。
2. **mini 未触发臂是所有 6 臂中最好成绩**（62.5% vs baseline 44%，+18.75pp），且同时**击败完整版强制臂**（56%）。轻量 skill 自主触发 > 重型 skill 强灌。
3. **mini 是唯一解出 pytest-6116 的臂**（其余 5 臂全失败）——skill 引导的测试先行/验证循环在真实仓库任务上真实生效。
4. **强制反而有害**：mini_forced (50%) < mini 自主 (62.5%)。对每个任务强推工作流，在模型本可快速完成的小任务上制造纯开销（如 phone_number 7/21 vs 16/21）。
5. **收益集中在 SWE-bench**：mini 在真实仓库任务 83% vs 50%（+33pp）；polyglot 小函数任务上各臂都 ~50%，收益有限。

## 对 vibeweaver 的最终结论

- 给 27B 这类小模型用：**必须压缩**。2KB 核心规则（研究→测试先行→NO TEST NO DONE→验证循环→报告）即可带来可测的工程纪律收益，且触发率高。
- 71KB 完整版只适合强模型（大上下文/高遵循度）或用户主动要求。
- 描述写法（"ALWAYS LOAD...任务不完成"）对触发有边际作用，但体积才是主变量。

---

# 第三轮：deepseek-v4-flash（大模型对照，2026-08-01）

## 配置

- 模型: deepseek-v4-flash @ api.deepseek.com（OpenAI 兼容，reasoning 模型）
- 4 臂 × 16 题 = 64 次运行：ds_baseline / ds_mini（2.2KB 自主触发）/ ds_full（71KB 自主触发）/ ds_full_forced（71KB 全文强制）

## 结果

| 臂 | 触发率 | polyglot 10 | SWE-bench 6 | 合计 |
|---|---|---|---|---|
| ds_baseline | — | 5/10 | 6/6 | 11/16 (68.8%) |
| ds_full（71KB 自主） | **0/16** | 5/10 | 6/6 | 11/16 (68.8%) |
| ds_mini（2.2KB 自主） | **12/16 (75%)** | 5/10 | 6/6 | 11/16 (68.8%) |
| ds_full_forced | (强制) | **8/10** | 6/6 | **14/16 (87.5%)** |

## 关键发现

1. **SWE-bench 饱和**：deepseek-v4-flash 裸模型就 6/6 全解（含 27B 从未解出的 flask-4045、pytest-6116），skill 在此测不出区分度（天花板效应）。
2. **触发率规律跨模型复现**：71KB 完整版在 deepseek 上同样 **0/16** 不触发；2.2KB mini 触发 75%。"模型越强越会加载大 skill"的假设不成立。
3. **效果反转**：在能真正执行完整工作流时（13/16 次创建 acceptance.md），完整版强制 = **87.5%，全场最高**——大模型吃下了完整版的额外机制（验收清单、测试先行、验证循环）并转化为收益（bowling 19/31→31/31、simple_linked_list 17/20→20/20）。
4. **mini 在大模型上"平"**：其核心规则（先测试、验证再收工）对 deepseek 是原生行为，无增益（68.8% = baseline）。

## 结论：压缩版 vs 完整版（按模型）

| | 27B (qwen3.6) | 大模型 (deepseek-v4-flash) |
|---|---|---|
| 完整版自主触发 | 0% | 0% |
| mini 自主触发 | 62.5% | 75% |
| 完整版强制效果 | 56% | **87.5%** |
| mini 自主效果 | **62.5%** | 68.8% (=baseline) |
| 最优形态 | **mini 自主** | **完整版强制**（插件注入或用户要求） |

**直接回答**：压缩版在大模型上"自主使用时"效果并不比完整版好（模型已具备核心纪律，mini 无增益）；完整版只有被强制加载时在大模型上显著更好（87.5% vs 68.8%）。但由于大模型同样不会自主加载 71KB 完整版，实践中对大模型的最优解是：**mini 常驻触发 + 完整版渐进披露（细节按需展开）**，或**插件级强制注入完整版**；对 27B 小模型的最优解则是**纯 mini**。

---

# 第四轮：修改版 mini（+Playwright/vision 条款）复测（2026-08-01）

## 目的
验证加 Playwright/mm-sensor 验证条款后的 mini（2.4KB）是否影响两个模型的表现；并补 v1 重复运行做方差对照。

## 结果（16 题 = 10 polyglot + 6 SWE-bench）

| 臂 | 运行 1 | 运行 2（干净环境重跑） | 均值 |
|---|---|---|---|
| qwen + mini v1（旧版） | 10/16 | **9/16**（方差对照） | ~9.5/16 |
| qwen + mini v2（新版） | 8/16 | 8/16 | 8/16 |
| ds + mini v1 | 11/16 | — | 11/16 |
| ds + mini v2 | 11/16（受污染环境） | **13/16**（干净环境） | ~12/16 |

## 结论

1. **无统计显著的回归**：qwen 上 v2（8/16 两次）比 v1 低约 1.5 题，但 v1 重跑也只有 9/16——v1 的 10/16 含运气成分，两版本差异在任务级方差（±2-3 题）内。
2. **ds 上 v2 数值反而更好**（13/16 vs 11/16），同样在噪声内但方向为正。
3. **条款在本评测集中无生效机会**：16 题全为后端任务，32 个 v2 运行 0 次提及 Playwright——该条款只在 UI/浏览器任务上才会激活，其价值未被本评测集覆盖（需要 UI 型任务集才能验证）。
4. **方法论教训**：评估 agent 运行会污染全局 Python 环境（pip install -e 到 user site 并劫持系统 flask/pytest），导致同批后续运行与评分失真——已通过清理 + 评分器 `PYTEST_DISABLE_PLUGIN_AUTOLOAD` 隔离修复。

---

# 第五轮：A4.7b 工作流测试条款 + flow 基准（2026-08-01）

## 变更
- **完整版 vibeweaver** 新增 A4.7b "Workflow Scenario Tests"：多接口业务流测试（入口调用→逐步状态断言→最终验证）、三条硬规则（干净起点/断言状态转移/轨迹落盘 `tests/workflows/*.trace.log`）、cap=5/stall=3× 收敛、收敛行扩展为 `| X/Y test cases | Z/W workflow cases`。
- **vibeweaver-mini** 第 3 节新增一行：多接口后端任务须写 1 条跨接口 workflow 测试（含状态断言、干净起点）。

## 新基准：flow（2 个多接口业务流任务）
1. **flow_todo_auth**（8971）：register→login→todo CRUD，含 409/401/403/404 与跨用户隔离断言
2. **flow_orders**（8972）：register→topup→下单扣余额（原子性）→持久化→余额不足 400
- 隐藏测试 = 完整业务流 pytest（httpx），评分器启动服务（uvicorn）→ 跑流 → 杀进程
- gold 验证：两题 gold 实现均通过

## 结果（10 运行，全部通过 = 天花板）

| 臂 | flow_todo_auth | flow_orders |
|---|---|---|
| qwen baseline | ✅ | ✅ |
| qwen mini_v2 | ✅ | ✅ |
| qwen 完整版强制（含 A4.7b） | ✅ | ✅ |
| ds baseline | ✅ | ✅ |
| ds mini_v2 | ✅ | ✅ |

## 结论
1. **任务太易，无区分度**：规格明确的绿地小服务对两个模型都是基本功（连 27B 裸模型都全解），新条款没有机会显示增益。
2. **但遵循证据确凿**：完整版强制臂按 A4.7b 完整执行——`tests/workflows/test_full_flow.py` + `*.trace.log`、API.md、设计文档、memory/、script/ 全套；mini 臂也产出 script/ + acceptance.md + verification_log.md + 自写流测试。
3. **要测出条款价值需"陷阱任务"**：提供"单接口看似正确、跨接口流程有 bug"的骨架（如 token 不持久、余额扣减非原子），隐藏 workflow 测试会抓住 baseline 臂（凭感觉信任代码）而 skill 臂（强制流测试）能发现——这才是区分设计。

---

# 第六轮：qwen3.8_27b 模型升级复测（2026-08-15）

## 配置

- 模型: **qwen3.8_27b** @ OpenAI 兼容端点（同端 vllm，262k ctx，thinking 开启，temperature 0.6 与原 qwen3.6 完全一致）
- Agent: opencode 1.18.18 headless（原轮 1.18.10，小版本漂移）
- 3 臂 × 16 题（10 polyglot + 6 SWE-bench Lite），提示词/任务集/评分脚本与 qwen3.6 时代完全一致，仅模型与配置目录更换
- 新增隔离配置：configs/q38_baseline / q38_mini / q38_v2（复制原配置，仅改模型 ID）

## 结果（16 题）

| 臂 | polyglot 10 | SWE-bench 6 | 合计 | qwen3.6 对应臂 |
|---|---|---|---|---|
| **q38_baseline** | 7/10 | **6/6** | **13/16 (81%)** | baseline 7/16 (44%) |
| q38_mini_v2 | 6/10 | **6/6** | **12/16 (75%)** | mini_v2 8/16 (50%) |
| **q38_v2（71KB 完整版自主）** | 9/10 | **6/6** | **15/16 (94%)** | with_skill_v2 9/16 (56%) |

（另：5 个 flow 任务 3 臂全过，含 3 个 trap 陷阱任务——历史同题亦全过，无区分度，不计入。）

## 关键发现

1. **裸模型能力飞跃**：baseline 从 7/16 (44%) → 13/16 (81%)（+37.5pp）。SWE-bench 从 3/6 → **6/6 全解**，其中 flask-4045、pytest-6116 是 qwen3.6 从未解出的题；qwen3.8 裸模型已达 deepseek-v4-flash 的 SWE-bench 天花板。polyglot 4/10 → 7/10。
2. **触发率大反转（最反直觉）**：71KB 完整版（q38_v2）在 qwen3.8 上 **12/16 (75%) 自主触发**——qwen3.6 时代仅 12.5%、deepseek-v4-flash 为 0%。此前"体积是触发率决定性变量、模型越强越不会加载大 skill"的结论被推翻：qwen3.8 主动加载完整版并产出全场最高分。
3. **v2 完整版自主触发 = 历史最高成绩**：15/16 (94%) 超越此前所有臂（含 ds_full_forced 87.5%）。完整版工作流（acceptance.md、验证循环、测试先行）在 qwen3.8 上被真实执行并转化为收益（phone_number 21/21、grade_school 20/20、bowling 31/31）。
4. **mini 相对价值下降**：q38_mini_v2 12/16 < baseline 13/16（-1 题，噪声内）。mini 的核心纪律（先测后写、验证再收工）对 qwen3.8 接近原生行为——与 deepseek 上"mini 无增益"的结论一致，27B 时代 mini 的优势来自补足弱模型缺失的纪律。
5. **自测≠隐藏测试**：phone_number 上 mini 臂 0/21——模型忠实执行了 mini 的 RED→GREEN 流程（自写验证 23/23 全过），但自测规范与隐藏测试（Exercism 风格：ValueError + pretty()）不一致，自测全绿仍 0 分；同题 baseline 14/21、v2 21/21。skill 引导的自测不能替代真实测试集。
6. **成本大幅上升**：qwen3.8 平均耗时是 qwen3.6 的 2-4 倍（baseline 230s vs 69s、v2 515s vs 134s）。思考增强（thinking 深）与完整版工作流双重叠加。

## 对 vibeweaver 的结论更新（模型换代后）

| | qwen3.6_27b（旧） | qwen3.8_27b（新） | deepseek-v4-flash |
|---|---|---|---|
| 裸模型 | 7/16 (44%) | **13/16 (81%)** | 11/16 (69%) |
| 完整版自主触发 | 12.5% | **75%** | 0% |
| 完整版自主效果 | 9/16 (56%) | **15/16 (94%)** | 11/16 (69%) |
| mini 自主效果 | 8/16 (50%) | 12/16 (75%) | 11/16 (69%) |
| 最优形态 | mini 自主 | **完整版自主（或 mini+渐进披露）** | 完整版强制 |

**直接回答"模型升级是否真实提升"**：是，且幅度巨大。qwen3.8_27b 在相同提示词/任务/评分下 baseline 13/16 vs qwen3.6 的 7/16（+6 题，SWE-bench 3→6 全解，远超任务级 ±2-3 题方差）；同时模型变强后 vibeweaver 完整版从"不触发/低触发"变为 75% 自主触发，94% 通过率刷新全部历史臂纪录——升级后"完整版自主"取代"mini 自主"成为 27B 档的最优配置。

## 复现

```bash
# 新建 3 臂配置（q38_baseline/q38_mini/q38_v2，模型改为 local/qwen3.8-27b）
EVAL_MODEL=local/qwen3.8-27b python3 harness/run_eval.py --arm q38_baseline --concurrency 3
EVAL_MODEL=local/qwen3.8-27b python3 harness/run_eval.py --arm q38_mini_v2 --concurrency 3
EVAL_MODEL=local/qwen3.8-27b python3 harness/run_eval.py --arm q38_v2 --concurrency 3
# 评分同前（grade_polyglot.py / grade_swebench.py / grade_flow.py）
```

原始数据: `workspace/iteration-1/runs/result_*__q38_*.json` + `workspace/iteration-1/graded/grade_*__q38_*.json`（63 次运行全部落盘，零超时）。

### qwen3.8_27b vs deepseek-v4-flash（同口径，ds 数据来自第三/四轮 2026-08-01）

| 臂 | qwen3.8_27b | deepseek-v4-flash | 差值 |
|---|---|---|---|
| 裸模型 (baseline) | **13/16 (81%)** | 11/16 (69%) | +2 题 |
| mini 自主 | 12/16 (75%) | 13/16 (81%)（ds_mini_v2 干净环境重跑） | -1 题 |
| 完整版自主 | **15/16 (94%)** | 11/16 (69%)（ds_full 触发 0%=裸模型） | +4 题 |
| 完整版强制 | — | 14/16 (87.5%) | — |

**跨模型排名（同 16 题）**：q38_v2 15/16 > ds_full_forced 14/16 > q38_baseline 13/16 = ds_mini_v2 13/16 > q38_mini_v2 12/16 > ds 其余臂 11/16。

**要点**：qwen3.8 裸模型已是该评测集最强（SWE-bench 双方 6/6 饱和，差距在 polyglot 7/10 vs 5/10）；qwen3.8 自主触发完整版（94%）反超 ds 强制加载（87.5%）；mini 对两个"已具备纪律"的模型均无增益。

---

# 第七轮：新版 mini（当前发布版 5.7KB）复测（2026-08-15）

## 背景

vibeweaver-mini 发布版已从评测时代的 2.2-2.6KB 扩到 5.7KB（新增前端三层测试标准、完整 TDD 循环、修复循环细则、收尾报告）。此前 q38 轮的 mini 数据均来自旧版 2.6KB（configs/q38_mini）。本轮用**当前发布版**（configs/q38_mini_new，SKILL.md 与发布目录逐字节一致）复测 16 题，与旧版 mini、完整版、baseline 对比。

## 配置

- 模型: qwen3.8_27b @ OpenAI 兼容端点（同前，temperature 0.6）
- Agent: opencode 1.18.18 headless
- 1 臂 × 16 题（10 polyglot + 6 SWE-bench Lite），提示词/任务集/评分脚本与前轮完全一致
- 新增配置：configs/q38_mini_new（复制 q38_mini，仅替换 skill 为当前发布版 5.7KB）

## 结果（16 题）

| 臂 | polyglot 10 | SWE-bench 6 | 合计 |
|---|---|---|---|
| q38_baseline | 7/10 | 6/6 | 13/16 (81%) |
| q38_mini_v2（旧版 mini 2.6KB） | 6/10 | 6/6 | 12/16 (75%) |
| q38_v2（完整版 71KB） | 9/10 | 6/6 | 15/16 (94%) |
| **q38_mini_new（新版 mini 5.7KB）** | **8/10** | **5/6** | **13/16 (81%)** |

### 逐题对比（四臂）

| 任务 | baseline | 旧mini | 完整版 | 新版mini |
|---|---|---|---|---|
| polyglot_bowling | ✅ | ❌ | ✅ | ✅ 31/31 |
| polyglot_grade_school | ❌ | ❌ | ❌ | ✅ 20/20 |
| polyglot_list_ops | ❌ | ❌ | ❌ | ✅ 24/24 |
| polyglot_phone_number | ❌ | ❌ | ✅ | ❌ 6/21 |
| polyglot_simple_linked_list | ✅ | ✅ | ✅ | ❌ 17/20 |
| polyglot_pig_latin | ✅ | ✅ | ✅ | ✅ |
| polyglot_robot_name | ✅ | ✅ | ✅ | ✅ |
| polyglot_transpose | ✅ | ✅ | ✅ | ✅ |
| polyglot_two_bucket | ✅ | ✅ | ✅ | ✅ |
| polyglot_variable_length_quantity | ✅ | ✅ | ✅ | ✅ |
| swebench_flask_4045 | ✅ | ✅ | ✅ | ❌ |
| swebench_flask_4992 | ✅ | ✅ | ✅ | ✅ |
| swebench_requests_3362 | ✅ | ✅ | ✅ | ✅ |
| swebench_pytest_6116 | ✅ | ✅ | ✅ | ✅ |
| swebench_pytest_9359 | ✅ | ✅ | ✅ | ✅ |
| swebench_sympy_21627 | ✅ | ✅ | ✅ | ✅ |

## 关键发现

1. **新版 mini 优于旧版 mini（+1 题，polyglot 6/10 → 8/10）**：新条款（测试先行强调、前端三层标准、验收标准前置）在 polyglot 上生效——grade_school 20/20、list_ops 24/24 是**四臂中唯一解出**的任务（旧 mini 与完整版都失败）；bowling 从旧 mini 的失败变为 31/31 满分。前端向的 TDD 条款确实转化为收益。
2. **SWE-bench 出现唯一回退（6/6 → 5/6）**：flask_4045 四臂中只有新版 mini 失败。16 题样本下 ±1 在任务级方差内，但方向值得注意：新增的测试先行/验收标准条款在真实仓库任务上可能挤占了探索时间（该任务 wall 1398s，全场最长）。
3. **vs baseline 打平（13/16 = 13/16）**：新版 mini 在 qwen3.8 上仍无净增益——与旧结论一致（mini 供给的纪律对已具备纪律的模型无增益），但构成变了：polyglot 8/10 反超 baseline 的 7/10，SWE 5/6 落后 1 题。
4. **完整版仍领先**：15/16 (94%) > 13/16。qwen3.8 上"完整版自主触发"仍是最优形态；新版 mini 的 5.7KB 已能 100% 触发（polyglot 10/10 全部加载 skill），但机制密度不足以追平完整版（验收清单、doc↔code 审计、验证闸门）。
5. **成本居中**：均值 329s/题（baseline 189-230s / 旧mini 254s / 完整版 518s）。5.7KB 的新版 mini 比 2.6KB 旧版贵约 30%，仍显著低于完整版。

## 对 vibeweaver-mini 的结论

新版 mini 在小模型档的定位不变（弱指令遵循模型的最高杠杆配置），在 qwen3.8 档从"持平基线"变为"polyglot 反超、SWE 欠 1"，净效果与完整版差距稳定在 -2 题。若后续要缩小差距，方向明确：把完整版的 doc↔code 审计（A4.7）压缩进 mini 的 workflow 测试条款。

## 复现

```bash
# 配置：复制 q38_mini 为 q38_mini_new，将 skills/vibeweaver-mini/SKILL.md 替换为当前发布版
EVAL_MODEL=local/qwen3.8-27b python3 harness/run_eval.py --arm q38_mini_new --benchmark polyglot --concurrency 3
EVAL_MODEL=local/qwen3.8-27b python3 harness/run_eval.py --arm q38_mini_new --benchmark swebench_lite --concurrency 3
# 评分同前
```

原始数据: `workspace/iteration-1/runs/result_*__q38_mini_new.json` + `workspace/iteration-1/graded/grade_*__q38_mini_new.json`（16 次运行全部落盘，零超时）。

---

# 第八轮：qwen3.6-35b-a3b（极弱模型）四臂对照（2026-08-15）

## 配置

- 模型: **qwen3.6_35b-a3b** @ OpenAI 兼容端点（llama.cpp 后端，GGUF Q5_K_M 量化，34.6B 总参 / ~3B 激活 MoE，n_ctx 262144）
- Agent: opencode 1.18.18 headless
- 4 臂 × 16 题（10 polyglot + 6 SWE-bench Lite），提示词/任务集/评分脚本与前轮完全一致
- 新增隔离配置：configs/a3b_baseline / a3b_mini_old（旧版 mini 2.6KB）/ a3b_mini_new（当前发布版 mini 5.7KB）/ a3b_full（完整版 71KB），仅模型与端口更换

## 结果（16 题）

| 臂 | polyglot 10 | SWE-bench 6 | 合计 | 触发率（polyglot） |
|---|---|---|---|---|
| a3b_baseline | 2/10 | 4/6 | 6/16 (37.5%) | — |
| a3b_mini_old | 2/10 | 4/6 | 6/16 (37.5%) | **1/10** |
| a3b_mini_new | 2/10 | 4/6 | 6/16 (37.5%) | **0/10** |
| a3b_full | 3/10 | 4/6 | 7/16 (43.8%) | **0/10** |

## 关键发现

1. **触发层彻底崩塌（本轮最重要的结论）**：35b-a3b 对 skill 工具**几乎零调用**——旧 mini 1/10、新 mini 0/10、完整版 0/10。此前的"体积决定触发率"规律在极弱模型上失效：qwen3.6-27B 会加载 2.2KB mini（62.5%），qwen3.8-27B 连 71KB 完整版都主动加载（75%），但这个模型连读 available_skills 都懒得读——日志显示它直接 Read prompt.md 开干，从不调用 skill 工具。**模型弱到一定程度，skill 机制整体失效，无论体积。**
2. **四臂结果 ≈ 裸模型 ± 噪声**：6/16 vs 6/16 vs 6/16 vs 7/16，差值全部在任务级方差（±2-3 题）内。逐题看全是噪声：list_ops 24/24 只在 a3b_full 过（此前只有 qwen3.8+新版 mini 过过）、two_bucket 9/9 只在 a3b_mini_new 过、flask_4045 只有 a3b_baseline 过——没有一个差分可以被归因于 skill 生效。
3. **SWE-bench 与 polyglot 表现倒挂**：裸模型 SWE-bench 4/6（flask_4045/4992、requests_3362、sympy_21627 全过）但 polyglot 只有 2/10。3B 激活的弱模型在"读仓库修 bug"上比"纯函数算法题"强——前者可以抄现成模式，后者需要推理。
4. **放弃率信号**：多臂出现 `no diff produced`（agent 直接放弃没产出补丁）：baseline 1 次、旧 mini 1 次、新 mini 1 次、完整版 1 次——弱模型在面对 SWE-bench 时存在系统性弃坑。
5. **成本最高的一轮**：llama.cpp 后端（~27 tok/s 提示、~77 tok/s 生成）导致均值 700-943s/题，每臂 2-4 次撞 2400s 超时上限；完整版臂最贵（均值 943s，4 次超时）。

## 对 vibeweaver 家族的结论

极弱模型（≈3B 激活）是 skill 机制的死角：不是规则写得不够好，是模型根本不加载。**对这类模型，skill 需要降级为提示词强制注入或 AGENTS.md 常驻指令**（本评测集未测注入臂——qwen3.6-27B 上强制注入反而有害 50% < 62.5%，值得后续专项验证）。若用户目标就是这类模型，vibeweaver 的收益要等到模型升级到 qwen3.6-27B 档才会出现。

## 复现

```bash
# 4 臂配置已就绪（configs/a3b_*，模型 qwen3.6_35b-a3b @ port 18002）
EVAL_MODEL=local/qwen3.6-35b-a3b python3 harness/run_eval.py --arm a3b_baseline --benchmark polyglot --concurrency 3
# 其余臂同，依次 a3b_mini_old / a3b_mini_new / a3b_full；SWE-bench 用 --benchmark swebench_lite
# 评分同前
```

原始数据: `workspace/iteration-1/runs/result_*__a3b_*.json` + `workspace/iteration-1/graded/grade_*__a3b_*.json`（64 次运行全部落盘；8 次超时 2400s）。

## 第八轮补充：强制注入三臂（2026-08-16）

上轮结论"对极弱模型需降级为强制注入"未实测，本轮补测。3 臂 × 16 题（prompt 全文注入 SKILL.md，`--force-skill`），其余配置同第八轮。

| 臂 | polyglot 10 | SWE-bench 6 | 合计 | mean_s | 超时 |
|---|---|---|---|---|---|
| a3b_baseline（对照） | 2/10 | 4/6 | 6/16 (37.5%) | 764 | 2 |
| a3b_mini_old_forced | 1/10 | 3/6 | 4/16 (25%) | 857 | 1 |
| **a3b_mini_new_forced** | **4/10** | 3/6 | **7/16 (43.8%)** | 1092 | 3 |
| a3b_full_forced | 4/10 | 1/6 | 5/16 (31.3%) | 2063 | 9 |

逐题亮点：a3b_mini_new_forced 在 bowling 拿到 **31/31 满分**（自主轮仅 22/31）、robot_name 4/4、transpose 12/12——新版 mini 的 TDD/测试先行条款在强制注入下被真实执行并转化为收益；但 SWE 从自主轮的 4/6 掉到 3/6。a3b_full_forced SWE 仅 1/6 且 **5 次 no diff produced**（模型被 71KB 注入淹没直接放弃），成本翻倍（2063s，9 次超时）。

结论更新：

1. **强制注入新版 mini 是极弱模型上唯一正增益路径**：7/16 > baseline 6/16，polyglot 4/10 全场最高。模型不主动加载 skill 的缺陷被注入绕过后，条款真实生效。
2. **强制注入完整版 = 灾难，不可用**：71KB 全文对 3B 激活模型是上下文毒药——SWE 几乎全灭、成本翻倍、超时率 56%。极弱模型的注入版必须 ≤5.7KB 档位。
3. **强制注入旧 mini 反而有害**（4/16 < 自主 6/16）：2.6KB 旧版只有规则骨架、没有可执行细节（无 RED 证据要求、无验收标准条款），注入后既占上下文又不产生纪律收益。qwen3.6-27B 上"mini 强制有害"的规律在 35b-a3b 上仅对旧版重现——新版 mini 的条款密度才是注入有效的关键。
4. **对极弱模型的最终处方**：新版 mini + 强制注入（或 AGENTS.md 常驻），别碰完整版注入。

---

# 第九轮：qwen3.8-27B 完整版强制注入补测（2026-08-16）

## 背景

此前 qwen3.8 轮只有三臂（baseline / mini_v2 / v2 自主），完整版强制注入缺失——而 qwen3.6（9/16）、deepseek（14/16）、35b-a3b（5/16）都有强制注入数据。本轮补上，形成四模型 × 强制注入的完整矩阵。

## 配置

- 模型: qwen3.8_27b @ OpenAI 兼容端点（同前）
- 1 臂 × 16 题（10 polyglot + 6 SWE-bench Lite），复用 q38_v2 配置 + `--force-skill`

## 结果（16 题）

| 臂 | polyglot 10 | SWE-bench 6 | 合计 |
|---|---|---|---|
| q38_baseline | 7/10 | 6/6 | 13/16 (81%) |
| q38_mini_v2（旧 mini 自主） | 6/10 | 6/6 | 12/16 (75%) |
| q38_v2（完整版自主） | 9/10 | 6/6 | 15/16 (94%) |
| **q38_v2_forced（完整版强制）** | **10/10** | **6/6** | **16/16 (100%)** |

- polyglot **10/10 全满分**：bowling 31/31、grade_school 20/20、list_ops 24/24、phone_number 21/21、pig_latin 22/22、robot_name 4/4、simple_linked_list 20/20、transpose 12/12、two_bucket 9/9、variable_length_quantity 26/26
- SWE-bench 6/6，P2P 守卫全绿
- **全场历史最高分**：超越此前所有模型所有臂（含 q38_v2 自主 15/16、ds_full_forced 14/16）

## 关键发现

1. **强制注入 > 自主触发**（16/16 vs 15/16）：qwen3.8 上完整版强制注入刷出评测史上第一个满分，比自主触发多 1 题（phone_number 21/21 是自主轮唯一失败的题）。此前"qwen3.8 完整版自主触发已是最优形态"的结论需要修正为"强制注入更优"。
2. **成本翻 3.5 倍**：均值 1820s/题 vs 自主 518s（+251%）。完整版全文注入（71KB）+ 高遵循度 = 每题都走完整验证循环，时间代价巨大。100% 通过率是用时间买的。
3. **四模型强制注入完整矩阵**：qwen3.6 9/16 (56%) · qwen3.8 **16/16 (100%)** · deepseek 14/16 (87.5%) · 35b-a3b 5/16 (31.3%)。强制注入的效果随模型能力单调上升，qwen3.8 达到顶格。

## 复现

```bash
EVAL_MODEL=local/qwen3.8-27b python3 harness/run_eval.py --arm q38_v2 --force-skill --benchmark polyglot --concurrency 3
EVAL_MODEL=local/qwen3.8-27b python3 harness/run_eval.py --arm q38_v2 --force-skill --benchmark swebench_lite --concurrency 3
```

原始数据: `workspace/iteration-1/runs/result_*__q38_v2_forced.json` + `workspace/iteration-1/graded/grade_*__q38_v2_forced.json`（16 次运行全部落盘，零超时）。
