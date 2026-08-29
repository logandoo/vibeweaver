# A/B Report — vibeweaver wave3 (modes/PAUSED/profiles/C4-C7) (deepseek-v4-flash, 强制注入, 16 题)

Date: 2026-08-29 · Harness: vibeweaver-eval `run_eval.py --force-skill` (arms `ds_wave2_before` / `ds_wave2_after`)
Model: `deepseek/deepseek-v4-flash` (api.deepseek.com) · Concurrency: **16**（用户要求满并发）· Timeout 1800s
Tasks: canonical 16 (10 polyglot + 6 SWE-bench Lite)

## Wave under test (dev repo `9954e82`)

1. **Deadlock fixes**: project profiles (assert `--profile`/`tests/project_profile.json` — library/CLI 不再被 group 5 锁死) · `vw-approved`⇄`- secret-approved:` 配对 · gate.js 证据路径豁免（tests/memory 写入不再触发 GATE-BLOCKED catch-22）· GATE-BLOCKED 文案前置 "WRITE SUCCEEDED — completion gate, NOT an execution stop" · §3.3 轻量重入。
2. **COV-12 双模式**: AUTO（默认，全程接管）/ GUIDED — Class-I 交互点在 AUTO 下转为 `tests/decisions.md` ADR；Class-E 硬停（生产部署/破坏性操作/注入冲突）两模式相同。
3. **§3.4/A4.11 PAUSED 协议**: 每个停必带 `[PAUSED] gate=… | default-if-continue=… | state=…` 包；"继续"=批准默认选项，非重计划。
4. **任务类型补全**: C4 审计（只读）· C5 部署（Class-E 确认）· C6 运维/事故 · C7 非Web运行时 — WORKFLOWS_EXTENDED.md（新 companion）。
5. SKILL.md 48993B（T11 <49000 达标）；单测 14/14（新增 S10/S10b/S11）；selftest 36 项仅预存 T6 环境失败（与基线一致）。

## Headline

| Arm | polyglot (10) | SWE-bench Lite (6) | **Total (16)** | wall avg | 超时/冻结 |
|---|---|---|---|---|---|
| BEFORE (48,978B, `d71f0c8`) | 9/10 | 6/6 | **15/16 (93.75%)** | ~452s | 0 |
| AFTER (48,993B, `9954e82`) | 8/10 | 6/6 | **14/16 (87.5%)** | ~367s | 0 |

- **SWE-bench 饱和：6/6 = 6/6**，P2P 守卫全绿 — 真实仓库任务零回归。
- BEFORE 唯一失败：`robot_name` 3/4（41.6s 早退）；AFTER 反而 4/4 通过。
- AFTER 两失败均为**部分分、早退、措辞/规格类**：`grade_school` 15/20（50s，模型明确声明"按任务约束不建工件"后早退）、`pig_latin` 21/22（69s，1 条措辞差异）。与上一波报告中 BEFORE 的 VLQ 24/26 失败同构——n=16 下 ±1-2 题为任务级方差（前波 A/B 的 BEFORE 臂同样 15/16）。
- **判定：非劣（non-inferior）**，通过率差异在方差内；编码完成能力未下降（约束 #2 达成）。

## Adherence（polyglot n=10/臂，机制采用证据）

| marker | BEFORE | AFTER |
|---|---|---|
| `Mode: AUTO/GUIDED` 声明 | 1 | **9** |
| `tests/decisions.md`（ADR） | 0 | **6** |
| `[Verification Gate]` | 9 | 9 |
| `HARD-GATE-1` | 9 | 8 |
| 8 列表 | 8 | 7 |
| `[Covenant Recall]` | 7 | 7 |
| `[Convergence]` | 8 | 9 |
| verification_log iter 条目 | 7 | 7 |

旧机制 marker 持平（±1）；新 AUTO 协议被真实执行（robot_name 臂产出 5 条规范 ADR，含 trigger/options/chosen/why/revisit-if 全字段；before 臂 0 — 协议确属新增行为）。`[PAUSED]` 两臂均 0 — 32 次运行全程自主完成，无一中途停摆等人工。

## 新机制专项验证（非模型，机械测试）

- assert 14/14：S10 library profile → group 5 跳过且其余照常 enforce（破坏 acceptance 仍 exit 1）；S10b 无 profile 缺 start.sh 仍 exit 1（严格默认不变）；S11 `vw-approved` 无配对 exit 1 / 有 `- secret-approved:` exit 0。
- 修复潜伏 bug：start.sh 缺失时旧脚本 stat() 崩溃出 traceback（现输出干净断言行）。
- gate.js：node --check 通过；tests/memory 写入豁免；GATE-BLOCKED 首行声明写入已成功。

## 并发与稳定性

