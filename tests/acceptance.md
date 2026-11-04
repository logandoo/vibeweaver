> cap=5  stall=3×

# Acceptance — W18 实施第 1 批 P0（G1 门禁三态 · G2 tests/ 豁免 · R1 Class-E runbook · D-W18-2 必修回归）

Source: `docs/PLAN_w18_gate_hardening_20261021.md` §G1/§G2/§R1 + §"新波次开工清单"（第 1 批 P0）· tests/decisions.md D-W18-2（必修回归）· W12 实测事故记录（同计划文档头部）。

1. G1 三态：无 seal 的项目根上 gate 输出 `evidence seal: none yet` 且**不** GATE-BLOCKED（早期波次豁免：当前任务块无 `- iter N PASS` 时封印义务不成立）；seal 存在但 code_fingerprint 不匹配 → BLOCK 且文案含 `STALE`；匹配 → 静默。assert 级与 gate 级 selftest 覆盖，RED→GREEN 有日志。
2. G2 放行方案：真实宿主参数形态（`args.path`）下写 `tests/**` 不被 GATE-BLOCKED（与 COMPLETION_GATE.md §A4.4.2 "tests/ writes are never gated" 一致），写 `src/x.js`（缺证据）仍 BLOCK；含文档↔实现一致性断言（grep 级）。
3. R1 runbook：ENGINEERING_STD.md §A10.1 给出可照抄的 6 步 Class-E 历史重写顺序清单（强制提交工作树 · mirror 备份 · filter-repo · .git/blob/count 验收对照 · commit-map hash remap · refs-original/reflog 清理），MEMORY_RULES.md §A7.10 补 remap 后再过 Gate 3；tmp 仓演练通过（第 1 步 dirty tree 被拒、走完后 git log 可追、commit-map remap 有产出物）。
4. D-W18-2 必修回归：`node tests/plugin_compat_test.mjs` 全绿（原 71 项含 E3/G9 + 本波新增 G1/G2/E3b 用例）且 known-failure 豁免（`--allow-known`/`known`）已删除；G9 no-newline x4 周期判定修复（x3 clean / very×40 fire / div×3 clean / punct clean 不回归）；E3 测试↔规格冲突按 VERIFICATION_UPGRADES §V2 规则 2/3 以 ADR 裁定并留痕（断言只加强不放松）。
5. 硬约束：SKILL.md 保持 < 49,000 B；`scripts/assert_artifacts.py` 22 个 self-verify marker 一个不少；`scripts/` 与 `tests/` canonical 副本一致；eval 仓 vendored 副本本波不碰；`node scripts/audit_selftest.mjs`、`node scripts/mutation_sweep.mjs`、`python3 tests/test_assert_groups.py` 全绿。

# Acceptance — W18 第二波：sync + D1 + 批 2/3（用户指令 2026-10-21「同步吧，然后把剩下的事情完成（完成输出顺序唯一化）尽快做掉」）

6. 同步完成：dev→system/open-source/repo 24 项 payload + 插件对字节一致（diff -q fail=0），`tests/sync_skill.py` 含 eval pins 全绿，repo verify_skill+selftest 过并 push，dsh 手移植过其单测。
7. D1 完成输出顺序唯一化：COMPLETION_GATE §A4.4 给出唯一权威顺序，SKILL/REFERENCE 引用化，grep/机检断言（T39）证明三处文档无第二顺序表述。
8. 批 2/3 全部实施并有回归：G3（--record-debt 棘轮）· G4（claim-lint 当前块+claim-ack）· G5（非 web seal 绑定+record_evidence.sh）· G6（- wave-base 任务锚点）· R2（carry-over 先行）· R3（纯删除不计波上限）· T1（make_review_package.sh）· T2（git add -f hint）· D-W18-6（new-task 归因）。
9. 硬约束守住：SKILL.md < 49,000 B、companion ≤ 45,000 B、22 marker 全在、canonical 副本一致；A4.9 双对抗复审 + scoped re-review 的 Critical/Important 全部修复并有 PoC/revert 证据；FCV fresh-context 复跑全绿。

# Acceptance — C4 audit：W18 发布「宣称 vs 实物」核验（2026-10-22）

