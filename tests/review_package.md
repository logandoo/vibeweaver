# Review package — W2-ISO（baseline accfbd1 → working tree；排除本文件自身）

## git log --oneline accfbd1..HEAD
```
5a01e4e fix(w2-iso): seed scrubbed state DB (schema+credential+kv) for model routing + classify agent-startup failures as indeterminate (wip-iter-4)
6bafc01 fix(w2-iso): bind subject agent to worktree (PWD + directory positional + temp HOME) and fail closed on containment violations (wip-iter-2)
b6afd5a test(w2-iso): RED isolation suite + C3 plan (wip-iter-1)
```

## git diff --stat accfbd1（不含 tests/review_package.md）
```
 docs/PLAN_w2_iso_20261023.md                       |  74 ++++++++
 docs/UNFINISHED_20261023.md                        |  17 +-
 memory/MEMORY.md                                   |   3 +-
 memory/project_w2_eval_lab.md                      |  21 ++-
 scripts/eval_run.py                                | 198 +++++++++++++++++++--
 tests/.evidence.lock                               |  12 +-
 tests/acceptance.md                                |  10 ++
 tests/coverage_matrix.md                           |  10 ++
 tests/decisions.md                                 |   2 +
 tests/eval/lab/scenarios/smoke.json                |   1 +
 tests/eval/runs/smoke-20261023_025238/cost.json    |   5 +
 .../eval/runs/smoke-20261023_025238/isolation.json |  20 +++
 .../runs/smoke-20261023_025238/trajectory.json     |  13 ++
 tests/eval/runs/smoke-20261023_025238/verdict.json |  10 ++
 tests/eval/runs/smoke-20261023_031133/cost.json    |   5 +
 .../eval/runs/smoke-20261023_031133/isolation.json |  23 +++
 .../runs/smoke-20261023_031133/trajectory.json     |  13 ++
 tests/eval/runs/smoke-20261023_031133/verdict.json |  10 ++
 tests/gate_result.json                             |   2 +-
 tests/perf/perf_20261023_023827.log                |   7 +
 tests/test_eval_isolation.py                       | 183 +++++++++++++++++++
 tests/verification_log.md                          |  24 +++
 tests/w2iso_baseline.log                           |  59 ++++++
 tests/w2iso_full_suite.log                         |   5 +
 tests/w2iso_green.log                              |  11 ++
 tests/w2iso_green2.log                             |  13 ++
 tests/w2iso_real_smoke2.log                        |   1 +
 tests/w2iso_red.log                                |  75 ++++++++
 tests/w2iso_regression.log                         |  20 +++
 tests/w2iso_regression2.log                        |  16 ++
 tests/working_note.md                              |  38 ++++
 31 files changed, 863 insertions(+), 38 deletions(-)
```