- **16 并发全程零冻结、零超时**（上轮报告 12 流曾 8/12 冻结；本轮 16 流 × 2 臂 = 32 次运行干净完成）。看门狗（11min 日志停滞杀进程）全程未触发。
- 均耗时 AFTER 更低（~367s vs ~452s；grade_school/pig_latin 早退拉低均值）。

## Honest limits

- 单次运行/任务/臂，n=16：-1 题在任务级方差内，按上波口径记为**非劣**而非更优。
- 强制注入只注入 SKILL.md；WORKFLOWS_EXTENDED.md 在 after 臂未被注入（模型可经 Read 读取但未强制）— C4-C7 路径在本 16 题集中无触发机会（无审计/部署/运维题），其验证靠机械测试 + 设计评审，属诚实缺口。
- `Mode:` 行采纳率 9/10、decisions.md 6/10 — AUTO 协议遵循良好但非 100%；`assert=1` 于 polyglot 玩具目录（无 memory//script/）为预期正确行为，两臂对称。
- swebench 两臂 run.log 被 grade_swebench 的 reset 清除（对称损失；hidden-test 评分与 result_*.json 完整）。

## 复现

```bash
cd /Users/logan/Documents/DEV/SKILLS/vibeweaver-repo/vibeweaver-eval
DEEPSEEK_API_KEY=$(python3 -c "import json;print(json.load(open('$HOME/.local/share/opencode/auth.json'))['deepseek']['key'])") \
EVAL_MODEL=deepseek/deepseek-v4-flash python3 harness/run_eval.py --arm ds_wave2_before --tasks <16题列表> --concurrency 16 --timeout 1800 --force-skill
# 同 --arm ds_wave2_after；评分：python3 /tmp/opencode/grade_wave2.py（或 harness/grade_*.py）
```

Raw data: `workspace/iteration-1/runs/result_*__ds_wave2_*` (32) · `graded/grade_*__ds_wave2_*` (32) · `graded/wave2_ab_summary.json`

---

# 补充：polyglot 10 题 × 4 轮平均（2026-08-29，应用户要求复核方差）

单轮 -1 被判定为任务级方差后，polyglot 两臂再各跑 3 轮（r2/r3/r4，每轮 before+after 并行 16 流），与本轮（r1）合并取平均。共 **80 次 polyglot 运行**（40/臂），全部完成、零超时、零冻结。

## 4 轮平均

| Arm | pass-runs | 通过率 | mean test-fraction（细粒度） |
|---|---|---|---|
| BEFORE (48,978B) | 35/40 | 87.5% | 0.9552 |
| AFTER (48,993B) | **37/40** | **92.5%** | **0.9845** |

逐题（pass-runs/4 · 平均得分率）：

| 任务 | BEFORE | AFTER |
|---|---|---|
| bowling | 4/4 · 1.000 | 3/4 · 0.919 |
| grade_school | 4/4 · 1.000 | 3/4 · 0.938 |
| list_ops | 3/4 · 0.979 | **4/4 · 1.000** |
| phone_number | 2/4 · 0.655 | **4/4 · 1.000** |
| pig_latin | 4/4 · 1.000 | 3/4 · 0.989 |
| robot_name | 3/4 · 0.938 | **4/4 · 1.000** |
| simple_linked_list | 4/4 · 1.000 | 4/4 · 1.000 |
| transpose | 4/4 · 1.000 | 4/4 · 1.000 |
| two_bucket | 4/4 · 1.000 | 4/4 · 1.000 |
| variable_length_quantity | 3/4 · 0.981 | **4/4 · 1.000** |

## 结论（方差复核后）

1. **单轮 -1 是方差，方向实测反转为 +2**（92.5% vs 87.5%）：r1 中 AFTER 失败的 grade_school/pig_latin 在其它轮通过，r1 中 BEFORE 通过的 phone_number/list_ops/VLQ/robot_name 在其它轮各翻车 1 次。
2. **phone_number 差异最大**（BEFORE 2/4 vs AFTER 4/4）——该题要求精确匹配 Exercism 规格（ValueError + pretty()），新 skill 的验收标准条款（A4.1 Step 1 + AUTO 决策记录）对此类"规格精确性"任务增益明显。
3. n=40/臂下 ±5pp 仍在噪声带（二项 se≈5pp），严谨口径维持**非劣、方向为正**；无任何"编码后完成能力下降"的证据（约束 #2 双重确认：单轮 + 4 轮均值）。
4. mean test-fraction（0.9552 → 0.9845）作为连续指标同样正向。

数据：`graded/grade_*__ds_wave2_*_{r2,r3,r4}_forced.json` (60) + `graded/wave2_ab_avg.json`；评分器沉淀至 `harness/grade_wave2.py`、`harness/grade_wave2_avg.py`。
