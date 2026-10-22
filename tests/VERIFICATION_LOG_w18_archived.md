# W18 verification log — archived from the dev tree

> Provenance (2026-10-22, release-hygiene fix): these are the verbatim W18 task
> blocks (2026-10-21 — the plan wave plus the three implementation waves) of the
> dev tree's `tests/verification_log.md` — the executed evidence behind the W18
> changelog claims. They were produced in
> the dev tree while the published repo carried none of them (audit finding F4);
> archived here so the claims and their anchor live in the same tree. The
> evidence logs they cite are in `tests/w18/` and `tests/w18sync/`. Excluded
> with this marker: the 9 lines that follow these blocks in the dev log belong
> to a separate 10-21 task (bilingual README dedup), not to W18.

---

## W18 — vibeweaver 加固计划文档（2026-10-21）

- class: CODE — 本任务交付物为 prose md（docs/PLAN + tests/ + memory/，零代码）；但 wave 取样锚点 99ec5d9 属上一波次，measured wave 含前几波 plugin 代码（vibeweaver-audit.js 等 5 个 .js/.mjs）——按 C1 asymmetry 就高升类为 CODE（绝不降级），基线锚点错位已记为计划条目 G6
- Baseline has 2 pre-existing failures (plugin_compat: E3-audit-v1 stale-latch auto-release · G9-loopguard-v1 no-newline x4) — named disposition: 本波零代码改动（diff 全为 prose md），二者位于前几波 plugin 代码、provably out of scope，按 AUTO I4 路径以 ADR 置换处置：quarantined by scope（见 tests/decisions.md），报告用户并移交 W18 实施波次；覆盖测试 audit_selftest 568 checks / 0 failures GREEN on delivered tree
- iter 1 PASS: criterion #1 #2 #3 | docs/PLAN_w18_gate_hardening_20261021.md 落盘：11 项（G1-G5/R1-R3/D1/T1-T2）四段齐全（实测证据/SOTA 依据/修改规格/验收命令），SOTA 4 组可查（joeira-ratchet 三态 + OWASP CVE-lite + openchrome 单向棘轮 · Google pyguide/TS + Android lint 抑制政策 · SLSA v1.2/in-toto · git 官方 filter-repo 推荐 + filter-branch 破坏性 checklist）；含不改清单 + 开工清单 | 覆盖 3/3 criteria
- docs-drift: none（新增计划文档；无既有文档因本次改动过期）
- test-change: tests/plugin_compat_test.mjs — 前几波 plugin-compat 代码，本 docs 波未改动；基线 re-seal 授权以绑定当前测试代码（C3b）
- assert-run: assert_artifacts.py: all 29 checks pass
- final-run: --existing --final — pass=29/fail=0

## W18-impl batch1 — G1 门禁三态 · G2 tests/ 豁免 · R1 Class-E runbook · D-W18-2 必修回归（2026-10-21）