## git diff -U10 accfbd1（不含 tests/review_package.md）
```diff
diff --git a/docs/PLAN_w2_iso_20261023.md b/docs/PLAN_w2_iso_20261023.md
new file mode 100644
index 0000000..5a49544
--- /dev/null
+++ b/docs/PLAN_w2_iso_20261023.md
@@ -0,0 +1,74 @@
+# W2-ISO 实施计划：eval_run 的 opencode worktree 隔离（Lane L / C3）
+
+**Goal:** 关闭 `docs/UNFINISHED_20261023.md` §3 的 **W2-ISO**（P0 阻塞项）：`scripts/eval_run.py --agent opencode` 的主体 agent 必须绑定在临时 worktree，运行后 worktree/沙箱之外零写入，verdict 三值正确（污染运行永不 `pass`）；并用真实 `--scenario smoke --agent opencode` 收口 W2-T12。
+**Architecture:** 单文件修复（`scripts/eval_run.py`）+ 独立隔离测试（`tests/test_eval_isolation.py`，用 PATH 注入的 stub `opencode` 做确定性回放）+ 真实 smoke 作为端到端证据。
+**Tech Stack:** Python 3 标准库（subprocess/unittest/tempfile）· opencode CLI v2.1.3（被测对象）· 本仓库既有 `tests/` 断言体系。
+**执行顺序:** §A4.8 test-first（RED→GREEN→回归三步）→ 真实 smoke → 覆盖矩阵/FCV/对抗复审 → 完成表。
+
+## Global Constraints
+
+- `cap=5  stall=3×`（COV-7）；测试只读（§V2）：本波只**新增** `tests/test_eval_isolation.py`，不改既有断言。
+- 不跑任何 G3 / rule-TDD live eval（UNFINISHED §6）；本波只跑 smoke（1 场景 × 少量 runs）。
+- 不移动已发布 tag；不用 `git add -A`。
+- 运行证据只落 `tests/eval/runs/<id>-<ts>/`（`--out` 可重定向，测试用 tmp）。
+- 被测 agent 的 HOME/环境不得指向宿主 repo（W6 教训：env/config 也是泄露通道）。
+
+## Consistency Hub
+
+| Entity | Canonical value/type | Source of truth |
+|---|---|---|
+| CLI 目录绑定形式 | `opencode run [flags] <directory> <message...>`（目录位置参数在 message **之前**） | 实测：`probe_c.txt` 落 `/tmp/vwprobe5`；`opencode --help` v2.1.3 `opencode <subcommand> [flags] [<directory>]` |
+| 环境目录绑定 | `env["PWD"] = str(work)`（实测 opencode 会话目录取 `$PWD`，不取进程 cwd） | 实测：cwd=/tmp/vwprobe3 + `PWD=/tmp/vwprobe_decoy` → `probe_a.txt` 落 decoy |
+| HOME 隔离 | `env["HOME"] = str(home)`；删除 `XDG_*`、`OLDPWD`、`OPENCODE_*`、值含宿主 repo 路径的变量 | `seed_auth()` 布局：`home/.local/share` · `home/.cache` · `home/.config` |
+| 播种面（模型路由） | `auth.json` + `models.json` + `opencode.jsonc` + **scrubbed `opencode.db`**（schema + `credential` + `kv`；`DB_CONTENT_TABLES` 18 张内容表清空、`job.%` 键剔除） | 实测二分：provider 路由 = `credential` 表 + `kv.models-dev:catalog`；整库含 42,773 条宿主 `session_message`（答案面）→ 必须 scrub（ADR D-W2ISO-1） |
+| 沙箱边界 | `tmp` = `tempfile.mkdtemp(prefix="vw-eval-")`；worktree = `tmp/work`；评分用 home = `tmp/home` | `scripts/eval_run.py:81-83` |
+| 越界监控（两腿） | ① 宿主 repo `git status --porcelain` 前后差分（剔除本次证据目录 `tests/eval/runs/<id>-<ts>/`）② 沙箱内 `work/` 之外的任务产物（场景 `artifacts` 声明的名字） | UNFINISHED §3 W2-ISO 判据「worktree 外 git status 零新增」 |
+| verdict 三值 | `pass`（隐藏测试 exit 0 且无违例）· `fail`（隐藏测试 exit 1 或 agent 非零退出）· `indeterminate`（隔离违例 / harness 捕获失败 = exit -1 / 隐藏测试非 0-1 退出）；**违例永不 pass** | `scripts/eval_run.py` docstring + acceptance #41 |
+| 运行证据文件 | `trajectory.json` · `cost.json` · `verdict.json` · **`isolation.json`**（新增） | `tests/eval/runs/smoke-20261023_*/` 既有结构 |
+| 场景任务产物声明 | `tests/eval/lab/scenarios/<name>.json` 新增 `"artifacts": ["hello.txt"]`（list[str]） | 本计划 Task 1 |
+| stub 回执格式 | stdout 首行 `VW-STUB cwd=<abs> pwd=<abs> home=<abs> argv=<rest>` | `tests/test_eval_isolation.py` |
+| 测试接缝 | CLI：`python3 scripts/eval_run.py --scenario smoke --agent opencode --model <stub> --out <tmp>` + PATH 注入 stub | 不新增内部 seam（seam 越少越好） |
+
+## Task 1 — 场景产物声明 + RED 测试
+
+**Files:** Modify `tests/eval/lab/scenarios/smoke.json` · Create `tests/test_eval_isolation.py` · Modify `tests/acceptance.md`（追加任务块）· Modify `tests/verification_log.md`。
+**Interfaces:** *Consumes* — `eval_run.py` CLI（`--scenario/--agent/--model/--out`）；*Produces* — 4 个 unittest 用例（`test_stale_pwd_binding`、`test_contamination_fails_closed`、`test_mock_isolated_and_hidden_test_outside`、`test_verdict_three_valued`）。
+**Test seam:** CLI（上表）；stub `opencode` 由测试写入 tmp 目录并前置到 `PATH`。
+**Steps:**
+1. `tests/eval/lab/scenarios/smoke.json` 增加 `"artifacts": ["hello.txt"]`。验证：`python3 -c "import json;print(json.load(open('tests/eval/lab/scenarios/smoke.json'))['artifacts'])"`。
+2. 写 `tests/test_eval_isolation.py`：stub `opencode` 把 `hello.txt` 写进 **`$PWD`**（复刻实测的 opencode 行为），并打印 `VW-STUB` 回执；测试用 `--out <tmp>` 跑 `eval_run`。
+3. **RED**：`python3 -m unittest tests.test_eval_isolation -v` → 观察 4 用例失败，输出贴进 `tests/verification_log.md`（含 `diagnosis:`）。
+
+## Task 2 — GREEN：绑定 + 越界检测（`scripts/eval_run.py`）
+
+**Files:** Modify `scripts/eval_run.py`。
+**Interfaces:** *Consumes* — Task 1 的 CLI 契约；*Produces* — `build_env(work, home, root) -> dict`、`git_status_lines(root) -> list[str]`、`sandbox_artifacts_outside_work(tmp, work, names) -> list[str]`、`isolation.json`（`{outside_repo_delta, sandbox_outside_work, violations, monitored}`）。
+**Steps:**
+1. `run_agent()`：`env = build_env(...)`（PWD/HOME 绑定 + XDG/OLDPWD/宿主路径变量清洗）；`cmd` 末尾插入 `str(work)` 位置参数（在 prompt 之前）。验证：Task 1 全绿。
+2. `main()`：agent 运行前后各取一次快照（宿主 `git status` 差分 + 沙箱产物扫描）→ 违例清单 → `isolation.json`；违例 → `verdict="indeterminate"`（覆盖隐藏测试结果）。验证：`test_contamination_fails_closed` 绿。
+3. 隐藏测试退出码：0→pass，1→fail，其他→indeterminate。验证：`test_verdict_three_valued` 绿。
+4. 回归三步（§A4.8）：`git stash`/`git restore` 修回旧实现 → 测试必须 FAIL → 恢复 → 绿。日志记 `- regression-cycle:`。
+
+## Task 3 — 真实 smoke（W2-T12 收口）
+
+**Files:** 新证据目录 `tests/eval/runs/smoke-<ts>/` · Modify `tests/verification_log.md`。
+**Steps:**
+1. `python3 scripts/eval_run.py --scenario smoke --agent opencode`（deepseek-flash）→ 产出 4 个 json。
+2. 检查 `isolation.json`：`violations == []`；宿主 repo `git status` 除证据目录零新增；`hello.txt` 只在 worktree；stderr 无宿主插件噪音（HOME 隔离证据）。
+3. 判定 criteria #45-#49，写入 `tests/coverage_matrix.md`。
+
+## Task 4 — 收口（Lane L 附加层）
+
+**Files:** `tests/coverage_matrix.md` · `tests/fcv_brief.md` / `tests/fcv_report.md` · `tests/review_package.md` + 对抗复审结论 · `memory/`（fix topic + `project_w2_eval_lab.md` 修订）· `docs/UNFINISHED_20261023.md`（状态回写）。
+**Steps:** 覆盖矩阵 → FCV 子代理（§V1）→ 双对抗复审（§V4）→ 记忆（A7.9）+ Memory Gate → `python3 scripts/evidence_seal.py` → `python3 tests/assert_artifacts.py --final` → 完成表（§A4.4）。
+
+## 自评（C3 inline）
+
+- **Coverage**：UNFINISHED §3 W2-ISO 三条完成判据 + §7 步骤 3 的「零新增」测试 = criteria #45-#49，逐条映射到 Task 1-3 的用例/命令（见 `tests/coverage_matrix.md`）。
+- **Placeholder scan**：无 TBD/「处理边界情况」；每个 Task 的验证命令都是可执行命令。
+- **Type consistency**：`build_env(work, home, root)` 签名在 Task 2 定义、Task 1 测试只经 CLI 观察（不 import 内部）；`artifacts` 为 `list[str]`，Task 1 与 Task 2 同名同型。
+
+## 已知 residual（不写进完成宣称）
+
+- 越界监控只覆盖**宿主 repo 树** + **沙箱内 work/ 之外的任务产物**；任意其他文件系统位置的写入未被监控（与 memory `fix_eval_answer_leak_w6` 的 residual 同类：同 uid agent 仍可盲走文件系统）。
+- HOME 隔离后 provider/auth 依赖播种的 `auth.json`/`models.json`/`opencode.jsonc` 三项；模型注册表仍与宿主共享（`run_agent` 注释中的「documented partial isolation」不变）。
diff --git a/docs/UNFINISHED_20261023.md b/docs/UNFINISHED_20261023.md
index 48c8599..861ede2 100644
--- a/docs/UNFINISHED_20261023.md
+++ b/docs/UNFINISHED_20261023.md
@@ -2,21 +2,21 @@
 
 > 状态快照：dev `8ef1a61`（工作树干净）· public `a5a3f3d` / tag `w18.3.5`。
 > 本文件只记录**尚未完成/未验证**的事项，避免把它们误当成已完成。
 > 规则：没有可复现证据的项一律写 `unchecked`，不写“应该可以”。
 
 ## 0. 先看结论
 
 - **W0（P0）已完成并发布**：`w18.2.4`（后续被 W1 取代）。
 - **W1 已发布 `w18.3.5`**，但 **Task 10（规则级 TDD pilot）未做**。
 - **W2 只完成 lab/power/prereg 的静态部分**；**Task 14 的 G3 live runs 没有跑**。
-- **当前最危险的未完成项是 eval 隔离**：`opencode run` 在临时 worktree 中把文件写到了宿主 repo 根目录（实测 `hello.txt`）。修好之前**禁止**跑任何 live eval。
+- **W2-ISO（eval 隔离）已于 2026-10-23 修复并验证**：`eval_run.py` 三重绑定 worktree + 越界 fail-closed，真实 smoke `--agent opencode` 通过（`tests/eval/runs/smoke-20261023_031133/`）。**仍未完成的最危险项改为 W2-T14 预算/场景**：96-run pilot 需要 8 个场景（当前 lab 只有 `smoke`）+ 模型预算上限。
 
 ## 1. 发布状态
 
 | 层 | 状态 | 说明 |
 |---|---|---|
 | W0 trust floor | ✅ 已发布 | `w18.2` → `w18.2.4`；manifest/checker pin/evidence lock/bootstrap/state |
 | W1 contract & gate | ✅ 已发布 | `w18.3` → `w18.3.5`；installer/core profile/gate/risk/destructive/security/claims/compat |
 | W2 eval | ⏳ 未发布 | dev 有 `eval_run/eval_report/eval_power/prereg`；public 仍是 `w18.3.5` |
 | W3 governance | ⬜ 未开始 | Task 17/18/19 |
 
@@ -27,21 +27,21 @@
 
 | ID | 项 | 状态 | 阻塞/下一步 | 完成判据 |
 |---|---|---|---|---|
 | W1-T10 | 规则级 TDD pilot（COV-1/COV-9/COV-0） | ⬜ 未做 | 需要 eval harness + 60 runs（3 规则 × 2 场景 × 5 reps × baseline/with-rule）；当前无预算 | `tests/rule_tdd/summary.json` 有 baseline/with-rule 合规率；无正向 pilot 的规则标 delete/downgrade |
 | W1-EXIT-REVIEW | W1 exit 双对抗复审 | ✅ 已做 | 两个 reviewer + 修复见 `tests/review_verdicts_w1.md`；发布 w18.3.5 | 无需重做；后续只做 scoped re-review |
 
 ## 3. W2 未完成（当前主战场）
 
 | ID | 项 | 状态 | 阻塞/下一步 | 完成判据 |
 |---|---|---|---|---|
-| W2-ISO | `eval_run.py --agent opencode` 的 worktree 隔离 | ❌ **危险** | 实测 agent 写到宿主 repo 根目录（`hello.txt`）；需改为 `opencode <directory> run …` 或每 worktree 独立 server；加“工作区外零写入”测试 | 临时 worktree 外无任何新文件；hidden test 仍在工作区外；verdict 三值正确 |
+| W2-ISO | `eval_run.py --agent opencode` 的 worktree 隔离 | ✅ 已修复并验证 | 根因=opencode 会话目录取环境 `$PWD`（不是 cwd）；三重绑定（CLI 目录位置参数 + `PWD=work` + `cwd=work`）+ 越界 fail-closed + scrubbed state DB 播种 | 临时 worktree 外零写入（`isolation.json` violations=[] 且宿主 `git status` 零新增）；hidden test 仍在工作区外；verdict 三值正确（污染=indeterminate）|
 | W2-T12 | Task 12 eval lab | 🟡 部分 | mock smoke 通过；real-opencode smoke 在 isolation 修复前 **unchecked** | `eval_run.py --scenario smoke --agent opencode` 产出 verdict/trajectory/cost，且隔离测试通过 |
 | W2-T14 | G3 live runs | ⬜ 未跑 | 96-run pilot（8×3×4）→ 192/240；需要模型/API 预算 + W2-ISO | `tests/eval/g3/summary.json` 有 n/seeds/95% CI/paired/MDE/cost；`status` 不是 `not_run` |
 | W2-T15 | 全量 13 COV rule TDD | ⬜ 未做 | 依赖 W1-T10 与 W2-T14；成本高 | `tests/rule_tdd/summary.json` 13/13 有 baseline + with-rule；无“未测但保留” |
 | W2-T16 | 独立复现 | 🟡 仅声明 | `docs/REPLICATION.md` 已写 `single-operator; no independent replication`；没有外部操作者 | 有非作者操作者按 prereg 跑完并签署；否则 README 保持 `no independent replication` |
 
 **W2 已完成（不要重做）：**
 
 - `scripts/eval_run.py`（mock lab）· `scripts/eval_report.py`（Wilson CI）· `scripts/eval_power.py`（MDE 0.286）
 - `docs/EVAL_G3_PREREG.md` + `tests/eval/g3/prereg.sha256`（冻结）
 - `tests/eval/g3/summary.json` = `not_run`（真实、无伪造）
@@ -73,25 +73,30 @@
 - **不要在 W2-ISO 修复前跑 G3/rule-TDD live eval**：agent 可能写到宿主 repo；这是数据污染风险。
 - **不要移动已发布 tag**（尤其 `w18.3.5`）；修复发新 tag。
 - **不要把 `not_run` / `indeterminate` 写成 pass**；不要用 `unchecked` 冒充 `na`。
 - **不要重跑已完成的 W0/W1 任务**：只会增加 release 噪声。
 - **不要用 `git add -A`**（destructive guard 会 block，且 45k 路径事故）；用 `git add -u` + 显式路径。
 
 ## 7. 恢复流程（新会话从这里开始）
 
 1. 读本文件 + `docs/PLAN_comprehensive_hardening_20261022.md` §W2。
 2. `git status --porcelain`、`git log -1`；确认 dev `8ef1a61`、public `a5a3f3d`。
-3. **先修 W2-ISO**：
-   - 让 `eval_run.py` 用 `opencode <directory> run …`（或每 worktree 独立 server）；
-   - 加测试：运行 mock/real smoke 后，worktree 外 `git status` 零新增；
-   - 再跑 `python3 scripts/eval_run.py --scenario smoke --agent opencode`。
+3. **先修 W2-ISO**（✅ 2026-10-23 已完成）：
+   - 根因不是目录参数形式，而是 **`opencode run` 的会话目录取环境变量 `$PWD`**（`cwd=` 无效）；
+     正确 CLI 形式是 `opencode run [flags] <directory> <message...>`（本文档原写的
+     `opencode <directory> run …` 实测解析失败，勿照抄）；实现=`PWD=work` + 目录位置参数 + 临时 HOME；
+   - 已加测试（`tests/test_eval_isolation.py`，8 用例）：mock/real smoke 后 worktree 外 `git status` 零新增、
+     越界 → `verdict=indeterminate`；
+   - 已跑通 `python3 scripts/eval_run.py --scenario smoke --agent opencode` → `verdict=pass`
+     （证据 `tests/eval/runs/smoke-20261023_031133/`）。
 4. 只有 W2-ISO 通过，才进入 Task 14 的 96-run pilot；预算上限先定（$ / 小时）。
+   **（W2-ISO 已通过；Task 14 现在缺的是 8 个场景 + 预算授权，不再缺隔离。）**
 5. 每步 TDD + 落盘证据；按 `cap=5 stall=3×`；不通过不进入下一步。
 6. W2 出口才 sync public + 发 `w19.0`；不要提前发布。
 
 ## 8. 证据索引
 
 - W0/W1 最终证据：`tests/w1_exit_assert2.log`（32/32）· `tests/review_verdicts_w1.md` · `tests/fcv_report_w1batch1.md` · `tests/fcv_report_w1batch2.md`
 - W1 release：`w18.3.5` / public `a5a3f3d`；CI run 39821704012（6/6）；Release 39821704007
 - W2 当前：`tests/test_eval_validity.py` 4/4 · `tests/w2_unit.log` · `tests/eval/g3/summary.json`（not_run）
 - 隔离事故：`tests/eval/runs/smoke-20261023_020914/trajectory.json`（agent stdout 承认写到宿主 repo 根目录）
 
diff --git a/memory/MEMORY.md b/memory/MEMORY.md
index acd944a..cc4ebbc 100644
--- a/memory/MEMORY.md
+++ b/memory/MEMORY.md
@@ -22,26 +22,27 @@
 - [AB Suite v2 反饱和方案](project_ab_suite_v2.md) — v1 饱和（q38_v2_forced 16/16）后的三层难度带 + 10 任务家族 + pass^k/bootstrap/退役治理设计；docs/AB_SUITE_V2_DESIGN.md；实现属后续波
 - [GitHub 文档债 已清偿 2026-10-13](project_github_doc_debt.md) — 双语 README/CHANGELOG 至 wave24 + 守卫/安装器 + dev 回填，已 push（dc0e6d8）；残留项在档
 - [README 证据代际 + 可渲染流程图](project_readme_evidence_generations.md) — G1/G2/G3 标注；mermaid→`docs/assets` SVG+mmd；2455×3102→706×1379；DOC 资产放 `docs/` 避免 C18 误报
 - ✅ [外部评审×SOTA 改进方案](project_review_improvement_plan.md) — 2026-10-15 评审（34f4b84）16 项发现核验 + W1-W6 改进设计（docs/PLAN_review_improvement_20261015.md）；P0-P3 路线，实施前先建评审语料回归集
 - ✅ [上下文压缩评估 pi-vcc 对比](project_context_compression_pi_vcc_eval.md) — waves16-24=生存投递（不缩窗）· pi-vcc=提取摘要+recall · 改进选项 A1-A5/B 未实施（报告在档）；1.18.35 能力面（text.complete 可改写摘要·prompt 替换·工具注册·autocontinue）实证
 
 ## External References
 - [GitHub Repo](reference_github_repo.md) — logandoo/vibeweaver remote + local repo path + verify harness
 
 ## W2 Eval (2026-10-23)
-- ⏳ [Eval lab batch 1](project_w2_eval_lab.md) — mock lab · power MDE 0.286 · G3 prereg；live runs not_run；❌ opencode worktree isolation wrote to host repo
+- ⏳ [Eval lab batch 1](project_w2_eval_lab.md) — mock lab · power MDE 0.286 · G3 prereg；live runs not_run；隔离缺陷已关闭（见 fix_eval_isolation_w2iso）；Task 14 现缺 8 场景 + 预算
 
 ## W1 Hardening (2026-10-22)
 - ⏳ [W1 batch 1](project_w1_hardening_batch1.md) — installer lifecycle · contract lint full · core profile 1,169 tokens · perf budget PASS；Task 6/11/7/7.5/10/20/21 待做
 
 ## Fix Tracking
+- ⏳ [Fix: Eval isolation W2-ISO](fix_eval_isolation_w2iso.md) — opencode 会话目录取 `$PWD`（非 cwd）→ 三重绑定 + 临时 HOME + scrubbed state DB 播种 + 越界 fail-closed；8/8 + 真实 smoke pass；❌ `git checkout` 覆盖未提交编辑教训（2026-10-23）
 - ✅ [Fix: W0 trust floor (w18.2)](fix_w0_trust_floor_20261022.md) — release manifest/attestation · checker pin · evidence lock · clean-clone self-check · COV-0 · bootstrap · state redaction；CI 6/6，tag `w18.2`（2026-10-22）
 - ⏳ [Fix: W18 批 2/3 门禁语义收口](fix_w18_batch2_semantics.md) — G3 git 锚定债棘轮 · G4 claim-lint 当前块+claim-ack · G5 非 web seal 绑定+record 工具 · G6 wave-base 严格祖先 · D-W18-6 new-task 归因 · D1 顺序唯一化；复审两轮 PoC：日志锚点致盲/硬顶绕过/自引用死锁（2026-10-21）
 - ⏳ [Fix: W18 门禁噪音三态 + tests/ 豁免 arg-shape + 周期相位](fix_w18_gate_noise_batch1.md) — G1 seal 三态（no-seal WARN · stale/tamper/partial C3 · current 静默 · bootstrap 双硬限 `--final` 恒执行+`PASS\b`）· G2 双插件 args.path 豁免 · G9 rtrim 相位双探针 · E3 断言按 D3 重定（§V2 ADR）；复审抓出半修/off-switch/pin 空转（2026-10-21）
 - ⏳ [Fix: W10 stop-guard / loop-guard false positives](fix_loopguard_false_positives_w10.md) — positive predicate scoped to CODE task-file writes + read-only/awaiting whitelists; 256KB visible-text ceiling (reasoning excluded); tool-frequency opt-in; SOTA basis (2026-10-19)
 - ✅ [Fix: W11 stop-guard blind spots](fix_loopguard_blindspots_w11.md) — turn log slice + assert-bound final-run + part-seq gate ordering + DOC/write cross-check + churn-safe ceiling + success-only v2 write evidence (2026-10-19)
 - ✅ [Fix: W12 leftover closure](fix_w12_leftover_closure.md) — paused/Class-E visible approval, tool-frequency warn-only, verified seal, classifier/build-file edges, mutation variants, repo publish (2026-10-19)
 - ✅ [Fix: W13 v2 prompts + seal cleanup](fix_w13_v2_prompts.md) — v2 explicit euphemism prompts, positive always debt, prompt-failure debt; JS seal verifier removed (2026-10-19)
 - ⏳ [Fix: W9 scan FP + canonical sync](fix_payload_scan_fp_w9.md) — pwd/path/ALPHABET/approval/reference semantics; sync checker + eval pins; two reviewers (2026-10-19)
 - ✅ [Fix: eval answer leak (W4-B1 residual)](fix_eval_answer_leak_w6.md) — env/config skill paths exposed suite/tasks/graded; staged config outside repo + fail-closed + peek signatures + opencode v2 shapes; 89/89, leak probe, A/B report (2026-10-18)
 - ⏳ [Fix: eval isolation W9 + 1M longctx floor](fix_eval_isolation_1m_w9.md) — stale WS quarantine, targeted sandbox, token/compaction telemetry, symlink/overwrite/SPEC_ACK gates, 40-step/4MB fixture; bare 40/40, 769s, 0 compactions; full-arm pending (2026-10-20)
diff --git a/memory/project_w2_eval_lab.md b/memory/project_w2_eval_lab.md
index 7708e62..337ec28 100644
--- a/memory/project_w2_eval_lab.md
+++ b/memory/project_w2_eval_lab.md
@@ -11,22 +11,27 @@ status: partial
 ## Done
 
 - `scripts/eval_run.py`: mock smoke pass; hidden test outside worktree;
   three-valued verdict; `trajectory.json` + `cost.json`.
 - `scripts/eval_report.py`: Wilson 95% CI, pass/fail/indeterminate separate.
 - `scripts/eval_power.py`: MDE n=16 seeds=3 = 0.286 absolute.
 - `docs/EVAL_G3_PREREG.md` + `tests/eval/g3/prereg.sha256` (hash frozen).
 - `tests/eval/g3/summary.json`: `status: not_run` (no fabricated results).
 - `docs/EVAL_VALIDITY.md`, `docs/REPLICATION.md` (`single-operator; no independent replication`).
 
-## ❌ OpenCode isolation finding
+## ✅ OpenCode isolation finding — CLOSED 2026-10-23
 
-`opencode run --standalone` inside a temp worktree **wrote to the host repo
-root** instead of the worktree (observed `hello.txt` at the real repo root).
-The lab therefore refuses to claim `--agent opencode` isolation; only the mock
-smoke is certified. G3 live runs remain `not_run`.
+`opencode run --standalone` inside a temp worktree wrote to the host repo
+root (observed `hello.txt`). Root cause: **opencode binds its session
+directory to the environment's `$PWD`, not to the process cwd**. Fixed in
+`scripts/eval_run.py` (three-way binding + temp HOME + fail-closed
+containment) and proven by `tests/test_eval_isolation.py` 8/8 + a real
+`--agent opencode` smoke (`tests/eval/runs/smoke-20261023_031133/`,
+verdict=pass, zero outside writes). Full write-up:
+`memory/fix_eval_isolation_w2iso.md`.
 
 ## Next
 
-- Fix opencode directory binding (`opencode <directory> run …` or a dedicated
-  server per worktree) before any live eval.
-- Then run Task 14 pilot (8×3×4=96) under a budget cap; then full 192/240.
+- Task 14 pilot (8×3×4=96) needs: 8 scenarios + hidden tests (lab currently
+  has `smoke` only) and a budget cap ($ / hour) — that is the blocker now,
+  NOT isolation.
+- Then full 192/240 runs; then W2 exit sync + release `w19.0`.
diff --git a/scripts/eval_run.py b/scripts/eval_run.py
index df3f44b..09cb27c 100755
--- a/scripts/eval_run.py
+++ b/scripts/eval_run.py
@@ -1,22 +1,37 @@
 #!/usr/bin/env python3
 """eval_run.py — isolated eval lab (W2 Task 12).
 
 Subject agent and evaluator are separate: the hidden test lives OUTSIDE the
 worktree and is injected only at grading time. Verdict is three-valued:
 pass / fail / indeterminate (setup/capture failure is never pass).
+
+W2-ISO isolation contract (docs/PLAN_w2_iso_20261023.md):
+  * the subject agent's session directory is the run's temp worktree — bound
+    three ways: the `opencode run … <directory> <message>` positional, the
+    process cwd, and `PWD` (measured: `opencode run` takes its session
+    directory from the ENVIRONMENT's `$PWD`, not from the process cwd);
+  * the agent runs with the run's temp HOME (auth/models/config seeded there
+    only), and every env value naming the host repo is dropped (W6 lesson:
+    env/config are answer-leak channels too);
+  * after the run, writes outside the worktree/sandbox are DETECTED (host
+    repo `git status` delta + task artifacts outside the worktree) and a
+    violation fails closed as `indeterminate` — a contaminated measurement
+    is never `pass`.
 """
 import argparse
 import json
 import os
 import pathlib
+import re
 import shutil
+import sqlite3
 import subprocess
 import sys
 import tempfile
 import time
 
 ROOT = pathlib.Path(__file__).resolve().parents[1]
 
 
 def lab_root():
     for p in (ROOT / "vibeweaver-eval" / "lab", ROOT / "tests" / "eval" / "lab"):
@@ -26,83 +41,234 @@ def lab_root():
 
 
 def scenario(name):
     p = lab_root() / "scenarios" / (name + ".json")
     if not p.is_file():
         raise SystemExit("eval_run: scenario not found: " + str(p))
     return json.loads(p.read_text(encoding="utf-8"))
 
 
 def seed_auth(home):
-    """Copy only auth material so a temp HOME can still call the model."""
+    """Copy ONLY auth material so a temp HOME can still call the model.
+
+    Measured (2026-10-23): provider/model ROUTING lives in the opencode state
+    DB (`credential` table = per-provider API keys, `kv.models-dev:catalog`),
+    not in auth.json — a fresh DB yields 12 models and zero provider routes.
+    The same DB also holds the host's session/message/part rows (42k+), which
+    are ANSWER MATERIAL: seeding it whole would hand the subject agent the
+    host's conversation history. So the DB copy is scrubbed — schema +
+    auth-shaped tables only, every content-bearing table emptied.
+    """
     src = pathlib.Path.home() / ".local" / "share" / "opencode" / "auth.json"
     if src.is_file():
         dst = home / ".local" / "share" / "opencode"
         dst.mkdir(parents=True, exist_ok=True)
         shutil.copyfile(src, dst / "auth.json")
     # model/provider registry is config, not evidence: seed only the config file
     cache = pathlib.Path.home() / ".cache" / "opencode" / "models.json"
     if cache.is_file():
         cdir = home / ".cache" / "opencode"
         cdir.mkdir(parents=True, exist_ok=True)
         shutil.copyfile(cache, cdir / "models.json")
     cfg = pathlib.Path.home() / ".config" / "opencode" / "opencode.jsonc"
     if cfg.is_file():
         cdir = home / ".config" / "opencode"
         cdir.mkdir(parents=True, exist_ok=True)
         shutil.copyfile(cfg, cdir / "opencode.jsonc")
+    return seed_state_db(home)
 
 
-def run_agent(name, work, home, model):
-    prompt = scenario(name)["prompt"]
-    # Worktree/HOME are isolated; the model registry/config is shared because
-    # a fresh HOME cannot discover providers (documented partial isolation).
-    # Model discovery/credentials live in the host HOME; the worktree and the
-    # hidden-test boundary are still isolated. Full HOME isolation is a
-    # documented gap until a portable model registry is available.
+# content/answer-bearing tables of the opencode state DB — NEVER seeded.
+DB_CONTENT_TABLES = [
+    "message", "part", "session", "session_message", "session_v2", "session_inbox",
+    "session_pending", "session_share", "todo", "instruction_blob", "instruction_entry",
+    "instruction_state", "project", "project_directory", "worktree", "event",
+    "event_sequence", "permission", "workspace",
+]
+
+
+def seed_state_db(home):
+    """Seed a SCRUBBED copy of the host state DB: schema + credential + kv only.
+
+    Returns True when seeded. The scrub is what keeps the model route without
+    the answer material (see seed_auth docstring)."""
+    src = pathlib.Path.home() / ".local" / "share" / "opencode" / "opencode.db"
+    if not src.is_file():
+        return False
+    dst = home / ".local" / "share" / "opencode" / "opencode.db"
+    dst.parent.mkdir(parents=True, exist_ok=True)
+    src_con = sqlite3.connect("file:%s?mode=ro" % src, uri=True)
+    dst_con = sqlite3.connect(str(dst))
+    try:
+        src_con.backup(dst_con)          # safe copy while the host service writes
+        for t in DB_CONTENT_TABLES:
+            dst_con.execute("delete from '%s'" % t)
+        dst_con.execute("delete from kv where key like 'job.%'")
+        dst_con.commit()
+    finally:
+        src_con.close()
+        dst_con.close()
+    return True
+
+
+def build_env(work, home, root):
+    """W2-ISO: bind the subject agent to the worktree + the run's temp HOME.
+
+    Measured: `opencode run` takes its session directory from the
+    ENVIRONMENT's `$PWD`, not from the process cwd (a run with cwd=/tmp/A and
+    PWD=/tmp/B wrote its artifact into /tmp/B). `cwd=` alone is therefore not
+    a binding — `PWD` is set to the worktree, the directory positional is
+    passed on the CLI as well, and every env value naming the host repo is
+    dropped (W6 lesson: env/config are answer-leak channels too).
+    """
     env = dict(os.environ)
-    if args.agent == "mock":
+    for k in list(env):
+        if k.startswith("XDG_") or k == "OLDPWD":
+            del env[k]
+    for k in list(env):
+        if k in ("PATH", "HOME", "PWD", "USER", "LOGNAME", "SHELL", "TERM", "LANG"):
+            continue
+        v = env[k]
+        if isinstance(v, str) and str(root) in v:
+            del env[k]
+    env["HOME"] = str(home)
+    env["PWD"] = str(work)
+    return env
+
+
+def git_status_lines(root):
+    """Isolation leg (a): host-repo tree fingerprint. None = not monitorable
+    (missing != success: an unmonitorable tree is an isolation violation)."""
+    try:
+        r = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
+                           capture_output=True, text=True, timeout=60)
+    except Exception:
+        return None
+    if r.returncode != 0:
+        return None
+    return sorted(l for l in r.stdout.splitlines() if l.strip())
+
+
+def tree_files(base):
+    """Every file under `base`, relative to it, sorted."""
+    return sorted(str(p.relative_to(base)) for p in base.rglob("*") if p.is_file())
+
+
+def containment_check(tmp, work, out, artifacts, hidden_name, before_repo, after_repo):
+    """W2-ISO: detect writes that left the worktree/sandbox and fail closed.
+
+    Two monitored legs (residual named in docs/PLAN_w2_iso_20261023.md): the
+    host repo's `git status` delta (excluding this run's evidence dir) and
+    task artifacts found outside the worktree inside the sandbox. The hidden
+    test appearing in the worktree is a violation too.
+    """
+    out_rel = os.path.relpath(str(out), str(ROOT))
+    work_files = tree_files(work)
+    outside = []
+    for rel in tree_files(tmp):
+        try:
+            (tmp / rel).relative_to(work)
+        except ValueError:
+            outside.append(rel)
+    violations = []
+    monitored = before_repo is not None and after_repo is not None
+    delta = []
+    if monitored:
+        delta = [l for l in after_repo if l not in before_repo and out_rel not in l]
+        violations += ["host-repo write outside sandbox: " + l for l in delta]
+    else:
+        violations.append("host repo not monitorable (git status failed) — isolation unverified")
+    for rel in outside:
+        if pathlib.Path(rel).name in artifacts:
+            violations.append("task artifact outside worktree: " + rel)
+    for rel in work_files:
+        if pathlib.Path(rel).name == hidden_name:
+            violations.append("hidden test inside worktree: " + rel)
+    return {
+        "sandbox": str(tmp),
+        "worktree": str(work),
+        "work_files": work_files,
+        "sandbox_outside_work": outside,
+        "host_repo_delta": delta,
+        "host_repo_monitored": monitored,
+        "artifacts": list(artifacts),
+        "violations": violations,
+    }
+
+
+# CLI error signatures meaning the AGENT NEVER STARTED (harness/environment
+# problem: model route, auth, provider config) — never a subject failure.
+SETUP_FAILURE_RE = re.compile(
+    r"Model unavailable|provider\.no-route|provider\.auth|Model not found|"
+    r"No such model|config\.invalid", re.I)
+
+
+def is_setup_failure(agent):
+    return bool(SETUP_FAILURE_RE.search((agent.get("stderr") or "") + (agent.get("stdout") or "")))
+
+
+def run_agent(name, work, home, model, agent_kind):
+    prompt = scenario(name)["prompt"]
+    # Worktree/HOME are isolated; the model registry/config is seeded into the
+    # temp HOME (auth.json / models.json / opencode.jsonc) because a fresh HOME
+    # cannot discover providers — documented partial isolation.
+    if agent_kind == "mock":
         (work / "hello.txt").write_text("hello\n", encoding="utf-8")
         return {"exit": 0, "stdout": "mock agent", "stderr": "", "cmd": "mock"}
-    cmd = ["opencode", "run", "--standalone", "-m", model, "--format", "default", "--auto", prompt]
+    env = build_env(work, home, ROOT)
+    # `opencode run [flags] <directory> <message...>` — the directory positional
+    # goes BEFORE the variadic message (v2.1.3; `opencode <dir> run` parses wrong).
+    cmd = ["opencode", "run", "--standalone", "-m", model, "--format", "default",
+           "--auto", str(work), prompt]
     t0 = time.time()
-    r = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, timeout=scenario(name)["timeout_seconds"])
-    return {"exit": r.returncode, "stdout": r.stdout[-20000:], "stderr": r.stderr[-20000:], "cmd": " ".join(cmd), "seconds": time.time() - t0}
+    r = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True,
+                       timeout=scenario(name)["timeout_seconds"])
+    return {"exit": r.returncode, "stdout": r.stdout[-20000:], "stderr": r.stderr[-20000:],
+            "cmd": " ".join(cmd), "seconds": time.time() - t0,
+            "cwd": str(work), "home": str(home)}
 
 
 def main(argv=None):
     global args
     ap = argparse.ArgumentParser()
     ap.add_argument("--scenario", default="smoke")
     ap.add_argument("--agent", choices=["opencode", "mock"], default="opencode")
     ap.add_argument("--model", default="deepseek/deepseek-flash")
     ap.add_argument("--out", default="")
     args = ap.parse_args(argv)
     sc = scenario(args.scenario)
+    artifacts = list(sc.get("artifacts") or [])
+    hidden_name = pathlib.Path(sc["hidden_test"]).name
     tmp = pathlib.Path(tempfile.mkdtemp(prefix="vw-eval-"))
     work, home = tmp / "work", tmp / "home"
     work.mkdir(); home.mkdir(); seed_auth(home)
     out = pathlib.Path(args.out) if args.out else ROOT / "tests" / "eval" / "runs" / (sc["id"] + "-" + time.strftime("%Y%m%d_%H%M%S"))
     out.mkdir(parents=True, exist_ok=True)
+    before_repo = git_status_lines(ROOT)
     try:
-        agent = run_agent(args.scenario, work, home, args.model)
+        agent = run_agent(args.scenario, work, home, args.model, args.agent)
     except Exception as e:
         agent = {"exit": -1, "stdout": "", "stderr": str(e), "cmd": "opencode"}
+    iso = containment_check(tmp, work, out, artifacts, hidden_name,
+                            before_repo, git_status_lines(ROOT))
     # hidden test is NOT copied into work; run it from the lab
     if agent["exit"] != 0:
-        verdict = "indeterminate" if agent["exit"] in (-1,) else "fail"
+        verdict = "indeterminate" if (agent["exit"] == -1 or is_setup_failure(agent)) else "fail"
         test = {"exit": None, "output": "agent failed/could not run"}
     else:
         tp = lab_root() / sc["hidden_test"]
         r = subprocess.run([sys.executable, str(tp), str(work)], capture_output=True, text=True, timeout=60)
         test = {"exit": r.returncode, "output": (r.stdout + r.stderr)[-8000:]}
-        verdict = "pass" if r.returncode == 0 else "fail"
+        verdict = "pass" if r.returncode == 0 else ("fail" if r.returncode == 1 else "indeterminate")
+    if iso["violations"]:
+        verdict = "indeterminate"  # fail-closed: a contaminated measurement is never pass
+    (out / "isolation.json").write_text(json.dumps(iso, indent=2), encoding="utf-8")
     (out / "trajectory.json").write_text(json.dumps({"scenario": sc["id"], "agent": agent, "worktree": str(work)}, indent=2), encoding="utf-8")
     (out / "cost.json").write_text(json.dumps({"wall_seconds": agent.get("seconds"), "model": args.model, "tokens": None}, indent=2), encoding="utf-8")
-    (out / "verdict.json").write_text(json.dumps({"scenario": sc["id"], "verdict": verdict, "hidden_test": test, "agent_exit": agent["exit"]}, indent=2), encoding="utf-8")
+    (out / "verdict.json").write_text(json.dumps({"scenario": sc["id"], "verdict": verdict, "hidden_test": test, "agent_exit": agent["exit"], "isolation_violations": iso["violations"]}, indent=2), encoding="utf-8")
     print(f"EVAL {sc['id']}: {verdict} -> {out}")
     shutil.rmtree(tmp, ignore_errors=True)
     return 0 if verdict == "pass" else 1
 
 
 if __name__ == "__main__":
     sys.exit(main())
diff --git a/tests/.evidence.lock b/tests/.evidence.lock
index 17dd0f2..095d873 100644
--- a/tests/.evidence.lock
+++ b/tests/.evidence.lock
@@ -1,16 +1,16 @@
 {
   "acceptance": {
-    "bytes": 1035,
-    "heading": "# Acceptance \u2014 W2 \u7b2c\u4e00\u6279\uff1aeval lab \u00b7 validity/power \u00b7 G3 prereg",
-    "sha256": "dd2a6fd86a11b227971aac8e673d0c377eda48f95e55e3b42468a569559c90f7",
-    "start_line": 78
+    "bytes": 1611,
+    "heading": "# Acceptance \u2014 W2-ISO\uff1aopencode worktree \u9694\u79bb\u4fee\u590d\uff08W2-T12 \u6536\u53e3\uff09",
+    "sha256": "6c735568a78524d1b3b030029dca9922ab27175b2d0d57bb2a34c76126d35b31",
+    "start_line": 87
   },
   "debt": {
     "sha256": "75e6fc99fcf491434d1ab3e5ef0236c315807fd599d0a82fda97404ac28784a3"
   },
   "history": [
     {
       "approved": true,
       "at": "2026-10-23T00:08:08",
       "reason": "start W1 batch 2 criteria section (gate/risk/destructive/security/compat)",
       "sha256": "0a0242a5e040a7b0ca432d4840d8497f49fba04f8ee382488183b28c5c2788ef"
@@ -746,19 +746,19 @@
         "i": 469,
         "prev": "6a87af4f0a4a60b9e280c602b4751194a3670416c304c8a47b8af4eb09bfcbd7",
         "sha256": "f4efd04bd6f71bbdf3014b2ec538d18c8ec150c3373119c8bef5830861c076b8"
       },
       {
         "i": 470,
         "prev": "f4efd04bd6f71bbdf3014b2ec538d18c8ec150c3373119c8bef5830861c076b8",
         "sha256": "07f4fb6538fb39aa38fdca6272f09cb042d91cf8199a95f99e71c5c69c78a345"
       }
     ],
-    "head_lines": 470,
-    "head_sha256": "07f4fb6538fb39aa38fdca6272f09cb042d91cf8199a95f99e71c5c69c78a345",
+    "head_lines": 482,
+    "head_sha256": "06cbfba00a4585138232328e3485584556f8bdc0084c36627ad7096c4e8d2c56",
     "mode": "chain"
   },
   "profile": {
     "sha256": "ebc6b55a6700504b0c9f16e353770bec7630d55d7063ffc3d6fbbbaefc15fe2b"
   },
   "version": 1
 }
diff --git a/tests/acceptance.md b/tests/acceptance.md
index f9c306d..9a20379 100644
--- a/tests/acceptance.md
+++ b/tests/acceptance.md
@@ -77,10 +77,20 @@ Source: `docs/PLAN_comprehensive_hardening_20261022.md` W1（Task 6 / 7 / 7.5 /
 40. (计划 #6) `python3 scripts/check_claims.py` → `0 unbound`；注入 `70/71` 与无 n/seeds/ci 的 `+251%` 均 fail；README/README_zh 与 CHANGELOG 当前条目的 count/effect 宣称全部命中 `release/claims.json`。
 
 # Acceptance — W2 第一批：eval lab · validity/power · G3 prereg
 
 Source: `docs/PLAN_comprehensive_hardening_20261022.md` W2（Task 12 / 12.5 / 13 / 16 statement）。
 
 41. (计划 #? Task 12) `python3 scripts/eval_run.py --scenario smoke --agent opencode` 产出 `verdict.json` + `trajectory.json` + `cost.json`；隔离 HOME/worktree；`indeterminate` 不进入 pass；隐藏测试不在 agent 工作区。
 42. (Task 12.5) `python3 scripts/eval_power.py --n 16 --seeds 3` 打印 MDE；`tests/eval/g3/summary.json` 含 n/seeds/95% CI/paired diff/cost/MDE/κ；contamination/grader-independence/multiplicity/kill-criteria 有文档与测试。
 43. (Task 13) `sha256sum docs/EVAL_G3_PREREG.md` == `tests/eval/g3/prereg.sha256`；prereg 含 contamination、MDE/power 决策规则、单一 primary endpoint、停止规则。
 44. (Task 14/16 状态) `tests/eval/g3/summary.json` 明确 `status: not_run`（或真实 n/seeds/CI），不得伪造；README/`docs/REPLICATION.md` 标注 `single-operator; no independent replication`。
+
+# Acceptance — W2-ISO：opencode worktree 隔离修复（W2-T12 收口）
+
+Source: `docs/UNFINISHED_20261023.md` §3 W2-ISO 完成判据 + §7 步骤 3（先修 W2-ISO，才谈 96/192 runs）。
+
+45. `python3 scripts/eval_run.py --scenario smoke --agent mock` 运行后，任务产物（`hello.txt`）只出现在本次运行的临时 worktree 内；隐藏测试文件不在 worktree 内；verdict 是三值之一，且带污染的运行拿不到 `pass`。
+46. 主体 agent 的会话目录绑定到临时 worktree（不是宿主 repo）：stub 代理与真实 `--agent opencode` 运行都证明 `$PWD`、进程 cwd、CLI 目录位置参数三者指向 worktree。
+47. mock 与 real smoke 运行结束后 worktree/沙箱之外零写入：宿主 repo `git status --porcelain` 前后差分为空（本次证据目录 `tests/eval/runs/` 除外），且临时沙箱内 `work/` 之外没有任务产物；任何违例 → `verdict=indeterminate`（永不 `pass`）。
+48. `python3 scripts/eval_run.py --scenario smoke --agent opencode` 真实跑通并产出 `verdict.json` / `trajectory.json` / `cost.json` / `isolation.json`；verdict 三值正确（`pass`=隐藏测试 exit 0；`fail`=隐藏测试 exit 1 或 agent 非零退出；`indeterminate`=越界/捕获失败/隐藏测试非 0-1 退出）；隐藏测试仅在评分时从 lab 注入。
+49. HOME 隔离生效：被测 agent 以本次运行的临时 HOME 运行（只播种 `auth.json`/`models.json`/`opencode.jsonc` 三项），宿主 `~/.config/opencode` 插件不进入被测会话（stderr 无 `GATE-BLOCKED` 噪音；trajectory 记录 home 路径）。
diff --git a/tests/coverage_matrix.md b/tests/coverage_matrix.md
index 64b6375..871848d 100644
--- a/tests/coverage_matrix.md
+++ b/tests/coverage_matrix.md
@@ -2,10 +2,20 @@
 |---|---|---|---|---|
 | 21 | Manifest verify + tamper detection | `python3 scripts/verify_release.py` (public repo); temp bundle tamper | `tests/w0_release_verify.log`, `tests/w0_task1_bundle_verify.log`, `tests/w0_task1_bundle_tamper.log` | covered |
 | 22 | Checker pin + cache invalidation | `bash tests/gate_trust/run.sh`; `cache_invalidation.sh` | `tests/w0_final_gate.log`, `tests/w0_final_cache.log` | covered |
 | 23 | Clean-clone self-check + COV-0 | `bash tests/self_check.sh` (public repo); `contract_lint.py` | `tests/w0_repo_selfcheck.log`, `tests/w0_final_selfcheck2.log`, `tests/w0_final_unit.log` | covered |
 | 24 | Contract lint 0 conflicts | `python3 scripts/contract_lint.py` | `tests/w0_final_selfcheck.log` | covered |
 | 25 | Evidence integrity + new-task guards | `bash tests/gate_trust/evidence_integrity/run.sh` | `tests/w0_final_evi2.log` (6/6 + 3/3) | covered |
 | 26 | State redaction/bounds/retention | `python3 scripts/state_sanitize.py --check`; `node tests/state_bounds_test.mjs` (incl. reasoning parts) | `tests/w0_state_reasoning.log`, `tests/w0_task15_state_check.log`, `tests/w0_task15_scan.log` | covered |
 | 27 | Bootstrap v1/v2/no-hook (+ object system part) | `node tests/bootstrap_test.mjs` | `tests/w0_final_bootstrap2.log` (8/8) | covered |
 | 28 | Release + attestation + CI 6/6 | `gh release view w18.2.4`; `gh attestation verify`; CI run | `tests/w0_release_attest.log`, verify run 39783700555 | covered |
 | 27b | Eval subset loaded ≥8/16 | model eval harness | not run (no model API in this session) | unchecked |
+
+## W2-ISO（2026-10-23）— criteria #45-#49
+
+| # | Criterion | Check (test/command) | Evidence file | Status |
+|---|---|---|---|---|
+| 45 | mock 产物只在 worktree；隐藏测试在工作区外；污染运行不拿 pass | `python3 -m unittest tests.test_eval_isolation`（test_mock_agent_isolated_hidden_test_outside · test_contamination_fails_closed） | tests/w2iso_green2.log（8/8） | covered |
+| 46 | `$PWD` / 进程 cwd / CLI 目录位置参数 三者绑定 worktree | 同上（test_agent_binds_to_worktree_despite_stale_pwd · test_home_isolation_and_directory_arg）+ 真实 smoke trajectory | tests/w2iso_green2.log · tests/eval/runs/smoke-20261023_031133/trajectory.json | covered |
+| 47 | worktree/沙箱外零写入 + 违例 fail-closed（verdict=indeterminate） | 同上（test_host_repo_delta_detects_out_of_sandbox_write · test_contamination_fails_closed）+ 真实 smoke isolation.json + shell 级 `git status` 差分双路核对 | tests/w2iso_real_smoke2.log · tests/eval/runs/smoke-20261023_031133/isolation.json | covered |
+| 48 | 真实 `--agent opencode` smoke 产出 4 json；verdict 三值正确；隐藏测试仅评分时注入 | `python3 scripts/eval_run.py --scenario smoke --agent opencode`；test_verdict_three_valued · test_setup_failure_is_indeterminate | tests/w2iso_real_smoke2.log · tests/w2iso_regression2.log | covered |
+| 49 | HOME 隔离：宿主插件不进被测会话；播种面只含 auth 形状数据（无宿主会话内容）（判据括注按 ADR D-W2ISO-1 修订：3 项 → 4 项含 scrubbed DB） | test_seed_state_db_scrubs_content_tables + 真实 smoke stderr 无 `GATE-BLOCKED`、`trajectory.home`=沙箱 home | tests/w2iso_green2.log · tests/eval/runs/smoke-20261023_031133/trajectory.json | covered |
diff --git a/tests/decisions.md b/tests/decisions.md
index a08fcb2..3dfa55d 100644
--- a/tests/decisions.md
+++ b/tests/decisions.md
@@ -346,10 +346,12 @@ D-001 | trigger: 计划 §0.2 定位决策 | options: (a) framework/standard (b)
 D-002 | trigger: 计划 §0.2 宿主支持面 | options: (a) 多宿主同语义 (b) opencode 一级 + 其他 adapter | chosen: (b) | why: 只有 opencode v1/v2 有实机验证；其他宿主语义差异必须显式标注，不混称 gate | revisit-if: 第二个宿主通过同一套 bootstrap/gate 测试
 D-003 | trigger: 计划 §0.2 fail-open 语义 | options: (a) 禁止 fail-open (b) fail-open 但必须输出 UNVERIFIED 且不算完成 | chosen: (b) | why: 宿主缺 hook 时硬失败会让技能不可用；UNVERIFIED 的诚实降级保留可用性又不制造假绿 | revisit-if: 宿主提供稳定 hook 后收紧为 fail-closed
 D-004 | trigger: 计划 §0.2 仪式产物位置 | options: (a) 所有 gate line 只进 tests/ (b) 最终回答允许一行摘要，profile 决定 | chosen: (b) | why: 用户需要可读结果；profile 控制是否附 gate line，避免双份契约 | revisit-if: 统一 profile 字段落地后冲突
 D-005 | trigger: 计划 §0.2 公开 repo 定位 | options: (a) chatbot 参考实现 (b) contract + reference runtime，chatbot 是 host | chosen: (b) | why: 公开树承载契约与可验证运行时；chatbot 只是消费者，不能反向定义契约 | revisit-if: 公开 repo 转为产品分发
 D-W0-1 | trigger: 用户选择完整 W0（Task 1→2→2.5→3→4→1.5→5） | options: (a) 最小包 (b) 完整 W0 | chosen: (b) | why: 用户在开工问答中明确选择完整 W0，包含正式 w18.2 发布；该选择同时构成 Task 5 的 Class-E 预授权 | revisit-if: 用户撤回发布授权
 D-W0-2 | trigger: 计划 §0.3 与 §0.4 的任务集不一致（§0.3 含 2.5，§0.4 不含） | options: (a) 按 §0.4 跳过 2.5 (b) 按 §0.3/依赖顺序执行 2 → 2.5 → 1.5 → 3 | chosen: (b) | why: 2.5 与 2 共用 protected-evidence 机制，拆开会让 checker pin 可被改 acceptance 绕过；用户选择完整 W0 也覆盖 2.5 | revisit-if: 时间预算不足时先发布 rc1
 D-W0-3 | trigger: COV-3 研究源不可用（exa MCP 402 credits exhausted） | options: (a) 停等 (b) 采用计划内 2026-10-22 研究结论 + 现有代码契约 | chosen: (b) | why: 计划已含 SLSA/TUF/OpenSSF/Anthropic/Superpowers 检索结论；实现栈无开放选型，跳过不改变任何设计 | revisit-if: 出现需要外部 API 的新选型
 
 D-W0-4 | trigger: release workflow 失败（contents:read 403；sha256 路径；Windows 测试）后需要重发 w18.2 | options: (a) 保留红 tag、另发 w18.2.1 (b) 在无消费者下载前删除 release 并重切 tag (c) 放弃发布 | chosen: (b) | why: 首次 release 无资产下载（downloadCount=0）且 workflow 失败，未构成已消费发布；保留红 tag 会让“可验证发布”名不副实。最终 tag 指向 7ccc5e9，verify 6/6 + release success；一旦有下载即按 (a) 处理 | revisit-if: 出现任何外部下载/引用，禁止再移动 w18.2
 D-W0-5 | trigger: Windows 矩阵上 POSIX shell trust fixtures 因 Git-Bash 路径映射失败 | options: (a) 为 Windows 重写五套 shell 夹具 (b) P0 跳过该步骤、保留 Python/Node 单测 (c) 删除 Windows 腿 | chosen: (b) | why: P0 验收只要求本地/仓库证据；跨平台同等语义属 P1 Task 21 兼容矩阵。步骤加 `if: runner.os != 'Windows'` 并在 memory 标注 adapter 缺口，不伪造绿 | revisit-if: Task 21 开工时用 Python 重写夹具
+D-W2ISO-1 | trigger: acceptance #49 的「只播种 auth.json/models.json/opencode.jsonc 三项」被证据推翻（仅三项时 provider 路由为空，`Model unavailable: deepseek/deepseek-flash`） | options: (a) 改用 config-declared 模型跑 smoke，保持三项播种 (b) 增播 scrubbed state DB（schema+credential+kv） (c) 整库播种 opencode.db | chosen: (b) | why: (c) 把 42,773 条宿主 session_message/2,573 part/604 message（答案面）交给被测 agent，属 W6 同类泄露；(a) 让 lab 只能用 LAN 端点且 #48 指名的默认命令跑不通；(b) 只播 auth 形状数据（credential=provider API key，与已播 auth.json 同敏感度、无新增暴露），清空 18 张内容表后实测 443 模型路由恢复（tests/w2iso_seed_bisect 证据链） | revisit-if: opencode 改变 provider 存储位置，或 credential/kv 表出现非 auth 数据
+D-W2ISO-2 | trigger: COV-3 研究源不可用（exa MCP 402 credits exhausted，本会话第二次） | options: (a) 停等 (b) websearch + 本机 CLI 实测（help/探针）作为证据源 | chosen: (b) | why: 目录绑定语义以实测为准（诱饵探针 probe_a/probe_c），文档只作旁证；等待配额不改变任何已测事实 | revisit-if: exa 配额恢复后补检索
diff --git a/tests/eval/lab/scenarios/smoke.json b/tests/eval/lab/scenarios/smoke.json
index 3d96cce..bc3f27f 100644
--- a/tests/eval/lab/scenarios/smoke.json
+++ b/tests/eval/lab/scenarios/smoke.json
@@ -1,6 +1,7 @@
 {
   "id": "smoke",
   "prompt": "Create a file named hello.txt in the current directory containing exactly the word hello and a newline. Do not modify anything else.",
   "hidden_test": "hidden/smoke_test.py",
+  "artifacts": ["hello.txt"],
   "timeout_seconds": 180
 }
diff --git a/tests/eval/runs/smoke-20261023_025238/cost.json b/tests/eval/runs/smoke-20261023_025238/cost.json
new file mode 100644
index 0000000..02fb63e
--- /dev/null
+++ b/tests/eval/runs/smoke-20261023_025238/cost.json
@@ -0,0 +1,5 @@
+{
+  "wall_seconds": 1.3343255519866943,
+  "model": "deepseek/deepseek-flash",
+  "tokens": null
+}
\ No newline at end of file
diff --git a/tests/eval/runs/smoke-20261023_025238/isolation.json b/tests/eval/runs/smoke-20261023_025238/isolation.json
new file mode 100644
index 0000000..b0baa20
--- /dev/null
+++ b/tests/eval/runs/smoke-20261023_025238/isolation.json
@@ -0,0 +1,20 @@
+{
+  "sandbox": "/var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/vw-eval-wqgjujpo",
+  "worktree": "/var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/vw-eval-wqgjujpo/work",
+  "work_files": [],
+  "sandbox_outside_work": [
+    "home/.cache/opencode/models.json",
+    "home/.config/opencode/opencode.jsonc",
+    "home/.local/share/opencode/auth.json",
+    "home/.local/share/opencode/log/opencode.log",
+    "home/.local/share/opencode/opencode.db",
+    "home/.local/share/opencode/opencode.db-shm",
+    "home/.local/share/opencode/opencode.db-wal"
+  ],
+  "host_repo_delta": [],
+  "host_repo_monitored": true,
+  "artifacts": [
+    "hello.txt"
+  ],
+  "violations": []
+}
\ No newline at end of file
diff --git a/tests/eval/runs/smoke-20261023_025238/trajectory.json b/tests/eval/runs/smoke-20261023_025238/trajectory.json
new file mode 100644
index 0000000..03a69d0
--- /dev/null
+++ b/tests/eval/runs/smoke-20261023_025238/trajectory.json
@@ -0,0 +1,13 @@
+{
+  "scenario": "smoke",
+  "agent": {
+    "exit": 1,
+    "stdout": "",
+    "stderr": "\u001b[91m\u001b[1mError: \u001b[0mModel unavailable: deepseek/deepseek-flash\n",
+    "cmd": "opencode run --standalone -m deepseek/deepseek-flash --format default --auto /var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/vw-eval-wqgjujpo/work Create a file named hello.txt in the current directory containing exactly the word hello and a newline. Do not modify anything else.",
+    "seconds": 1.3343255519866943,
+    "cwd": "/var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/vw-eval-wqgjujpo/work",
+    "home": "/var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/vw-eval-wqgjujpo/home"
+  },
+  "worktree": "/var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/vw-eval-wqgjujpo/work"
+}
\ No newline at end of file
diff --git a/tests/eval/runs/smoke-20261023_025238/verdict.json b/tests/eval/runs/smoke-20261023_025238/verdict.json
new file mode 100644
index 0000000..d2b8754
--- /dev/null
+++ b/tests/eval/runs/smoke-20261023_025238/verdict.json
@@ -0,0 +1,10 @@
+{
+  "scenario": "smoke",
+  "verdict": "fail",
+  "hidden_test": {
+    "exit": null,
+    "output": "agent failed/could not run"
+  },
+  "agent_exit": 1,
+  "isolation_violations": []
+}
\ No newline at end of file
diff --git a/tests/eval/runs/smoke-20261023_031133/cost.json b/tests/eval/runs/smoke-20261023_031133/cost.json
new file mode 100644
index 0000000..669d743
--- /dev/null
+++ b/tests/eval/runs/smoke-20261023_031133/cost.json
@@ -0,0 +1,5 @@
+{
+  "wall_seconds": 3.1535348892211914,
+  "model": "deepseek/deepseek-flash",
+  "tokens": null
+}
\ No newline at end of file
diff --git a/tests/eval/runs/smoke-20261023_031133/isolation.json b/tests/eval/runs/smoke-20261023_031133/isolation.json
new file mode 100644
index 0000000..2d93eea
--- /dev/null
+++ b/tests/eval/runs/smoke-20261023_031133/isolation.json
@@ -0,0 +1,23 @@
+{
+  "sandbox": "/var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/vw-eval-atnuc4s9",
+  "worktree": "/var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/vw-eval-atnuc4s9/work",
+  "work_files": [
+    "hello.txt"
+  ],
+  "sandbox_outside_work": [
+    "home/.cache/opencode/models.json",
+    "home/.config/opencode/opencode.jsonc",
+    "home/.local/share/opencode/auth.json",
+    "home/.local/share/opencode/log/opencode.log",
+    "home/.local/share/opencode/opencode.db",
+    "home/.local/share/opencode/opencode.db-shm",
+    "home/.local/share/opencode/opencode.db-wal",
+    "home/.local/share/opencode/shell/044d08e3e54dac8105be25227e391026c5312b66/sh_16506a0ee001th9sNamkNu8P1v.out"
+  ],
+  "host_repo_delta": [],
+  "host_repo_monitored": true,
+  "artifacts": [
+    "hello.txt"
+  ],
+  "violations": []
+}
\ No newline at end of file
diff --git a/tests/eval/runs/smoke-20261023_031133/trajectory.json b/tests/eval/runs/smoke-20261023_031133/trajectory.json
new file mode 100644
index 0000000..9e9de52
--- /dev/null
+++ b/tests/eval/runs/smoke-20261023_031133/trajectory.json
@@ -0,0 +1,13 @@
+{
+  "scenario": "smoke",
+  "agent": {
+    "exit": 0,
+    "stdout": "Created `hello.txt` in the working directory with the exact contents `hello\\n` (6 bytes, verified with `od`). Nothing else was modified.\n",
+    "stderr": "\u001b[0m\n> build \u00b7 deepseek-flash\n\u001b[0m\u2190 \u001b[0mWrite hello.txt\nCreated file successfully: hello.txt\n> build \u00b7 deepseek-flash\n\u001b[0m$ \u001b[0mod -c hello.txt\n0000000    h   e   l   l   o  \\n                                        \n0000006\n> build \u00b7 deepseek-flash\n",
+    "cmd": "opencode run --standalone -m deepseek/deepseek-flash --format default --auto /var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/vw-eval-atnuc4s9/work Create a file named hello.txt in the current directory containing exactly the word hello and a newline. Do not modify anything else.",
+    "seconds": 3.1535348892211914,
+    "cwd": "/var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/vw-eval-atnuc4s9/work",
+    "home": "/var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/vw-eval-atnuc4s9/home"
+  },
+  "worktree": "/var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/vw-eval-atnuc4s9/work"
+}
\ No newline at end of file
diff --git a/tests/eval/runs/smoke-20261023_031133/verdict.json b/tests/eval/runs/smoke-20261023_031133/verdict.json
new file mode 100644
index 0000000..9ffdeed
--- /dev/null
+++ b/tests/eval/runs/smoke-20261023_031133/verdict.json
@@ -0,0 +1,10 @@
+{
+  "scenario": "smoke",
+  "verdict": "pass",
+  "hidden_test": {
+    "exit": 0,
+    "output": "PASS: hello.txt\n"
+  },
+  "agent_exit": 0,
+  "isolation_violations": []
+}
\ No newline at end of file
diff --git a/tests/gate_result.json b/tests/gate_result.json
index f1d8137..e1b323f 100644
--- a/tests/gate_result.json
+++ b/tests/gate_result.json
@@ -1 +1 @@
-{"flags":"(failed)","class":"","at":"2026-10-22T18:36:37.173Z"}
\ No newline at end of file
+{"flags":"(failed)","class":"","at":"2026-10-22T19:14:30.697Z"}
\ No newline at end of file
diff --git a/tests/perf/perf_20261023_023827.log b/tests/perf/perf_20261023_023827.log
new file mode 100644
index 0000000..d726b4d
--- /dev/null
+++ b/tests/perf/perf_20261023_023827.log
@@ -0,0 +1,7 @@
+scan_1k    p95=0.024s cap=2.0s OK
+assert     p95=0.529s cap=10.0s OK
+install    p95=0.193s cap=8.0s OK
+core  tokens=  1169 cap=  4000 OK
+full  tokens= 84727 cap= 90000 OK
+mini  tokens=     0 cap=  2000 MISSING
+TOKEN-BUDGET OK
diff --git a/tests/test_eval_isolation.py b/tests/test_eval_isolation.py
new file mode 100644
index 0000000..5e67c2c
--- /dev/null
+++ b/tests/test_eval_isolation.py
@@ -0,0 +1,183 @@
+#!/usr/bin/env python3
+"""tests/test_eval_isolation.py — W2-ISO: eval_run 的 worktree 隔离（确定性回放）。
+
+实测结论（docs/PLAN_w2_iso_20261023.md Consistency Hub）：真实 `opencode run`
+的会话目录取自**环境变量 `$PWD`**，而不是进程 cwd。下面的 stub `opencode` 复刻这条
+绑定规则，于是隔离契约可以在**不调用模型**的情况下确定性验证：
+
+  * $PWD / 进程 cwd / CLI 目录位置参数必须都指向本次运行的临时 worktree（#46）；
+  * worktree/沙箱之外零写入，任何违例必须 fail-closed 成 `indeterminate`（#45/#47）；
+  * 隐藏测试在工作区外，只在评分时注入（#45/#48）；
+  * 被测 agent 用本次运行的临时 HOME（#49）。
+
+Seam：CLI（`python3 scripts/eval_run.py …`）+ PATH 前置的 stub `opencode`；
+腿①（宿主 repo 差分）另加一次对 `eval_run.git_status_lines` 的直接调用。
+"""
+import json
+import os
+import pathlib
+import re
+import shutil
+import sqlite3
+import subprocess
+import sys
+import tempfile
+import unittest
+import uuid
+
+ROOT = pathlib.Path(__file__).resolve().parents[1]
+EVAL_RUN = ROOT / "scripts" / "eval_run.py"
+sys.path.insert(0, str(ROOT / "scripts"))
+
+import eval_run  # noqa: E402  (the module under test)
+
+# stub `opencode`：复刻实测的绑定规则 —— 会话目录 = $PWD（不是 cwd）。
+STUB = """#!/usr/bin/env python3
+import os, pathlib, sys
+
+mode = os.environ.get("VW_STUB_MODE", "good")
+pwd = os.environ.get("PWD") or os.getcwd()
+target = pathlib.Path(pwd)
+print("VW-STUB cwd=%s pwd=%s home=%s argv=%s" % (
+    os.getcwd(), pwd, os.environ.get("HOME", ""), " ".join(sys.argv[1:])))
+if mode == "crash":
+    sys.exit(3)
+if mode == "nomodel":
+    sys.stderr.write("Error: Model unavailable: stub/stub-model\\n")
+    sys.exit(1)
+(target / "hello.txt").write_text("hi\\n" if mode == "wrong" else "hello\\n", encoding="utf-8")
+if mode == "contaminate":
+    pathlib.Path(os.environ["HOME"], "hello.txt").write_text("hello\\n", encoding="utf-8")
+"""
+
+
+class EvalIsolationTest(unittest.TestCase):
+    def setUp(self):
+        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="vw-iso-test-"))
+        self.bin = self.tmp / "bin"
+        self.bin.mkdir()
+        stub = self.bin / "opencode"
+        stub.write_text(STUB, encoding="utf-8")
+        stub.chmod(0o755)
+        self.decoy = self.tmp / "decoy"
+        self.decoy.mkdir()
+        self.out = ROOT / "tests" / "eval" / "runs" / ("iso-test-" + uuid.uuid4().hex[:8])
+        self.addCleanup(shutil.rmtree, self.tmp, True)
+        self.addCleanup(shutil.rmtree, self.out, True)
+
+    def run_eval(self, agent="opencode", mode=None, stale_pwd=None):
+        env = dict(os.environ)
+        env["PATH"] = str(self.bin) + os.pathsep + env.get("PATH", "")
+        if mode:
+            env["VW_STUB_MODE"] = mode
+        # hermetic: never inherit the caller's $PWD — it is usually a real repo
+        # root, and the stub replicates the measured opencode rule ($PWD wins),
+        # so an inherited PWD reproduces the incident against the host tree.
+        env["PWD"] = str(stale_pwd or self.decoy)
+        r = subprocess.run(
+            [sys.executable, str(EVAL_RUN), "--scenario", "smoke", "--agent", agent,
+             "--model", "stub-model", "--out", str(self.out)],
+            capture_output=True, text=True, env=env, timeout=300)
+        return r
+
+    def load(self, name):
+        return json.loads((self.out / name).read_text(encoding="utf-8"))
+
+    # -- #46 绑定：stale $PWD 不得劫持会话目录 ---------------------------------
+    def test_agent_binds_to_worktree_despite_stale_pwd(self):
+        r = self.run_eval(stale_pwd=self.decoy)
+        self.assertEqual(self.load("verdict.json")["verdict"], "pass", r.stdout + r.stderr)
+        iso = self.load("isolation.json")
+        self.assertIn("hello.txt", iso["work_files"])
+        self.assertNotIn("hello.txt", [p.split("/")[-1] for p in iso["sandbox_outside_work"]])
+        self.assertEqual(iso["violations"], [])
+        self.assertEqual(list(self.decoy.iterdir()), [], "stale $PWD 目录被写入 = 事故复现")
+        receipt = self.load("trajectory.json")["agent"]["stdout"]
+        work = self.load("trajectory.json")["worktree"]
+        m = re.search(r"VW-STUB cwd=(\S+) pwd=(\S+) home=(\S+) argv=", receipt)
+        self.assertIsNotNone(m, receipt)
+        # realpath 比较：macOS 上 /var -> /private/var 是同一目录的两种拼写
+        self.assertEqual(os.path.realpath(m.group(2)), os.path.realpath(work))
+        self.assertEqual(os.path.realpath(m.group(1)), os.path.realpath(work))
+
+    # -- #49 HOME 隔离 + #46 目录位置参数 -------------------------------------
+    def test_home_isolation_and_directory_arg(self):
+        r = self.run_eval()
+        self.assertEqual(self.load("verdict.json")["verdict"], "pass", r.stdout + r.stderr)
+        traj = self.load("trajectory.json")
+        receipt = traj["agent"]["stdout"]
+        home = self.load("isolation.json")["sandbox"] + "/home"
+        m = re.search(r"VW-STUB cwd=\S+ pwd=\S+ home=(\S+) argv=", receipt)
+        self.assertIsNotNone(m, receipt)
+        self.assertEqual(os.path.realpath(m.group(1)), os.path.realpath(home))
+        self.assertNotEqual(os.path.realpath(home), os.path.realpath(str(pathlib.Path.home())))
+        self.assertIn(traj["worktree"] + " Create a file named hello.txt", receipt)
+        self.assertTrue(traj["agent"]["cmd"].endswith("/work Create a file named hello.txt "
+                                                      "in the current directory containing "
+                                                      "exactly the word hello and a newline. "
+                                                      "Do not modify anything else."))
+
+    # -- #45/#47 fail-closed：越界 → indeterminate，永不 pass ------------------
+    def test_contamination_fails_closed(self):
+        r = self.run_eval(mode="contaminate")
+        iso = self.load("isolation.json")
+        self.assertEqual(self.load("verdict.json")["verdict"], "indeterminate", r.stdout + r.stderr)
+        self.assertTrue(any(p.endswith("home/hello.txt") for p in iso["sandbox_outside_work"]), iso)
+        self.assertTrue(iso["violations"], "越界必须被记为 violation")
+
+    # -- #45/#48 mock 路径 + 隐藏测试在工作区外 -------------------------------
+    def test_mock_agent_isolated_hidden_test_outside(self):
+        r = self.run_eval(agent="mock")
+        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
+        self.assertEqual(self.load("verdict.json")["verdict"], "pass")
+        iso = self.load("isolation.json")
+        self.assertEqual(iso["work_files"], ["hello.txt"])
+        self.assertNotIn("smoke_test.py", iso["work_files"])
+        self.assertEqual(iso["violations"], [])
+
+    # -- #47 腿①：宿主 repo 差分必须抓到沙箱外写入 ----------------------------
+    def test_host_repo_delta_detects_out_of_sandbox_write(self):
+        before = eval_run.git_status_lines(ROOT)
+        probe = ROOT / "vw_iso_stray_probe.txt"
+        self.addCleanup(lambda: probe.unlink(missing_ok=True))
+        probe.write_text("stray\n", encoding="utf-8")
+        after = eval_run.git_status_lines(ROOT)
+        delta = [l for l in after if l not in before]
+        self.assertTrue(any("vw_iso_stray_probe.txt" in l for l in delta), delta)
+
+    # -- #48 三值正确 ---------------------------------------------------------
+    def test_verdict_three_valued(self):
+        self.run_eval(mode="wrong")
+        self.assertEqual(self.load("verdict.json")["verdict"], "fail")
+        self.run_eval(mode="crash")
+        d = self.load("verdict.json")
+        self.assertEqual(d["verdict"], "fail")
+        self.assertNotEqual(d["agent_exit"], 0)
+
+    # -- #48 三值：agent 根本没启动（模型路由/认证失败）= indeterminate --------
+    def test_setup_failure_is_indeterminate(self):
+        self.run_eval(mode="nomodel")
+        d = self.load("verdict.json")
+        self.assertEqual(d["verdict"], "indeterminate", d)
+        self.assertEqual(d["agent_exit"], 1)
+
+    # -- #49 播种面：state DB 只带 auth 形状数据，绝不带宿主会话内容 ----------
+    def test_seed_state_db_scrubs_content_tables(self):
+        home = self.tmp / "seedhome"
+        home.mkdir()
+        self.assertTrue(eval_run.seed_auth(home))
+        db = home / ".local" / "share" / "opencode" / "opencode.db"
+        self.assertTrue(db.is_file())
+        con = sqlite3.connect(str(db))
+        self.addCleanup(con.close)
+        for t in eval_run.DB_CONTENT_TABLES:
+            n = con.execute("select count(*) from '%s'" % t).fetchone()[0]
+            self.assertEqual(n, 0, "content table %s must be empty in the seed" % t)
+        self.assertGreater(con.execute("select count(*) from credential").fetchone()[0], 0,
+                           "credential rows are the model route and must survive the scrub")
+        self.assertGreater(con.execute("select count(*) from kv").fetchone()[0], 0,
+                           "kv.models-dev:catalog is part of the model route")
+
+
+if __name__ == "__main__":
+    unittest.main()
diff --git a/tests/verification_log.md b/tests/verification_log.md
index 70ad539..5c0719c 100644
--- a/tests/verification_log.md
+++ b/tests/verification_log.md
@@ -461,10 +461,34 @@
 - oracle: project-tests
 - working-note: created — tests/working_note.md
 - scope: Task 12/12.5/13；Task 14 runs budget-blocked → not_run；Task 15/16 later
 - test-change: tests/test_eval_validity.py — Task 12/12.5/13 四例（MDE/hash/not_run/mock smoke+report）
 - test-change: tests/eval/lab/hidden/smoke_test.py — hidden smoke test（worktree 外）
 - iter 1 PASS: criteria #42 #43 #44 | evidence: tests/w2_unit.log 4/4；`eval_power --n 16 --seeds 3` MDE 0.286；prereg hash freeze；summary status=not_run | 覆盖 3/3
 - iter 1 PARTIAL: criterion #41 | diagnosis: `opencode run --standalone` in a temp worktree wrote `hello.txt` to the host repo root instead of the worktree; mock lab passes but live isolation is unsafe, so `--agent opencode` is UNCHECKED | changed: none (blocked direction)
 - working-note: distilled into memory/project_w2_eval_lab.md -> deleted
 - assert-run: assert_artifacts.py --existing --final: all 31 checks pass (exit 0) — tests/w2_assert.log
 - final-run: --final — pass=31/fail=0
+
+## Task: W2-ISO — opencode worktree 隔离修复（2026-10-23）
+
+- class: CODE — basis: scripts/eval_run.py 运行器逻辑（绑定/清洗/越界判定）+ tests/test_eval_isolation.py 行为断言
+- wave-base: accfbd1
+- Mode: AUTO | Lane: L | Class: CODE | Verifier: model-native [image]（mm_probe 行为探针 PASS）；non-web 任务证据 = CLI 转录 + 日志 + JSON 工件
+- probe: model-native PASS (tests/probe_vision.png) — token 10/10 exact + color purple；转录 tests/w2iso_probe.log
+- plan: docs/PLAN_w2_iso_20261023.md（C3 + Consistency Hub）
+git add -u && git add tests/probe_vision.png tests/probe_vision.expected && git commit -m "chore: carry-over W2 eval lab work"
+git add -u && git commit --allow-empty -m "backup: before changes"
+bash script/linux/project_build.sh (or test runner) — run-once baseline
+- Baseline verified GREEN — proceed（@accfbd1：project_build 75/75；python3 -m unittest discover 54/54 → tests/w2iso_baseline.log）
+- oracle: self-tests (weak) + executable acceptance（隐藏测试即外部验收：smoke_test.py 由 harness 在评分时注入）
+- test-change: tests/test_eval_isolation.py — 新增隔离套件（纯新增，6 用例；未改任何既有断言）
+- cleanup: 宿主 repo 根的污染 `hello.txt`（RED 测试 stub 写入，od -c 取证 = `hi\n` 3 字节）已 `mv` 至 $TMPDIR/opencode/vw-iso-stray-hello.txt 移出项目树（未用 rm，无破坏性删除，证据保留）
+- iter 2 PASS: criterion #45 #46 #47 #49 | diagnosis: 三重绑定（`opencode run … <directory> <msg>` 位置参数 + `PWD=work` + `cwd=work`）并把 `HOME` 换成播种过的临时 home、清掉 `XDG_*`/`OLDPWD`/含宿主 repo 路径的变量后，stale-`$PWD` 不再劫持会话目录，且越界会被 `containment_check` 判为 indeterminate | changed: scripts/eval_run.py（build_env/git_status_lines/tree_files/containment_check/run_agent/main）| 证据 tests/w2iso_green.log 6/6 · tests/w2iso_full_suite.log 60/60
+- test-change: tests/test_eval_isolation.py — 断言改为 realpath 语义比较（macOS `/var`→`/private/var` 同一目录两种拼写；语义不变、更严），并让 run_eval 默认注入 decoy `$PWD`（hermetic：绝不继承调用方 PWD，否则 stub 会把事故复现到宿主树）
+- regression-cycle: tests/w2iso_regression.log — revert(`git checkout b6afd5a -- scripts/eval_run.py`) → step2_exit=1 FAILED(failures=2, errors=3) → restore → step4_exit=0 OK（该回归测试确证能抓住缺陷）
+- iter 3 FAIL: criterion #48 | diagnosis: 真实 smoke 在隔离 HOME 下 `Model unavailable: deepseek/deepseek-flash`（provider.no-route），说明 provider 路由不在 auth.json，而 `run_agent` 未播的那一份是必需品；setup 失败被记成 subject fail 也属误判 | changed: none（先定位）| 证据 tests/w2iso_real_smoke.log（verdict=fail，isolation 违例为 0：越界已阻断，问题在模型路由）
+- iter 4 PASS: criterion #45 #46 #47 #48 #49 | diagnosis: provider/模型路由由 state DB 的 `credential` 表（8 个 provider API key）+ `kv.models-dev:catalog` 提供（二分：auth/account/storage/mcp-auth/权限位/cache-bin/node_modules 均无效；整库=443 模型，清空 18 张内容表后仍=443，再去 credential 或 kv 则掉到 12/14），故 `seed_auth` 增播 **scrubbed** DB（schema+credential+kv，`job.%` 键剔除）；并把 agent 未启动（`Model unavailable|provider.no-route|…`）归为 indeterminate | changed: scripts/eval_run.py（seed_state_db/DB_CONTENT_TABLES/is_setup_failure）, tests/test_eval_isolation.py（+2 用例）| 证据 tests/w2iso_green2.log 8/8 · tests/w2iso_regression2.log（revert 仅 2 条新用例 FAIL → restore 8/8）· tests/w2iso_real_smoke2.log + tests/eval/runs/smoke-20261023_031133/（verdict=pass · hidden `PASS: hello.txt` · work_files=['hello.txt'] · host_repo_delta=[] · violations=[] · stderr 无 GATE-BLOCKED → 宿主插件未进入被测会话）
+- test-change: tests/test_eval_isolation.py — 新增 test_seed_state_db_scrubs_content_tables / test_setup_failure_is_indeterminate（纯新增覆盖，未删改既有断言）；这两条是 test-after（由真实 smoke 证据驱动），故用 revert-and-fail 三步补齐证明力（tests/w2iso_regression2.log）
+- ❌ memory: `git checkout <sha> -- <file>` 会覆盖**未提交**编辑——回归三步必须先把工作版快照到盘外，再用快照恢复（本次因此重做了 4 处编辑；已记 memory）
+- working-note: created — tests/working_note.md
+- iter 1 FAIL (RED): criterion #45 #46 #47 #48 #49 | diagnosis: `subprocess.run(cwd=work)` 只改进程 cwd，而 opencode 的会话目录取环境变量 `$PWD`（继承自宿主 repo），且 `run_agent` 从未把播种好的 `home` 写进 env —— 于是被测 agent 落在宿主 repo 根目录，且没有任何越界检测可以把该次运行判为 indeterminate | changed: tests/test_eval_isolation.py, tests/eval/lab/scenarios/smoke.json（artifacts 声明）| 证据 tests/w2iso_red.log（5 FAIL/ERROR：stale-$PWD 用例 verdict 'fail'!='pass'；isolation.json 缺失；git_status_lines 缺失；#6 三值用例的 fail 腿为既有行为回归钉，非新增行为）
diff --git a/tests/w2iso_baseline.log b/tests/w2iso_baseline.log
new file mode 100644
index 0000000..3733569
--- /dev/null
+++ b/tests/w2iso_baseline.log
@@ -0,0 +1,59 @@
+test_bound_claim_passes (test_check_claims.ClaimsTest) ... ok
+test_effect_without_power_fields_fails (test_check_claims.ClaimsTest) ... ok
+test_unbound_count_fails (test_check_claims.ClaimsTest) ... ok
+test_actions_are_pinned (test_compatibility_matrix.CompatibilityMatrixTest) ... ok
+test_model_class_default_is_core (test_compatibility_matrix.CompatibilityMatrixTest) ... ok
+test_supported_rows_have_ci_legs (test_compatibility_matrix.CompatibilityMatrixTest) ... ok
+test_banned_placeholder_fails (test_contract_lint.ContractLintTest) ... ok
+test_clean_contract (test_contract_lint.ContractLintTest) ... ok
+test_duplicate_cov0_fails (test_contract_lint.ContractLintTest) ... ok
+test_legacy_contradiction_fails (test_contract_lint.ContractLintTest) ... ok
+test_missing_core_profile_fails (test_contract_lint.ContractLintTest) ... ok
+test_missing_cov_fails (test_contract_lint.ContractLintTest) ... ok
+test_precedence_missing_fails (test_contract_lint.ContractLintTest) ... ok
+test_skill_size_cap_fails (test_contract_lint.ContractLintTest) ... ok
+test_mock_smoke_and_report (test_eval_validity.EvalValidityTest) ... ok
+test_power_mde (test_eval_validity.EvalValidityTest) ... ok
+test_prereg_hash (test_eval_validity.EvalValidityTest) ... ok
+test_summary_is_not_run (test_eval_validity.EvalValidityTest) ... ok
+test_check_green_then_detects_drift (test_installer_lifecycle.InstallerLifecycleTest) ... ok
+test_dry_run_writes_nothing (test_installer_lifecycle.InstallerLifecycleTest) ... ok
+test_force_backup_copies_unmanaged_file (test_installer_lifecycle.InstallerLifecycleTest) ... ok
+test_force_required_for_unmanaged_file (test_installer_lifecycle.InstallerLifecycleTest) ... ok
+test_from_migration_and_unknown_profile (test_installer_lifecycle.InstallerLifecycleTest) ... ok
+test_install_writes_files_and_manifest (test_installer_lifecycle.InstallerLifecycleTest) ... ok
+test_rollback_restores_previous_install (test_installer_lifecycle.InstallerLifecycleTest) ... ok
+test_uninstall_preserves_memory (test_installer_lifecycle.InstallerLifecycleTest) ... ok
+test_upgrade_backs_up_and_updates (test_installer_lifecycle.InstallerLifecycleTest) ... ok
+test_budget_constants (test_perf_budget.PerfBudgetTest) ... ok
+test_quick_check_passes (test_perf_budget.PerfBudgetTest) ... ok
+test_core_exists_and_fits_budget (test_profile_core.CoreProfileTest) ... ok
+test_install_core_profile (test_profile_core.CoreProfileTest) ... ok
+test_token_budget_check_passes (test_profile_core.CoreProfileTest) ... ok
+test_bad_bytes_type_fails (test_release_manifest.ReleaseManifestTest) ... ok
+test_bad_schema_fails (test_release_manifest.ReleaseManifestTest) ... ok
+test_bytes_mismatch_fails (test_release_manifest.ReleaseManifestTest) ... ok
+test_clean_tree_verifies (test_release_manifest.ReleaseManifestTest) ... ok
+test_duplicate_path_fails (test_release_manifest.ReleaseManifestTest) ... ok
+test_expected_tag_mismatch_fails (test_release_manifest.ReleaseManifestTest) ... ok
+test_extra_file_fails (test_release_manifest.ReleaseManifestTest) ... ok
+test_hash_mismatch_fails (test_release_manifest.ReleaseManifestTest) ... ok
+test_malformed_digest_fails (test_release_manifest.ReleaseManifestTest) ... ok
+test_manifest_shape_and_deterministic_order (test_release_manifest.ReleaseManifestTest) ... ok
+test_missing_file_fails (test_release_manifest.ReleaseManifestTest) ... ok
+test_path_traversal_rejected (test_release_manifest.ReleaseManifestTest) ... ok
+test_payload_files_dev_layout (test_release_manifest.ReleaseManifestTest) ... ok
+test_broken_link_fails (test_self_check.SelfCheckTest) ... ok
+test_canonical_copy_mismatch_fails (test_self_check.SelfCheckTest) ... ok
+test_clean_tree_passes_without_task_block (test_self_check.SelfCheckTest) ... ok
+test_manifest_mismatch_fails (test_self_check.SelfCheckTest) ... ok
+test_missing_payload_fails (test_self_check.SelfCheckTest) ... ok
+test_backup_fixture_is_scanned (test_state_sanitize.StateSanitizeTest) ... ok
+test_check_fails_and_never_echoes_value (test_state_sanitize.StateSanitizeTest) ... ok
+test_fix_redacts_and_check_passes (test_state_sanitize.StateSanitizeTest) ... ok
+test_gitignore_contains_state_dir (test_state_sanitize.StateSanitizeTest) ... ok
+
+----------------------------------------------------------------------
+Ran 54 tests in 2.812s
+
+OK
diff --git a/tests/w2iso_full_suite.log b/tests/w2iso_full_suite.log
new file mode 100644
index 0000000..dca68c4
--- /dev/null
+++ b/tests/w2iso_full_suite.log
@@ -0,0 +1,5 @@
+............................................................
+----------------------------------------------------------------------
+Ran 60 tests in 3.522s
+
+OK
diff --git a/tests/w2iso_green.log b/tests/w2iso_green.log
new file mode 100644
index 0000000..07bfcfc
--- /dev/null
+++ b/tests/w2iso_green.log
@@ -0,0 +1,11 @@
+test_agent_binds_to_worktree_despite_stale_pwd (tests.test_eval_isolation.EvalIsolationTest) ... ok
+test_contamination_fails_closed (tests.test_eval_isolation.EvalIsolationTest) ... ok
+test_home_isolation_and_directory_arg (tests.test_eval_isolation.EvalIsolationTest) ... ok
+test_host_repo_delta_detects_out_of_sandbox_write (tests.test_eval_isolation.EvalIsolationTest) ... ok
+test_mock_agent_isolated_hidden_test_outside (tests.test_eval_isolation.EvalIsolationTest) ... ok
+test_verdict_three_valued (tests.test_eval_isolation.EvalIsolationTest) ... ok
+
+----------------------------------------------------------------------
+Ran 6 tests in 1.154s
+
+OK
diff --git a/tests/w2iso_green2.log b/tests/w2iso_green2.log
new file mode 100644
index 0000000..eaa5479
--- /dev/null
+++ b/tests/w2iso_green2.log
@@ -0,0 +1,13 @@
+test_agent_binds_to_worktree_despite_stale_pwd (tests.test_eval_isolation.EvalIsolationTest) ... ok
+test_contamination_fails_closed (tests.test_eval_isolation.EvalIsolationTest) ... ok
+test_home_isolation_and_directory_arg (tests.test_eval_isolation.EvalIsolationTest) ... ok
+test_host_repo_delta_detects_out_of_sandbox_write (tests.test_eval_isolation.EvalIsolationTest) ... ok
+test_mock_agent_isolated_hidden_test_outside (tests.test_eval_isolation.EvalIsolationTest) ... ok
+test_seed_state_db_scrubs_content_tables (tests.test_eval_isolation.EvalIsolationTest) ... ok
+test_setup_failure_is_indeterminate (tests.test_eval_isolation.EvalIsolationTest) ... ok
+test_verdict_three_valued (tests.test_eval_isolation.EvalIsolationTest) ... ok
+
+----------------------------------------------------------------------
+Ran 8 tests in 6.365s
+
+OK
diff --git a/tests/w2iso_real_smoke2.log b/tests/w2iso_real_smoke2.log
new file mode 100644
index 0000000..7e9b81f
--- /dev/null
+++ b/tests/w2iso_real_smoke2.log
@@ -0,0 +1 @@
+EVAL smoke: pass -> /Users/logan/Documents/DEV/SKILLS/vibeweaver/tests/eval/runs/smoke-20261023_031133
diff --git a/tests/w2iso_red.log b/tests/w2iso_red.log
new file mode 100644
index 0000000..067fb2f
--- /dev/null
+++ b/tests/w2iso_red.log
@@ -0,0 +1,75 @@
+test_agent_binds_to_worktree_despite_stale_pwd (tests.test_eval_isolation.EvalIsolationTest) ... FAIL
+test_contamination_fails_closed (tests.test_eval_isolation.EvalIsolationTest) ... ERROR
+test_home_isolation_and_directory_arg (tests.test_eval_isolation.EvalIsolationTest) ... FAIL
+test_host_repo_delta_detects_out_of_sandbox_write (tests.test_eval_isolation.EvalIsolationTest) ... ERROR
+test_mock_agent_isolated_hidden_test_outside (tests.test_eval_isolation.EvalIsolationTest) ... ERROR
+test_verdict_three_valued (tests.test_eval_isolation.EvalIsolationTest) ... ok
+
+======================================================================
+ERROR: test_contamination_fails_closed (tests.test_eval_isolation.EvalIsolationTest)
+----------------------------------------------------------------------
+Traceback (most recent call last):
+  File "/Users/logan/Documents/DEV/SKILLS/vibeweaver/tests/test_eval_isolation.py", line 111, in test_contamination_fails_closed
+    iso = self.load("isolation.json")
+  File "/Users/logan/Documents/DEV/SKILLS/vibeweaver/tests/test_eval_isolation.py", line 77, in load
+    return json.loads((self.out / name).read_text(encoding="utf-8"))
+  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/pathlib.py", line 1256, in read_text
+    with self.open(mode='r', encoding=encoding, errors=errors) as f:
+  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/pathlib.py", line 1242, in open
+    return io.open(self, mode, buffering, encoding, errors, newline,
+  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/pathlib.py", line 1110, in _opener
+    return self._accessor.open(self, flags, mode)
+FileNotFoundError: [Errno 2] No such file or directory: '/Users/logan/Documents/DEV/SKILLS/vibeweaver/tests/eval/runs/iso-test-61683c19/isolation.json'
+
+======================================================================
+ERROR: test_host_repo_delta_detects_out_of_sandbox_write (tests.test_eval_isolation.EvalIsolationTest)
+----------------------------------------------------------------------
+Traceback (most recent call last):
+  File "/Users/logan/Documents/DEV/SKILLS/vibeweaver/tests/test_eval_isolation.py", line 128, in test_host_repo_delta_detects_out_of_sandbox_write
+    before = eval_run.git_status_lines(ROOT)
+AttributeError: module 'eval_run' has no attribute 'git_status_lines'
+
+======================================================================
+ERROR: test_mock_agent_isolated_hidden_test_outside (tests.test_eval_isolation.EvalIsolationTest)
+----------------------------------------------------------------------
+Traceback (most recent call last):
+  File "/Users/logan/Documents/DEV/SKILLS/vibeweaver/tests/test_eval_isolation.py", line 121, in test_mock_agent_isolated_hidden_test_outside
+    iso = self.load("isolation.json")
+  File "/Users/logan/Documents/DEV/SKILLS/vibeweaver/tests/test_eval_isolation.py", line 77, in load
+    return json.loads((self.out / name).read_text(encoding="utf-8"))
+  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/pathlib.py", line 1256, in read_text
+    with self.open(mode='r', encoding=encoding, errors=errors) as f:
+  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/pathlib.py", line 1242, in open
+    return io.open(self, mode, buffering, encoding, errors, newline,
+  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/pathlib.py", line 1110, in _opener
+    return self._accessor.open(self, flags, mode)
+FileNotFoundError: [Errno 2] No such file or directory: '/Users/logan/Documents/DEV/SKILLS/vibeweaver/tests/eval/runs/iso-test-399bb007/isolation.json'
+
+======================================================================
+FAIL: test_agent_binds_to_worktree_despite_stale_pwd (tests.test_eval_isolation.EvalIsolationTest)
+----------------------------------------------------------------------
+Traceback (most recent call last):
+  File "/Users/logan/Documents/DEV/SKILLS/vibeweaver/tests/test_eval_isolation.py", line 82, in test_agent_binds_to_worktree_despite_stale_pwd
+    self.assertEqual(self.load("verdict.json")["verdict"], "pass", r.stdout + r.stderr)
+AssertionError: 'fail' != 'pass'
+- fail
++ pass
+ : EVAL smoke: fail -> /Users/logan/Documents/DEV/SKILLS/vibeweaver/tests/eval/runs/iso-test-e5cecda0
+
+
+======================================================================
+FAIL: test_home_isolation_and_directory_arg (tests.test_eval_isolation.EvalIsolationTest)
+----------------------------------------------------------------------
+Traceback (most recent call last):
+  File "/Users/logan/Documents/DEV/SKILLS/vibeweaver/tests/test_eval_isolation.py", line 96, in test_home_isolation_and_directory_arg
+    self.assertEqual(self.load("verdict.json")["verdict"], "pass", r.stdout + r.stderr)
+AssertionError: 'fail' != 'pass'
+- fail
++ pass
+ : EVAL smoke: fail -> /Users/logan/Documents/DEV/SKILLS/vibeweaver/tests/eval/runs/iso-test-e7a405d4
+
+
+----------------------------------------------------------------------
+Ran 6 tests in 0.932s
+
+FAILED (failures=2, errors=3)
diff --git a/tests/w2iso_regression.log b/tests/w2iso_regression.log
new file mode 100644
index 0000000..528d248
--- /dev/null
+++ b/tests/w2iso_regression.log
@@ -0,0 +1,20 @@
+== step 1: revert the fix (git checkout b6afd5a -- scripts/eval_run.py) ==
+== step 2: run the isolation suite — MUST FAIL ==
+step2_exit=1
+test_agent_binds_to_worktree_despite_stale_pwd (tests.test_eval_isolation.EvalIsolationTest) ... FAIL
+test_contamination_fails_closed (tests.test_eval_isolation.EvalIsolationTest) ... ERROR
+test_home_isolation_and_directory_arg (tests.test_eval_isolation.EvalIsolationTest) ... FAIL
+test_host_repo_delta_detects_out_of_sandbox_write (tests.test_eval_isolation.EvalIsolationTest) ... ERROR
+test_mock_agent_isolated_hidden_test_outside (tests.test_eval_isolation.EvalIsolationTest) ... ERROR
+ERROR: test_contamination_fails_closed (tests.test_eval_isolation.EvalIsolationTest)
+ERROR: test_host_repo_delta_detects_out_of_sandbox_write (tests.test_eval_isolation.EvalIsolationTest)
+ERROR: test_mock_agent_isolated_hidden_test_outside (tests.test_eval_isolation.EvalIsolationTest)
+FAIL: test_agent_binds_to_worktree_despite_stale_pwd (tests.test_eval_isolation.EvalIsolationTest)
+FAIL: test_home_isolation_and_directory_arg (tests.test_eval_isolation.EvalIsolationTest)
+Ran 6 tests in 0.677s
+FAILED (failures=2, errors=3)
+== step 3: restore the fix (git checkout HEAD -- scripts/eval_run.py) ==
+== step 4: run again — MUST PASS ==
+step4_exit=0
+Ran 6 tests in 1.065s
+OK
diff --git a/tests/w2iso_regression2.log b/tests/w2iso_regression2.log
new file mode 100644
index 0000000..ff1c5c7
--- /dev/null
+++ b/tests/w2iso_regression2.log
@@ -0,0 +1,16 @@
+== step 0: snapshot of the working fix -> /private/var/folders/8z/h73xmj297g1995r1d9q6dc2r0000gn/T/opencode/vw-eval_run.fixed.py ==
+a50359476eeaed72254f56b96d2534e9
+== step 1: GREEN on the fix ==
+green_exit=0
+Ran 8 tests in 6.154s
+OK
+== step 2: revert to 6bafc01 (before seed_state_db + setup-failure) — MUST FAIL ==
+revert_exit=1
+FAIL: test_seed_state_db_scrubs_content_tables (tests.test_eval_isolation.EvalIsolationTest)
+FAIL: test_setup_failure_is_indeterminate (tests.test_eval_isolation.EvalIsolationTest)
+Ran 8 tests in 1.279s
+FAILED (failures=2)
+== step 3: restore from snapshot — MUST PASS ==
+restore_exit=0
+Ran 8 tests in 6.059s
+OK
diff --git a/tests/working_note.md b/tests/working_note.md
new file mode 100644
index 0000000..ecf1f36
--- /dev/null
+++ b/tests/working_note.md
@@ -0,0 +1,38 @@
+# W2-ISO working note（live state，任务结束时 distill → delete）
+
+> 用途：本任务的活体假设账本（§A7.15）。只记未定项与判据状态，完成后蒸馏进 memory/ 并删除本文件。
+
+## 任务
+
+修 `scripts/eval_run.py --agent opencode` 的 worktree 隔离（UNFINISHED_20261023 §3 W2-ISO，P0），
+并用真实 smoke 收口 W2-T12。
+
+## 根因（已证）
+
+- `opencode run` 会话目录取自**环境变量 `$PWD`**，不取进程 cwd（诱饵探针：cwd=/tmp/vwprobe3，
+  `PWD=/tmp/vwprobe_decoy` → `probe_a.txt` 落 decoy）。
+- `eval_run.run_agent` 用 `subprocess.run(cwd=work)` 只改真实 cwd；继承的 `PWD` 仍指宿主 repo → 事故。
+- `run_agent(name, work, home, model)` 收到 `home` 却从不使用（`env = dict(os.environ)`）→ HOME 隔离名不副实。
+- 显式绑定形式（实测）：`opencode run [flags] <directory> <message...>`（目录位置参数在 message 之前）。
+
+## 判据状态（#45-#49）
+
+| # | 判据 | 状态 | 证据 |
+|---|---|---|---|
+| 45 | mock 产物只在 worktree；隐藏测试在工作区外；污染不拿 pass | 待 GREEN | tests/w2iso_red.log |
+| 46 | $PWD/cwd/目录参数 三者绑定 worktree | 待 GREEN | tests/w2iso_red.log |
+| 47 | 沙箱外零写入 + 违例 fail-closed | 待 GREEN | tests/w2iso_red.log |
+| 48 | 真实 smoke 产出 4 json + 三值正确 | 未跑 | — |
+| 49 | HOME 隔离（播种三项，宿主插件不进） | 待 GREEN | — |
+
+## 未定项
+
+- 隔离监控只覆盖「宿主 repo git-status 差分」+「沙箱内 work/ 之外的任务产物」两腿；
+  任意其他 FS 位置的写入未监控（residual，完成后写入 memory 与完成表）。
+- 真实 smoke 的 HOME 隔离是否让 provider/auth 失效：Task 3 一跑即知（播种 auth.json/models.json/opencode.jsonc）。
+- Task 14（96-run pilot）预算未定 —— 本轮不做（UNFINISHED §6 禁令），结束时以 PAUSED/预算问题上交。
+
+## 失败方向（❌，勿重试）
+
+- ❌ 只把 `cwd=work` 当绑定（既有实现）——实测被 `$PWD` 覆盖。
+- ❌ `opencode <directory> run …` 形式 —— 实测解析失败（`Unrecognized flag: --format in command opencode`）。
```

## 新增未跟踪文件（本次任务创建）
```
memory/fix_eval_isolation_w2iso.md（memory 记忆条目，纯散文）
tests/test_eval_isolation.py（已在上方 diff 之外？否——已提交 6bafc01，见 diff）
```