10. 另一 agent 的全部指控在 GitHub main 实物（sha d81a7051，`git ls-remote` 证明与实测树同一 commit）逐条独立复测，二分为属实/不实，每条附 file:line 或命令输出摘录。
11. W18 机制（债棘轮/claim-ack/wave-base 锚点）交付正确性由可执行套件在该树复现（audit_selftest/mutation_sweep/mini_gate/unittest/verify_skill + dev 82 例 harness）。
12. 「宣称与实物不符」若存在，根因定位到具体文件/机制，区分「机制方案缺陷」与「同步/归档/口径治理缺口」，并给出严重度分级与修复优先级。
13. Critical/Important 发现经 fresh-context 独立复核者裁定一致（A4.9 契约）。

# Acceptance — W18 发布卫生修复（F1-F7 + 根因，2026-10-22；计划 docs/PLAN_release_hygiene_fix_20261022.md）

14. B 树 `node tests/plugin_compat_test.mjs`（无参数）82/82 exit 0，且 B `tests/plugin_compat_test.mjs` 与 A 同名文件 sha256 相等。
15. B `.github/workflows/verify.yml` 不含 `--allow-known`/known 豁免且含 Doc claims parity 步骤；`check_doc_counts.py` 对 README/README_zh 四套件计数实跑比对通过，且注入错误计数（如 70/71）时 fail（可证伪）。
16. README/README_zh 的 selftest/mutation/compat/mini 计数与实跑一致（571 · 44 · 82/82 · 62/62）；CHANGELOG/CHANGELOG_zh 新增 2026-10-22 条目（gap→mechanism→verification）记录审计发现与修复，无不可复现计数。
17. B 树 tests/w18/、tests/w18sync/ 证据 29 件在库 + W18 验证日志归档文件；`git tag` 含 w18 → 9d2c915。
18. A `tests/sync_skill.py` 受控清单含 plugin_compat harness 与 w18/w18sync 证据目录（repo 目标 + --allow-missing-repo），`python3 tests/test_sync_skill.py` 全绿（SS9-SS13 含 RED 证据）；A/B 两树六套件全绿。

# Acceptance — C6 事故修复：Doc claims parity CI 红（2026-10-22）

19. mini 计数的平台差异被如实处理：文档为三平台各给数字（62/62 macOS · 60/60 Linux · 55/55 Windows），check_doc_counts 每平台只绑定本平台宣称、外平台顺延；本平台错数/缺宣称必红（CDC14-17）。
20. CI 六条矩阵腿全绿（含 windows 两腿）；审计 R2 误判已更正并入 memory 教训。

# Acceptance — W0 P0 综合硬化（2026-10-22；计划 docs/PLAN_comprehensive_hardening_20261022.md）

> cap=5  stall=3×
> 续号映射：本块 #21–#28 = 计划 Acceptance #1/#3/#4/#5/#18/#27/#28/#2（P0 出口 = #21–#24 + #26–#27 + #28；#25 为 Task 2.5 的 #28）。