- class: CODE — basis: 计划文件集含 vibeweaver-gate.js / scripts/assert_artifacts.py / vibeweaver-audit.js 逻辑变更（分支/状态判定），按 §V11.2 首match CODE
- wave-base: de7da4d
- Mode: AUTO | Lane: L (≥3 文件 · 行为语义变更 · 计划 §开工清单 ⑤ 强制 A4.9) | Verifier: direct read (non-web)
- Baseline has 2 pre-existing failures (plugin_compat: E3-audit-v1 · G9-loopguard-v1) → disposition: D-W18-2 列为本波必修回归项（ADR D-W18-2 revisit-if 已触发），其余全绿：audit_selftest fixture checks 568/0 (1 skipped) + mutation sweep 44/0（tests/w18/baseline-build.log）
- live-incident: 本波第一笔 `tests/acceptance.md`/`tests/working_note.md` 写入即被 `GATE-BLOCKED ... sealed evidence is STALE (C3 freshness) ... (missing != success)`（write 实际已落地）——G2 漂移（COMPLETION_GATE §A4.4.2 称 tests/ writes are never gated）+ G1 三态缺失的现场复现，与 W12 30+ 误报同类；记为 G1/G2 的 RED 场景证据
- oracle: project-tests（compat harness + audit_selftest + mutation_sweep + test_assert_groups，全部项目自有验收测试）
- test-change: tests/plugin_compat_test.mjs — G9 用例原样保留（RED→GREEN 回归锚）；E3 断言按 D3 规格重定（§V2 rule 2/3 + ADR D-W18-3，从严：外会话写必须被拦且 latch 存活，新增 E3b 存活断言）；删除 `--allow-known`/`known` 失败豁免（D-W18-2 必修回归）；新增 D9-D11（args.path 真实宿主形态 tests/ 豁免 · no-seal 三态不阻断 · seal 后改码 STALE 阻断 · 文档↔实现一致性）
- test-change: tests/test_assert_groups.py — 新增 S45-S48（G1 三态 no-seal WARN · bootstrap 降级 · seal-live STALE FAIL · --final 媒体封印牙齿），既有 S1-S44 断言零改动
- iter 1 FAIL (RED): criterion #1 #2 #4 | diagnosis: 旧组 15b 无三态（无 seal 与过期混同、文案自相矛盾），gate 只认 args.filePath 使 tests/ 豁免永不生效，G9 尾随空白 rtrim 让 end-anchored 周期窗错相 1 位致 x4 MISS | changed: tests/plugin_compat_test.mjs, tests/test_assert_groups.py | RED 证据: tests/w18/red-revert-assert.log（de7da4d 版 assert 上 S45/S46 FAIL）+ tests/w18/baseline-build.log（G9 x4=0 · E3 blocked · 首笔 tests/ 写入即 STALE banner）
- iter 2 PASS: criteria #1 #2 #3 #4 #5 | evidence: tests/w18/iter1-assert-groups.log 52/52（含 S45-S48）· tests/w18/iter1-build.log（audit_selftest 568/0 (1 skipped) · mutation sweep 44/0 · compat 78/78 含 G9 x4=1 与 E3 D3 断言）· tests/w18/r1-runbook-drill.log（6 步演练：dirty-tree guard REJECTED→强制捕获→3 MB blob 归零→commit-map 3 对 remap→log 可追）| 覆盖 5/5 criteria
- Decisions: 3 auto-decisions → tests/decisions.md（D-W18-3 spec-test-conflict E3 断言重定 · D-W18-4 bootstrap 豁免覆盖 stale · D-W18-5 测试落点/start.sh 并线）
- test-change: tests/plugin_compat_test.mjs — 追加 D10c（bootstrap 窗口 gate 侧 advisory 注记）、D12/D12b/D12c（audit 插件 args.path 形态 tests/ 豁免 + src 仍拦，覆盖复审 Critical #1）、D11 扩到 gate+audit 双插件一致性
- test-change: tests/test_assert_groups.py — 追加 S49（partial seal：删 manifest 不清除封印义务）、S50-S52（--final 永远执行 · 无冒号 `PASS` 照样激活封印义务）；S46 补 `rc==0` 断言（只加强不放松）
- iter 3 FAIL (A4.9 复审轮 1): criteria #2 #4 #5 | diagnosis: G2 只修了 gate 插件，audit 插件在真实 args.path 形态下 RED-latch 证据修复路径仍死锁（复审 PoC 实证）；bootstrap 可被"永不记 PASS"永久关闭且 --final 媒体规则被降级；三态文档表漏 partial/tamper 态 | changed: vibeweaver-audit.js, scripts/assert_artifacts.py, vibeweaver-gate.js, COMPLETION_GATE.md, tests/plugin_compat_test.mjs, tests/test_assert_groups.py | 复审: tests/review_package.md 双对抗 subagent verdict（Critical 2 · Important 2 · Minor 4，全部逐条裁定）
- iter 4 PASS: criteria #1 #2 #3 #4 #5 | evidence: tests/w18/iter5-build.log（selftest 568/0 (1 skipped) · sweep 44/0 · compat 82/82 · assert groups 54/54）；scoped re-review tests/review_package_w18r2.md：两 Critical + Important #4 判 closed | 覆盖 5/5 criteria
- iter 5 FAIL (scoped re-review): criteria #1 #5 | diagnosis: S50 fixture 缺 `Baseline verified GREEN` 使媒体规则非唯一失败源（pin 空转，pre-fix 也过）；audit 插件 isTestDirPath 仍大小写折叠、writePathFromArgs 自称与 gate 同契约却行为不一致 | changed: tests/test_assert_groups.py, vibeweaver-audit.js, vibeweaver-gate.js
- iter 6 PASS: criteria #1 #2 #3 #4 #5 | evidence: tests/w18/iter6-build.log（568/0 · 44/0 · 82/82 · 56/56）；revert-and-fail tests/w18/red-revert-assert-r2.log（S49-S52 在 8aceebc 中间态全 FAIL → 修复后全 PASS）| 覆盖 5/5 criteria
- review-adjudication: Critical #1（audit 插件 args.path 死锁）与 #2（bootstrap off-switch：`--final` 永远执行 + `PASS\b` 文法）已修复并由 D12*/S50-S52 钉住；Important（--final 媒体降级 · partial/tamper 漂移）已修复；Minor（case-fold 豁免 · 混合参数形态 fail-closed · WARN 解析鲁棒 · D11 双插件 · S46 rc · acceptance 计数措辞 · runbook 步骤顺序）已修；移交项见 D-W18-6（releaseStale new-task 归因，波外既有缺口）
- Decisions: 3 auto-decisions → tests/decisions.md（D-W18-3/4/5）；1 裁定移交 → D-W18-6
- working-note: created → updated → distilled → deleted (A7.15)
- final-fresh-run: 交付树 fresh run 全绿 — selftest 568/0 (1 skipped) · mutation sweep 44/0 · compat 82/82 · assert groups 56/56（tests/w18/final-fresh-build.log）
- assert-run: assert_artifacts.py: all 29 checks pass (exit 0) — tests/w18/final-assert.log
- final-run: --existing --final — pass=29/fail=0
- re-seal: 绿测后重封 — test baseline 48 file(s) + code_fingerprint 记录（web 媒体/trace 0 件；tests/*.log 绑定属 G5 第 2 批范围）
- secrets: scan_secrets.py --all . clean（tests/w18/final-scan-secrets.log）
- fcv: fresh-context verify pass — 复跑 selftest 568/0 · sweep 44/0 · compat 82/82 · assert groups 56/56 · assert --final 29/0 · scan clean，10 项声明逐条核验（SKILL.md 48988B · canonical 一致 · evidence_seal.py 波内未动）| tests/fcv_report.md

## W18-sync+D1+batch2/3 — 同步 · 输出顺序唯一化 · 批 2/3 全部收口（2026-10-21，同日第二波）

- class: CODE — basis: assert_artifacts.py / vibeweaver-audit.js / vibeweaver-gate.js / evidence_seal.py 逻辑变更（分支/校验/状态机），按 §V11.2 首 match CODE
- wave-base: f0e5de7
- Mode: AUTO | Lane: L (≥3 文件 · 行为语义 · 复审必然触发) | Verifier: direct read (non-web)
- Baseline verified GREEN — `bash script/linux/project_build.sh` @ f0e5de7：selftest 571/0 (1 skipped) · sweep 44/0 · compat 82/82 · assert groups 68/68（tests/w18sync/baseline-build.log 缺失 → 记于 tests/w18sync/iter1-build.log 同型重跑）
- sync: dev→system/open-source/repo 24 项 payload + aux + 插件对字节一致（propagate fail=0）；`tests/sync_skill.py --fix` 重钉 eval fn_latest + 3 个 compliance task canonical/pin（commit 782744a）；repo verify_skill 10/10 + selftest 13/13 + push 7ab96b4（W18 batch1 payload + 双语 changelog）；dsh 派生副本手移植见末条
- D1: 完成输出顺序唯一化 — COMPLETION_GATE §A4.4 权威顺序块 + SKILL/REFERENCE 引用化 + T39 断言（三处无第二顺序表述）
- test-change: tests/test_assert_groups.py — 新增 S53-S66（G3 棘轮四态 · G4 claim-lint/ack/当前块 · G6 wave-base · R3 纯删除 · T2 hint · G5 sha lint/seal 绑定/record 工具 · S66 基线抬高锚定）；S29/S53 fixture 加 re-anchor（41 MiB patch 触发 16 MiB diff 上限的 fixture 现代化，断言未动）
- test-change: scripts/audit_selftest.mjs — T29b/T31/T32b acceptance 重写改经 hook 归因（D-W18-6 语义），新增 T29c/T29d（外会话/bash 触碰不放闩）与 T39 D1 顺序唯一断言
- iter 1 FAIL (RED): criteria #1 #2 #3 #4 | diagnosis: 批 2/3 特性全缺（--record-debt exit 2 · claim-ack 无抑制 · wave-base 无锚点 · 删除计入波上限 · record 工具不存在）| RED 证据: tests/test_assert_groups.py S53-S65 首跑 FAIL/崩溃
- iter 2 PASS: criteria #1 #2 #3 #4 | evidence: tests/w18sync/iter1-build.log（571/0 · 44/0 · 82/82 · 70/70）
- iter 3 FAIL (A4.9 双对抗复审轮 1): criteria #1 #2 #4 #5 | diagnosis: - wave-base 未校验致 14/15/16/C1 可被一行日志致盲 · 棘轮硬顶可被手改 debt_baseline 绕过 · G5 seal 自引用死锁 · arm clobber/相对路径死锁 · T1 缺 log 段 · COVER 表插断 rows 表 | 复审: tests/review_package_w18b2.md（Critical 3 · Important 若干，全部逐条裁定）
- iter 4 PASS: criteria #1 #2 #3 #4 #5 | evidence: tests/w18sync/iter4-build.log（571/0 · 44/0 · 82/82 · 71/71 含 S66）；scoped re-review 轮 2 判定项闭合 + 2 新问题（HEAD 锚点 · 块末行切片）
- iter 5 FAIL (scoped r2): criteria #1 #4 | diagnosis: merge-base --is-ancestor 允许锚点==HEAD（波取样为空致盲）；wave_base 切片 [a-1:b-1] 丢块末行锚点 | changed: scripts/assert_artifacts.py, vibeweaver-audit.js, COMPLETION_GATE.md, ENGINEERING_STD.md
- iter 6 PASS: criteria #1 #2 #3 #4 #5 | evidence: tests/w18sync/iter4-build.log 后同码全绿重跑 + PoC 自证（bogus-sha/HEAD 锚点 fail-closed · 块末行锚点识别）| 覆盖 5/5 criteria
- review-adjudication: 轮 1 三 Critical（wave-base fail-closed + 严格祖先 · 棘轮 git 锚定/抬高拒绝/未跟踪不豁免硬顶 · seal SELF_REFS 排除）+ 死锁/合规项全修；轮 2 新发现（HEAD 锚点 · 切片 off-by-one）已修并 PoC 自证；残余（提交级手改 debt_baseline 可过——review 可见、信任边界内）记 memory
- Decisions: 3 auto-decisions → tests/decisions.md（D-W18-6b 实施反转 · D-W18-7 G4 规格矛盾按验收裁定 · D-W18-8 复审裁定）
- working-note: created → updated → distilled into memory/fix_w18_batch2_semantics.md → deleted (A7.15)

## W18-residual — 残余两项闭合：债棘轮跨 git 历史 + claim-ack 内容绑定（2026-10-21，同日第三波）

- class: CODE — basis: scripts/assert_artifacts.py 逻辑变更（历史遍历/内容绑定校验），首 match CODE
- wave-base: a03c28d
- Mode: AUTO | Lane: M | Verifier: direct read (non-web)
- Baseline verified GREEN — `bash script/linux/project_build.sh` @ a03c28d：571/0 (1 skipped) · 44/0 · 82/82 · 71/71（tests/w18sync/r3-baseline.log）
- test-change: tests/test_assert_groups.py — S58 ack 格式升级为引文绑定（断言语义不变：有理由放行/裸 ack 拦截）；新增 S69（引文不匹配→不抑制+stale）· S70（55 次 churn 提交不可驱逐首锚）· S67（提交级抬高→FAIL）
- iter 1 FAIL (RED): criteria #1 #2 | diagnosis: 提交级抬高 `recorded` 后 rc=0（棘轮只对 HEAD 比较）；claim-ack 行号漂移静默改挂（无内容绑定）| RED 证据: S67 rc=0 · S68 stale=False
- iter 2 FAIL (scoped 复审): criteria #1 #2 | diagnosis: 50 修订窗口可被 49 次 cosmetic 提交驱逐低锚（R1b 洗白）；ack 引文仅验"是声明行"仍可 claim→claim 改挂（R2）| 复审: tests/review_package_w18r3.md
- iter 3 FAIL: criterion #2 | diagnosis: stale_claim_acks 仍写旧单值形态致解包 TypeError（修复自身引入的回归）| changed: scripts/assert_artifacts.py
- iter 4 PASS: criteria #1 #2 | evidence: tests/w18sync/r3-final.log（571/0 · 44/0 · 82/82 · 75/75）；S67/S69/S70 全绿 | 覆盖 2/2 criteria
- review-adjudication: R1b 窗口洗白（首修订锚定入 min）与 R2 claim→claim 改挂（强制引文绑定）已修并 S69/S70 pin；R4 fence/span 盲区一并修（fence 外/块外目标判 stale）；R8/R14b（采纳点/reset-squash/改名边界）按信任边界记录于 memory
- working-note: na (单线任务，无多迭代假设账本)