21. (计划 #1) `python3 scripts/verify_release.py` 对发布树输出 `MANIFEST OK N/N` exit 0；单字节篡改/缺文件/多文件 → exit 1 且指出路径；`install.sh --dry-run` 打印安装清单 + manifest digest，`--no-verify` 仅显式可用。
22. (计划 #3) `bash tests/gate_trust/run.sh` → `fake-checker: BLOCKED` · `canonical: PASS` · `tampered: BLOCKED`；`bash tests/gate_trust/cache_invalidation.sh` → 3/3（checker 更新失效 · mid-task→final 不复用 · 证据变更失效）。
23. (计划 #4) clean clone `bash tests/self_check.sh` → `SELF-CHECK OK`；`python3 tests/assert_artifacts.py --self-check` exit 0；公开树存在 `tests/assert_artifacts.py`。
24. (计划 #5) `python3 scripts/contract_lint.py` → `0 conflicts`；`SKILL.md` 有且仅有一个 COV-0；原 line 176 不再与 COV-0 冲突（COV-0 优先）。
25. (计划 #28) `bash tests/gate_trust/evidence_integrity/run.sh` → 6/6：改 acceptance / 删 FAIL 行 / 改 profile / 改 debt baseline / 1-byte PNG 全部 block；legacy log 迁移 pass。
26. (计划 #18) `python3 scripts/state_sanitize.py --check .vibeweaver/` → 0；假 `sshpass -p hunter2` 与 `AKIA…` 写 state 后零字面量；`git status --porcelain` 不含 `.vibeweaver/`；20k 事件回归状态大小有界。
27. (计划 #27) `node tests/bootstrap_test.mjs` → 4/4 + no-hook fallback 1/1；v1/v2/no-hook 三态注入一次、compaction 后再注入、子会话不注入、full 已注入时不重复；eval 子集 `loaded: N/16` 达标（≥8/16）。
28. (计划 #2) 发布工作流产出 attestation/manifest，`gh attestation verify release/MANIFEST.json --owner logandoo`（或 `cosign verify-blob`）可执行并绿；`gh release view w18.2` 含 manifest 与 3 条 verify 命令。

# Acceptance — W1 第一批：installer · gate activation · contract lint · profiles · perf · claims

Source: `docs/PLAN_comprehensive_hardening_20261022.md` W1（Task 5.5 / 6 / 8 / 9 / 9.5 / 11）。

29. (计划 #19) `python3 -m unittest tests.test_installer_lifecycle` → 8/8：临时 HOME 内 install → check → upgrade → rollback → uninstall 全链；`--dry-run/--backup/--check/--uninstall/--force` 行为正确；`memory/` 永不被删除。
30. (Task 6) 门禁激活 = `tests/verification_log.md` 或 `.vibeweaver/project.json`；有 marker 无 log 时输出一次 `GATE-INACTIVE`；`--existing`/`--backend-only` 需 task block 有 `- class:` + `- profile:`；实际 flags 写入 `tests/gate_result.json`；伪造 DOC + code 写 → block；正常 Modify-Existing → 绿。
31. (Task 8) `python3 scripts/contract_lint.py` → `0 conflicts`，并检查 13 个 COV 编号连续、COV-0 唯一、line-176 无冲突、禁用占位词、size caps（SKILL <49KB、companion ≤45KB、bootstrap ≤2KB）。
32. (计划 #7) `bash vibeweaver/install.sh --profile core` 后安装的 `SKILL.md` ≤4k tokens；`install.py --check` 报 `profile=core`；`token_budget.py` 断言 core ≤4k / full ≤90k / mini ≤2k；mini 安装器各自平台计数不变。
33. (计划 #20) `python3 scripts/perf_budget.py --check` → `PERF PASS`；1k/10k/45k fixture gate p95 在预算内（45k ≤5s，且不做全树 stat）；日志入 `tests/perf/`。
34. (计划 #6) `python3 check_claims.py` → `0 unbound`；注入 `70/71` 与无 n/seeds 的 `16/16` 均 fail；README/CHANGELOG 每个 count/effect 宣称命中 registry。

# Acceptance — W1 第二批：gate activation · risk paths · destructive guard · security · compatibility

Source: `docs/PLAN_comprehensive_hardening_20261022.md` W1（Task 6 / 7 / 7.5 / 20 / 21）。

35. (Task 6) 门禁激活 = `tests/verification_log.md` 或 `.vibeweaver/project.json`；有 marker 无 log 时输出一次 `GATE-INACTIVE`；`--existing`/`--backend-only` 需当前 task block 有 `- class:` + `- profile:`；实际 flags 写入 `tests/gate_result.json`；`--class DOC` 与 code 写不一致 → block；正常 Modify-Existing → 绿。
36. (Task 7) 风险路径（auth/security/payment/billing/crypto/migration/permission/acl）与删除操作：无 ADR/用户批准 → pre-write block；`tests/decisions.md` 有 ADR → pass；普通路径 → pass。
37. (Task 7.5) `bash tests/gate_trust/destructive_commands/run.sh` → 10/10：`git add -A` / `rm -rf src` / `git reset --hard` / `git clean -fdx` / `git checkout -- .` block；`rm -rf node_modules`、`.venv`、`dist`、`$TMPDIR` pass；有 ADR 的命令 pass；无 pre-hook 宿主退化为 post-hoc `GATE-WARNING` 且标注 adapter-only。
38. (计划 #21) `bash tests/security/run.sh` → 8/8（fake checker、symlink escape、traversal、secret state、prompt injection、bound-root、manifest mismatch、destructive）；`mutation_sweep.py` score ≥90%；`docs/TRUST_MODEL.md` 每个威胁有 control + residual + test。
39. (计划 #26) `python3 -m unittest tests.test_compatibility_matrix` → 矩阵与 CI 一致；`docs/COMPATIBILITY.md` 无无证据的 `supported`；`VIBEWEAVER_MODEL_CLASS` 有默认/报错。

# Acceptance — W1 第三批：claims registry（Task 11）

40. (计划 #6) `python3 scripts/check_claims.py` → `0 unbound`；注入 `70/71` 与无 n/seeds/ci 的 `+251%` 均 fail；README/README_zh 与 CHANGELOG 当前条目的 count/effect 宣称全部命中 `release/claims.json`。

# Acceptance — W2 第一批：eval lab · validity/power · G3 prereg

Source: `docs/PLAN_comprehensive_hardening_20261022.md` W2（Task 12 / 12.5 / 13 / 16 statement）。

41. (计划 #? Task 12) `python3 scripts/eval_run.py --scenario smoke --agent opencode` 产出 `verdict.json` + `trajectory.json` + `cost.json`；隔离 HOME/worktree；`indeterminate` 不进入 pass；隐藏测试不在 agent 工作区。
42. (Task 12.5) `python3 scripts/eval_power.py --n 16 --seeds 3` 打印 MDE；`tests/eval/g3/summary.json` 含 n/seeds/95% CI/paired diff/cost/MDE/κ；contamination/grader-independence/multiplicity/kill-criteria 有文档与测试。
43. (Task 13) `sha256sum docs/EVAL_G3_PREREG.md` == `tests/eval/g3/prereg.sha256`；prereg 含 contamination、MDE/power 决策规则、单一 primary endpoint、停止规则。
44. (Task 14/16 状态) `tests/eval/g3/summary.json` 明确 `status: not_run`（或真实 n/seeds/CI），不得伪造；README/`docs/REPLICATION.md` 标注 `single-operator; no independent replication`。

# Acceptance — W2-ISO：opencode worktree 隔离修复（W2-T12 收口）

Source: `docs/UNFINISHED_20261023.md` §3 W2-ISO 完成判据 + §7 步骤 3（先修 W2-ISO，才谈 96/192 runs）。

45. `python3 scripts/eval_run.py --scenario smoke --agent mock` 运行后，任务产物（`hello.txt`）只出现在本次运行的临时 worktree 内；隐藏测试文件不在 worktree 内；verdict 是三值之一，且带污染的运行拿不到 `pass`。
46. 主体 agent 的会话目录绑定到临时 worktree（不是宿主 repo）：stub 代理与真实 `--agent opencode` 运行都证明 `$PWD`、进程 cwd、CLI 目录位置参数三者指向 worktree。
47. mock 与 real smoke 运行结束后 worktree/沙箱之外零写入：宿主 repo `git status --porcelain` 前后差分为空（本次证据目录 `tests/eval/runs/` 除外），且临时沙箱内 `work/` 之外没有任务产物；任何违例 → `verdict=indeterminate`（永不 `pass`）。
48. `python3 scripts/eval_run.py --scenario smoke --agent opencode` 真实跑通并产出 `verdict.json` / `trajectory.json` / `cost.json` / `isolation.json`；verdict 三值正确（`pass`=隐藏测试 exit 0；`fail`=隐藏测试 exit 1 或 agent 非零退出；`indeterminate`=越界/捕获失败/隐藏测试非 0-1 退出）；隐藏测试仅在评分时从 lab 注入。
49. HOME 隔离生效：被测 agent 以本次运行的临时 HOME 运行（只播种 `auth.json`/`models.json`/`opencode.jsonc` 三项），宿主 `~/.config/opencode` 插件不进入被测会话（stderr 无 `GATE-BLOCKED` 噪音；trajectory 记录 home 路径）。

# Acceptance — W2-T14 前置：G3 pilot 场景集（8 场景 + 隐藏测试，不跑 live）

Source: `docs/UNFINISHED_20261023.md` §7 步骤 4 + 用户决定「先写 8 场景+隐藏测试，暂不跑 live」+ `docs/EVAL_G3_PREREG.md`（冻结）。

50. `tests/eval/lab/scenarios/` 有 8 个 G3 pilot 场景（`g3_*.json`），每个含 `id`/`prompt`/`hidden_test`/`artifacts`/`timeout_seconds` 五个字段且互相一致（hidden_test 文件存在、artifacts 非空），`python3 scripts/eval_run.py --scenario <id> --agent mock` 能跑通解析与评分流程。
51. 每个场景有对应隐藏测试 `tests/eval/lab/hidden/g3_<id>_test.py`：只读 worktree（argv[1]），结果只有 exit 0/1，隐藏测试文件位于 agent 工作区之外（沿用 W2-ISO 契约）。
52. 有效性自检（§V8 SPR/MS 门）通过：每个任务 gold 参考产物 → 隐藏测试 exit 0；空 worktree → exit 1；错误/朴素实现 → exit 1；`python3 tests/eval/lab/selfcheck.py` 全绿。
53. 不跑 live：`tests/eval/g3/summary.json` 保持 `status: not_run`；文档如实标注「G1 set 外部不可得 → 以 private held-out 替代（prereg 允许）」与污染检查缺口；既有测试套件（70 例）不回归。


# Acceptance — W2-T14 G3 live pilot（模型 biklimax/qwen3.8_27b，用户已授权）

Source: `docs/UNFINISHED_20261023.md` §7 步骤 4 + 用户指令「使用 biklimax:28000 的 qwen3.8-27B 进行测试」+ `docs/EVAL_G3_PREREG.md`（冻结）。

54. `python3 scripts/eval_pilot.py --model biklimax/qwen3.8_27b …` 按 prereg 跑 pilot：8 任务 × 4 arms × 3 seeds = 96 次 live 运行，每次产出 `verdict.json`/`trajectory.json`/`cost.json`/`isolation.json`，目录可区分 task/arm/seed。
55. arm 构造有明文规格（`docs/EVAL_G3_ARMS.md`）且实现与之一致：`bare`=无 skill；`core`=core profile 自发触发；`full_forced`/`mini_forced`=skill 内容强制进上下文；**arm 间唯一变量是 skill 内容与传递方式**（prompt 其余部分逐字节相同）。
56. `tests/eval/g3/summary.json` 含 prereg 字段：`n` / `seeds` / 95% CI / paired diff（对 `bare`）/ `mde` / `cost`；`status` 不再是 `not_run`（若只跑完一部分则如实标 `incomplete` 并给实际 n，不用超时/污染任务凑数）。
57. `indeterminate` 单列且**永不计 pass**；每 arm 的 pass rate 用 Wilson 95% CI；paired diff 按 task 配对计算。
58. 校准先于解读（§V8）：每任务先跑 bare ≥1 次并记录完成率与墙钟；跑不动的任务如实报告实际 n 与 MDE。



# Acceptance — W2-T14b G3 判别性复测 + LICENSE 定稿（用户授权：MIT；2026-10-24）

Source: 用户「可以，继续。license?不是 mit 吗？」+ `docs/EVAL_G3_PILOT_REPORT.md` §5 下一步（换判别器/扩预算）+ 遗留 minor（process-group kill）。

59. `LICENSE`（MIT，Copyright (c) 2026 logandoo——仓库最早提交 2026-08-21）+ `NOTICE` 落盘；`python3 scripts/license_check.py` exit 0（之前 5 fail 清零，含把自身标记串误判为内嵌第三方头部的自指假阳性——自指排除必须有明文理由）。
60. 三个 compliance 场景 `g3_comp_*.json` + 对应 hidden 测试通过 selfcheck 三向门（gold→0 / empty→1 / naive→1）；**naive = 功能正确但无证据构件**——这正是 pilot 天花板效应的判别器设计（W7：pure-capability 全饱和，process-contract 才分得开）。
61. hidden 测试的证据断言只要求根/core SKILL 实际契约明文规定的形状（`tests/acceptance.md` 顶行 `> cap=5  stall=3×`、`tests/verification_log.md` 的 `- class:` 与 `- iter N PASS` 行），不要求契约未规定的格式；prompt 不泄露证据文件的存在或格式（否则 bare 臂学会答案、判别力归零）。
62. 超时硬化：`eval_run.py` 的 agent 子进程用独立进程组（`start_new_session` + 超时 `killpg`），mock 挂起场景下超时返回后无孤儿进程继续烧模型额度；新增 `tests/test_process_group_kill.py` 可执行验证。
63. 判别性战役（3 compliance 任务 × 4 arms × 1 seed，forced 预算 1800s）产出 `tests/eval/g3/comp_summary.json` + 报告更新；结果如实呈现（bare 预期因无证据构件而 fail——这是设计使然，不是缺陷）。

64. full_forced 180min 重测：3 comp 任务 × 3 seeds = 9 runs 全部有 verdict（pass/fail/indeterminate 三值均算完成，不再称"缺数据"）；comp 场景 timeout_seconds=10800；启动前人工复核 plan 打印行 = 9（D-W2ISO-8 纪律）；`tests/eval/g3/comp_summary.json`（task_filter=g3_comp_）更新后仍 status=complete 36/36；报告 §7 的 full_forced 行与结论按实际数据改写（含耗时墙钟）。

65. 产品形态臂 `full_deployed`：`eval_run.py` 支持该臂 = skill payload + `~/.config/opencode/plugins/` 整目录进高温 HOME + 场景 `setup_files`（JSON 声明式）预放进沙箱 worktree；单测证明（mock，不打模型）：高温 HOME 出现 gate/audit 两 js 与 skills payload、setup_files 落进 work、既有四臂行为不变。
66. gate 事件解析器 `scripts/gate_events.py`：从 trajectory.json 的 opencode JSON 流统计 GATE-BLOCKED 拦截次数、按类型（completion/evidence-lock/destructive/secret/stall）分布、首次拦截位置；fixture 单测通过（含 0 事件、非 JSON 流容错）。
67. 3 个 comp 场景加 `setup_files`（verification_log 激活头 + class/profile/baseline 行、acceptance 首行、project_profile.json）——静态验证：canonical checker 在预放树 + `--existing --backend-only` 下只剩 agent 可自修的 fail（memory/MEMORY.md、iter 行），无结构性死锁。
68. 真烟测 1 run（g3_comp_dedupe × full_deployed × s0，biklimax/qwen3.8_27b）：trajectory 中 GATE-BLOCKED ≥1（插件真生效的判据；0 事件=哑火，停止战役先修 harness）。
69. v2 战役 9 runs（3 comp 任务 × full_deployed × 3 seeds）全部有 verdict；启动前人工复核 plan 行=9（D-W2ISO-8）；`v2_summary.json` 出 bare(复用 0/9) vs full_forced(3/9) vs full_deployed 三列 pass rate + 墙钟 + gate 事件统计。
70. README 完全重写：读者导向结构（readme-weaver 标准），所有数字宣称与 `release/claims.json` 一致且与 v2 数据同步（v2 完成前 README 不得引用 full_deployed 数字）；重写后 assert --final exit 0。

71. 评分器修复（用户授权 2026-10-26，ADR 记录）：`_comp_evidence.py` ① iter 行正则接受 `criterio[n]a`（单复数）且报错文案与代码行为一致（存在性，不谎称位置）② acceptance 首行接受 `3x` 与 `3×`（值语义而非字符形态，cap/stall 数值仍须逐字）③ selfcheck 新增 gold 变体夹具（复数 criteria + ASCII-x 首行必须活、naive 仍死）④ 11/11 valid 保持；报告 §8 追加勘误（不重写历史）。
72. 修复后重跑 v2 战役 9 runs（label=v2fix，同任务同臂同 seeds）；启动前人工复核 plan=9；新 summary 与旧口径并列呈现（50% 严格形态税 vs 修复后真实合规），README 数字按新数据更新且 claims 同步。

73. F7 headless 降级（产品补强）：MEMORY_RULES.md 状态流新增「无人值守降级」条——需要用户确认的晋升一律记账（`- awaiting decision:` + 保持 ⏳），不得以等待确认中止任务或结束会话；COMPLETION_GATE.md 预输出清单同步；回归测试钉住两面（降级条款存在 + ⏳→✅ 仍只能由用户确认，反伪造不放松）；验证 run（dedupe × full_deployed × s1，F7 原发 seed）agent_exit=0 且 trajectory 尾部无等待确认。
74. bare 必败任务筛选（n 扩样前置）：≥2 个「纪律有牙齿」新任务（spec-vs-test 冲突 / 作用域+保持陷阱），hidden 只测功能；selfcheck 三向门 valid；bare 筛查（每任务 3 seeds）中 bare 至少 2/3 fail 且失败为功能面——不达标任务淘汰并记原因。
