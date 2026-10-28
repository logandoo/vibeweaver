# vibeweaver 变更记录

本文件保存 vibeweaver 的完整修改历史，按日期倒序。README 只保留当前能力说明，历史条目的表述保持原样，不做改写。

2026-08-19 渐进式披露重构前的原版（79.5KB 单文件）备份于 `/tmp/vibeweaver-backup-20260819/`。

---

## 2026-10-28 评测清偿：清零重狩猎三方向筛查（零存活）+ 审计修复

### 评测（ADR D-W2ISO-10 裁决：清零重狩猎）

- 判据 #74 原文重狩（hidden 只测功能、失败为功能面）：10 候选 × 3 个方向（毒测试冲突 / F1 硬陷阱 / 并发不变量+自定义方言），35 个 bare runs（biklimax/qwen3.8_27b）
- 结果：31 个原位 hidden 全过 + 1 个重建全过；4 个异常 run 三个定性非功能面（端点 DNS、会话空转、exit-code 假 fail）+ globmatch-s0 有未判交付物不可恢复（即便计为失败亦仅 1/4 挂）→ **零已判定功能失败、零存活题**；#74 池数量目标未达，三方向 stall 后停止，处置权交用户
- F9 主发现：功能面饱和延伸到隐藏硬约束（边界含等/容量封顶/失败原子性）、并发不变量（check-then-act）、自定义方言状态机；裸模型主动识破并改写毒测试（轨迹实录在 §11）
- 并发夹具按 F1 flakiness 政策硬化：纯统计压测改 **opcode 级让渡确定性交错**，判杀 6/6 稳定；selfcheck 三向门 28/28
- 测量发现（UNFINISHED 候选）：harness 在 agent 进程非零退出时跳过 hidden 判 fail，进程失败混同行为失败（3/35）

### 审计清偿（docs/AUDIT_2026-10-28_eval_discrimination.md）

- 跨模型×逐题共同失败矩阵入 `vibeweaver-eval/REPORT.md` 附录 A：判别题 11/16、共同失败 1、天花板 4——「饱和」定性为题集天花板而非共同失败
- `vibeweaver-eval/REPORT.md` pytest-6116 矛盾修正（qwen3.6 mini 三臂实为解出）；`comp_summary.json` 刷至 180min 重跑口径（full_forced 3/9）
- README EN/ZH：统计口径脚注（run 独立假设 / 任务级 p=0.10 / 0/3 vs 3/3）+「怎么读这些表」代际导读
- W2 证据链（`docs/EVAL_G3_PILOT_REPORT.md` + `tests/eval/`）发布上架，README「Full data」悬空指针消除

### 验证

- `tests/eval/lab/selfcheck.py` 28/28（三向门）· 判杀稳定性 6/6 连跑 · 批 1/2 复判 26/26 功能通过
- `node scripts/audit_selftest.mjs` 571/1（T39 预算债既有）· `node scripts/mutation_sweep.mjs` 44/0 · `node tests/plugin_compat_test.mjs` 82/82

## 2026-10-26 发布：w19.0（W2 eval 出口 + 产品形态验证）

### 发布内容

- **W2 eval 基础设施**：`eval_run.py`（隔离 harness、进程组超时 kill、gate 自噪声豁免）、`eval_pilot.py`（战役编排）、`eval_report.py`（Wilson CI）、`eval_power.py`（MDE）、`gate_events.py`（拦截事件解析）
- **G3 场景集**：11 任务（8 能力 + 3 compliance 判别）+ `selfcheck.py` 三向有效性门 18/18
- **V2 产品形态臂** `full_deployed`：skill payload + gate/audit 插件进高温 HOME + `setup_files` 激活标记
- **compliance 判别战役**：bare 0/9 vs core 2/9（文本层，§7）；产品形态 bare 0/9 vs full_deployed 9/9（§8/§9）
- **F7 headless 降级条款**（§A7.7.1）：无人值守环境下 trust-tier 确认降级为 `awaiting decision` 记账
- **评分器修复**：D-W2ISO-9 四次形态税修复（单复数/×x/FAIL[C]/AC#），红队夹具钉住语义变体
- **LICENSE**：MIT（用户确认）+ NOTICE + `license_check.py` 0 fail/0 warn

### 验证

- `node scripts/audit_selftest.mjs` 571/0（1 skipped）· `node scripts/mutation_sweep.mjs` 44/0 · `node tests/plugin_compat_test.mjs` 82/82
- `python3 -m unittest discover -s tests -p 'test_*.py'` 95/95 · `bash script/linux/project_build.sh` 75/75
- `tests/eval/lab/selfcheck.py` 18/18 · `tests/assert_artifacts.py --final` 36/36 · `scripts/evidence_seal.py --check` VERIFIED
- 产品形态评测：bare 0/9 vs full_deployed 9/9（CI [0.70, 1.0]，directional）；gate 拦截 28 次、9/9 run 被拦

### 已知边界

- W2-T15（13 规则 TDD）未做；W2-T16（独立复现）单操作者，无独立复现
- 显著性扩样方案待启动（6 题 × 5 seeds × 2 臂 = 60 runs ≈ 15.5h）
- headless × trust-tier 确认语义（F7）已修，历史 1/9 发生率

---

## 2026-10-19 修改：W13 v2 显式提示 + seal verifier 清理

### 来源

W12 收口后仍有两项可继续闭合：v2 永远 debt-only（显式 euphemism 也不提示），以及一个与 `evidence_seal.py` 半 parity 的 JS seal verifier（既不是完成证据，又容易误判）。

### 修改

- **v2 显式提示**：v2 宿主有 `session.prompt` 时，显式 euphemism/truncation 触发一条 corrective prompt；v2 positive（静默停止）一律 journal debt（即使有 DOC/gate/paused/awaiting，因为这些在 v2 都是模型自写、不可验证）。模型自写的 gate/paused 不再压制显式触发。
- **prompt 失败不烧预算**：`onStopPrompt` 返回 false/throw 时回滚 intervention 计数并 journal `prompt-failed` debt。
- **删除 JS seal verifier**：`verifyEvidenceManifest`/`waveCodeFingerprint`/T44 删除；seal 完整性只由外部 `evidence_seal.py --check` 负责，`- seal:` 单独不是完成证据（D-W12-2）。
- **测试**：T27c117-121（v2 decision 语义）、T27e104-106（v2 DOC debt、gate 不压制 explicit、prompt 失败 debt）；T27e37/56 改为“v2 gate-only 仍 journal debt”；移除 T44a-c。

### 验证

`node scripts/audit_selftest.mjs` 568/0（1 skipped）· `node scripts/mutation_sweep.mjs` 44/0 · compat 69/71（E3/G9）· assert 29/0 · seal VERIFIED · FCV pass。

---

## 2026-10-19 修改：W12 遗留项清空（P2-4 / P2-6 / seal / repo）

### 来源

W11 交付后列出的 8 项遗留：paused_state/Class-E 可伪造、tool-frequency 默认覆盖损失、seal-only 不支持、typed assert 残余、v2 debt-only、role-less v1 mid-task idle、分类器/shell 边界、mutation sweep 无 W11 变体，以及 repo 未发布。

### 修改

- **P2-6 paused/Class-E 可见化**：`tests/paused_state.md` 必须满足 §3.4 字段（gate/question/options≥2/default-if-continue/state）**且最后一条 assistant 消息含 `[PAUSED]`** 才 whitelist；`Class-E` 必须同时有 “approved by user” 记录、最后 user 消息的批准线索、assistant 的 Class-E 声明。隐藏文件不再能自我豁免。
- **P2-4 高频工具 warn-only 层**：默认 ≥120 次变参同工具调用写一条 advisory 日志（每 session 一次），不 abort、不 prompt；`loopGuardToolFrequencyMin` 显式配置仍恢复旧 abort 行为，`loopGuardToolFrequencyWarnMin` 可调 warn 阈值（最小 20）。
- **seal 边界**：不发布 JS seal verifier（半 parity 比没有更危险；D-W12-2）；seal 完整性由外部 `evidence_seal.py --check` 负责，`- seal:` 单独**不构成完成证据**。完成仍要求 assert-run 或绑定日志。
- **分类器/shell 边界**：`output/app.html`、`src/report.json`、`Makefile`、`Dockerfile`、`src/config.json`、`db/migrate.sql` 均按 code；`output/report.html`、`data.json`、`table.json` 为 report/data；bash 增加 heredoc 首行、`foo2>`、`tee`、`cp/mv -t/--target-directory/-rt`。
- **mutation sweep**：新增 3 个 W11/W12 分类器变体（output HTML / src report JSON / Makefile → C18 BAD），sweep 44/0。
- **repo 发布**：payload + 双语 CHANGELOG 同步，repo commit + push（commit 见交付输出）。

### 验证

`node scripts/audit_selftest.mjs` 563/0（1 skipped）· `node scripts/mutation_sweep.mjs` 44/0 · compat 69/71（E3/G9 pre-existing）· assert 30/0 · seal VERIFIED · 四副本 cmp clean · FCV pass。

---

## 2026-10-19 修改：W11 stop-guard 盲区收口（P0-1..P0-5 / P1-1..P1-5）

### 来源

`docs/HANDOFF_W10_BLINDSPOTS_20261019.md` 只读复查：W10 主路径已绿，但仍有可被模型主动利用的 false negative——自报 `final-run`、同 session 旧任务豁免、提前 gate、伪造 `Class: DOC`、只读/等待判定的引号与问号漏洞、messageID churn 重置上限、无 input 写入与 v2 失败写入的证据口径。

### 修改

- **`final-run` 可信化**：完成证据必须出现在**当前 task block 的最后一条 `final-run`**，并且附近要有 `assert_artifacts.py: all N checks pass` 原文，或绑定一个本 turn 内生成的 `log=<path>` 且该文件内容含 assert 输出。仅手写 final-run 行不再算完成；`- seal:` 单独不再构成完成证据（manifest 可被模型写；D-W11-4），B12 同步收紧。
- **task boundary**：完成/class 证据只从当前 user turn 之后追加的日志切片、且只从当前 task block 读取；同 turn 的更早 Task 块或 trailing Notes 的旧 final-run 不能豁免新任务。
- **gate 顺序**：`[Verification Gate]` 的首次出现 seq 必须 ≥ 最后一次 task-file write 的 seq（delta 只扫 18 字符重叠，cumulative 只扫增长尾段）；中途 gate 后继续写代码不白名单，写到一半后最后一条消息补 gate 仍通过。
- **read-only 精度**：先剥离引号内历史引述；长 brief 扫首尾 8KB；肯定式实现动词（句首/序列词后）覆盖只读短语，逐 match 处理否定；文档动作（update the report / add findings / create a test plan / build the project）不算实现。
- **awaiting-user 精度**：裸 `?` 不再豁免；问句必须含第二人称/请求/决策线索（`you`、`请`、`需要`、`should I` 等），proceed/continue 必须整句或带线索。`Done. Continue?`、`All done. Continue?`、`工作完成。继续吗？` 不豁免，`Should I proceed?` 豁免。
- **ceiling churn**：user 边界始终重置；5 秒内 ≥4 次 messageID 变化视为 churn，不重置 256KB 可见文本上限与 1MB reasoning backstop。
- **write evidence**：v1 completed write 无 `input.filePath` 时记 unknown task write；v1 bash redirect 走 quote-aware 解析（heredoc 首行、`2>` vs `foo2>`、`tee`、`cp/mv` 目标目录）；v2 写入证据改到 `execute.after` 成功回调，按 call id 关联，blocked/failed write 不再污染 debt。
- **Class DOC 交叉校验**：`Class: DOC` 只在本 turn 没有 code/config 写入时生效；code/config 用扩展名而不是 "非 prose" 判断（`src/config.json`、`db/migrate.sql`、`output/app.html` 都算 code，report/data 产物除外）；伪造 DOC + code 写会触发 positive prompt。
- **测试**：新增 T27c41-c86、T27e22-e70、T24l churn 用例；T27e15 从“早 gate 不 prompt”翻转为正确的“早 gate + 后写代码 → prompt”；selftest 495/0（1 skipped），mutation sweep 41/0。

### 验证

`node scripts/audit_selftest.mjs` 404/0（1 skipped）· `node scripts/mutation_sweep.mjs` 41/0 · `tests/plugin_compat_test.mjs` 69/71（E3/G9 pre-existing，fail-set 不变）· `python3 tests/assert_artifacts.py --existing --final` 通过 · 四副本 `cmp` clean · A4.9 双评审 + scoped re-review + FCV 通过（`tests/w11/`）。

---

## 2026-10-19 修改：W10 stop-guard / loop-guard 误杀硬化

### 来源

用户实测：上一版 silent-stop 正向判定与 loop-guard 在强模型上误停止/误杀。联网 SOTA 对照：OpenHands `StuckDetector`（action-observation cycle，不是工具名频率）、LangChain 论坛（同工具+同参+同结果作为通用 loop 规则是 design flaw）、Strands `DebounceHook`（同参重复只 block 单次调用）、IAL-Scan（bound coverage 而非任意 repetition）、Claude Code hooks（Stop 是 strong nudge，PreToolUse 才是硬停）。

### 修改

- **stop-guard 正向判定收窄**：只在 `Class: CODE`（或未知 class 但写入了非证据任务文件）时启用；`Class: DOC`、用户限定只读（"仅评估，不修改" / read-only audit）、以及 awaiting-user（句号结尾的 "please confirm"/"请确认"，不再只认 `?`）都白名单。证据路径（`tests/`、`docs/`、`memory/`、报告）不再被当成"模型写到一半停了"。
- **完成判定容错**：`[Verification Gate]` 改为在当前 user turn 的 assistant 消息中查找（拆分最终消息不再误判）；`final-run` 必须 `pass≥1/fail=0`（`pass=0` 不算完成；W11 起还必须绑定真实 assert 输出，见下条 W11 记录）。
- **纠正文给出"已完成"出口**：如果任务其实已完成，明确要求补发 gate line + final-run，禁止伪造更多工作；等待用户时用直接问句或 PAUSED，不再把模型逼进"继续是造假、停是非法"的死角。
- **runaway 上限**：64KB→256KB（`loopGuardTurnCeilingBytes`，最小 64KB），只计可见文本、不计 reasoning；reasoning 保留独立 1MB 高上限（`loopGuardReasoningCeilingBytes`，最小 256KB），避免非周期推理失控。无 messageID 的宿主在观察到的 user 边界重置，不再 per-session 累计。纠正文从 "STOP emitting" 改为 checkpoint/continue。
- **tool-frequency 改为 opt-in**：默认关闭；只有显式配置 `loopGuardToolFrequencyMin`（整数≥4）才启用。工具名频率不是 loop 信号，合法 bulk work 不再被杀。`identical-tool-run`（同工具+同 canonical args ≥4）保持默认。
- **测试**：新增 T27c18-c40（read-only/awaiting/decision）、T27e12-e21（DOC/read-only/awaiting/split gate/pass=0/positive control）、T24l 256KB + reasoning 不计数、T35d/d2 opt-in；selftest 383/0（W11 前的最终树）。

### 验证

`node scripts/audit_selftest.mjs` 383/0（1 skipped）· `node scripts/mutation_sweep.mjs` 41/0 · `tests/plugin_compat_test.mjs` 69/71（E3/G9 pre-existing，fail-set 不变）。本轮只读 SOTA 检索来源见 `memory/fix_loopguard_false_positives_w10.md`。

---

## 2026-10-19 修改：W9 共享脚本误报 + canonical 同步

### 来源

W9 handoff（`docs/PLAN_vibeweaver_payload_fixes_20261019.md`）：eval 侧暴露 `scan_secrets.py` 误报/自噬与 canonical 副本漂移；只修共享 payload 脚本，不动 eval sandbox/W7/W8。

### 修改

- **`scripts/scan_secrets.py`**：保留 `pwd` 关键字（`db_pwd`/`MYSQL_PWD` 等真实密码缩写不再漏检）；路径值仅对路径型 key（`pwd|path|dir|home|cwd|root|file`）放行，`PWD: /var/...` 不再误报。`- secret-approved:` 审批元数据（仅跳过 generic 规则，命名规则仍扫描）、`*_ALPHABET/_CHARSET` 常量、引用表达式（call/index 或 `os.`/`process.`/`config.`/`self.` 根）不再误报；文本与 `--diff` 共用 `match_line`。
- **`scripts/assert_artifacts.py` group 14**：同一套语义（key 列表与 `scan_secrets.py` 完全一致、审批行/常量/路径/引用白名单）；新增 S37-S44 负/正样本。
- **`tests/sync_skill.py`（新增，dev-only）**：dev `scripts/`/`tests/` + installed + eval snapshot + 3 个 task canonical + `task.json > compliance.canonical_assert_sha` 的 fail-closed 校验，`--fix` 同步；`tests/test_sync_skill.py` 7/7（含“不发明缺失树”与 `--allow-missing-eval` 覆盖 task canonical 的回归）。
- **测试**：`test_scan_secrets.py` +13 TP/FP 向量 + `--diff` 场景 + pytest 入口；`test_assert_groups.py` +S37-S44 + pytest 入口。P1 gate `-S -I` 按 D-W9-3 延期；`SKILL.md` 保持 48,999B（本波未改）。

### 验证

- `scan_secrets.py --all .` / `--diff HEAD` clean；`test_scan_secrets.py` 57/57；`test_assert_groups.py` 48/48；pytest 3 passed；sync checker 7 assert + 3 scan copies + 3 pins（checker 7/7）；audit selftest 342/0；`mm_probe --selftest` PASS。
- 基线：compat 69/71（E3/G9 为 clean-HEAD 既存顺序敏感失败）；陈旧 `/tmp/tests` symlink 已移走（环境修复，非代码）。

---


### 来源

用户 2026-10-14「遗留项清掉」（D-uif-1 记录的 ③/④）：比较测量能力探针（TableTest/Tunnel Vision 依据见上波）+ 图像参考侧轻量区域提取（补 T1 ref-is-image 路径）。

### 修改

- **`scripts/mm_probe.py` 增 comparative 子探针**：`--compare-generate`（双面板单处差异：moved/covered/color/added/removed × 四形状 × 随机颜色，盐化哈希 ground truth）→ 报告 `<variant> <shape>` → `--compare-check`（正解 0 / 错解 1 / 枚举外 2）；FAIL = 记录「比较判断不可靠」，差异定位改用 T1/T2 簇（APPENDIX §A12 校准段）。selftest 增渲染差量/唯一解/无泄题不变量。
- **`scripts/ui_fidelity.py` 增 `refboxes` 子命令**：图像参考 → 候选区域（auto/--bg 背景、--tol、8 连通 + gap 合并、min-area 过滤）→ `ui-refboxes-*.json`（元素 schema，可作 boxes 的 REF）+ 叠加预览 `*.png`；selftest 19→23。**TESTING_PROTOCOLS §A4.1.2/Step 0a** 接线并以 T0/T2/T3 微缩对冲（终值 44,972B，仍 <45,000）。
- **APPENDIX §A12**：ref-is-image 路径改走 refboxes；新增 comparative 探针校准段。SKILL.md 不动；payload 仍 23；installers/verify 零改动。
- **repo 测试**：新增 `tests/test_mm_probe.py`（selftest/唯一解/无泄题/退出码/全变体）+ `test_ui_fidelity.py` 增 refboxes/alpha/校验用例 → 套件 38→44，修复轮（3 轮评审）再增至 49。

### 验证

- dev：mmp selftest PASS（我按协议读图 = brute-force 真值 removed square）；ui selftest 23；E2E 坐标与已知几何一致（tests/uif2-*.log · tests/uif2-e2e/）；audit 225/0/1 + sweep 41/41 + assert exit 0；四副本 diff -q 全等。
- repo：verify exit 0；unittest 49/49；A4.9 双对抗评审 + 2 轮 scoped + FCV 在档。

---

## 2026-10-14 修改：拷贝保真测量层 —— §A4.1.2 + scripts/ui_fidelity.py

### 来源

用户 2026-10-14「UI 拷贝开发错位/遮盖/尺寸不一致且 agent 无法发现」的 SOTA 评估（tests/verification_log.md DOC 任务块，六类 20+ 候选）：pixelmatch/odiff/SSIM 40 站基准、Boxy/LayoutLens/visual-diff 级联、claude-copy/mirrorframe/visual-parity、Design2Code/OmniParser、TableTest/VLMs Tunnel Vision 等一致结论——**measure-then-judge**：几何/像素必须由仪器认证；VLM 的比较感知/空间测量恰是已证伪的弱区，自评几何=结构性缺陷。

### 修改

- **TESTING_PROTOCOLS.md 新增 §A4.1.2 Design-Copy Fidelity（measure-then-judge）**：T0 同条件采集（同视口/DPR、冻结动画、等字体、hide caret、mask 动态区）→ T1 几何/遮挡（boxes：Δ尺寸/位置、missing/extra、非包含重叠、occluded_by 命中采样）→ T2 像素（pixelmatch v5.3.0 移植：YIQ colorDelta + AA 检测，diff 图 + 8 连通聚类）→ T3 语义仍由 §A4.1.1 VLM 判定；**几何类标准只由 T1/T2 认证，VLM 永不认证几何**。verifier 模式不变（T1/T2 仪器化，无需媒体模型——direct read 任务同样获得完整保真验证）。
- **scripts/ui_fidelity.py（新增，纯 stdlib）**：`diff`（PNG codec + pixelmatch 移植 + 聚类 + 尺寸失配 exit 3 / --allow-dim-mismatch 公共裁剪）与 `boxes`（逐元素 Δ、missing/extra、非包含重叠、occlusion 判定）子命令；`--selftest` 19 检查（RED 先行：NotImplementedError 留档；含尺寸失配合同与 AA/色度差分 pin）。
- **APPENDIX.md**：§A12 拷贝保真模板（T0 Playwright 采集 + BOX_DUMP_JS 含 elementsFromPoint 遮挡采样 + T1/T2 命令与引用规范）；§A10（A4.7b 工作流模板自 TP 迁入）。
- **SKILL.md**：§A4.1 摘要加 item 7 指针，净零编辑 48,992→48,972B（T11 双查实证）；TESTING_PROTOCOLS 瘦身对冲 44,993→44977B（<45,000 散文预算）。
- **install.sh/.bat**：安装 `scripts/ui_fidelity.py`；repo `verify_skill.py` PAYLOAD_FILES 22→23 + installer 双检查（RED 先行：verify exit 1 → sync → exit 0）。
- **repo tests/test_ui_fidelity.py**：6 项 unittest（selftest · identical · block diff+cluster · 尺寸失配 · allow-dim · boxes 规则）→ 套件 26→32。

### 验证

- dev：`--selftest` 17 checks；真实图 E2E 六连（退出码 0/1/3 语义、probe↔probe 聚类、boxes 五类缺陷全检出）（tests/uif-*.log · tests/uif-e2e/）；audit_selftest 225/0/1 + mutation_sweep 41/41 零退化；assert_artifacts --final exit 0。
- repo：verify_skill exit 0（23 文件 payload）；unittest 32/32。
- 四副本全量 diff -q 全等；A4.9 双对抗评审 + FCV 记录在 tests/。

---

## 2026-10-13 修改：残留波② —— release 日志 append-only 渲染 + T27 夹具对齐

### 来源

2026-10-13b 评审 R2 的 Important：`gate_audit.md`「Stale RED releases」段宣称「never delete」，但 `RELEASES_CAP=5` 的 FIFO 渲染会把最旧行从文件里挤掉（state 有界连坐了渲染）；另 R1 点名 T27 stop-guard 夹具的 FAIL 日志缺 `- working-note:` 行（latent）。

### 修改

- **core 新增 `mergeReleaseLines(existingText, stateLines)`（纯函数）**：解析前一渲染的 releases 段 → 与 state 行 union → 按行去重 → ISO 字典序排序。state 保持有界（RELEASES_CAP 不变），渲染文件成为真正的 append-only 审计轨迹。
- **audit.js 接线**：写报告前读取前一 `tests/gate_audit.md`，footer = merge(prior, state)。
- **T27 夹具对齐**：5 处 stop-guard 夹具日志补 `- working-note: created (fixture — active task)`（防 group-20 规则上提时翻车）。
- **T33 六 pin**：union / dedupe / sort / 区段不泄漏 + packet 引用头不遮蔽（评审 R1 抓出的首次匹配遮蔽）+ 集成（planted 旧行经真实 release 周期保留且恰一份、新 state 行同时在场）。
- **README EN/ZH**：计数 219→225、套件列表 T29–T32→T29–T33。

### 验证

- RED 先行：T33 pins 先跑 → `TypeError: mergeReleaseLines is not a function`（留档）；实现后 GREEN `225/0/1`（含 T33e/T33f）；mutation_sweep 41/41；四副本 + `~/.config/opencode/plugins/` diff 全等（活插件待 opencode 重启生效）。

---

## 2026-10-13 修改：GitHub 文档债清偿波（双语 README/CHANGELOG · 守卫/安装器补强 · dev 回填）

### 来源

2026-10-13 C4 只读审计（docs/AUDIT_2026-10-13_github_doc_freshness.md）：GitHub payload 已最新，但双语 README 停在 f636659（10-09）、双语 CHANGELOG 缺 loop-guard 两波条目；dev SoT 缺 scan_secrets.py/ab；repo 守卫清单缺 3 条目。修复中另发现：installers 自 wave13 起从未安装 VERIFICATION_UPGRADES.md（payload 有，install.sh/.bat 与 INSTALLED_DOCS 均缺）。

### 修改

- **双语 README（repo）**：工作记忆 bullet 补 wave21/24 确定性记忆投递（压缩镜像/恢复注入/首写 cue/memoryDeliveries/快照）；loop-guard bullet 与执行层段落补 reasoning 通道、counter 墙（≥16 严格 +1）、64KB turn 上限、标点墙（≥2KB）、尾噪归一；计数 166→219；assert 组 18→19；Files 表补 scan_secrets.py/backlog_check.py 两行。
- **双语 CHANGELOG（repo）**：新增 2026-10-10 loop-guard 加固条目（EN/ZH 对照，含 T24k/T24l/T24m、mutation 41/41、166→219、两波 dual+scoped 评审）。
- **守卫/安装器（repo）**：verify_skill PAYLOAD_FILES + INSTALLED_DOCS 补 VERIFICATION_UPGRADES.md / backlog_check.py / scan_secrets.py 与 installer 检查（RED 先行：先见 4 失败再修）；install.sh/.bat 补装 VERIFICATION_UPGRADES.md 与 scripts/scan_secrets.py（wave13 起漏装缺陷）。
- **dev 回填**：scripts/scan_secrets.py + scripts/ab/{run,obj_eval}.mjs 自 repo payload 回填（sha256 全等 + 冒烟）；scripts/tests/ 无引用不回填（残留项）；run.mjs:92 `hard-gate-token` 选择器触发 group-14 误报 → `vw-approved` 内联 + 日志 `- secret-approved:` 配对（四副本同步）。
- **COMPLETION_GATE.md（payload）**：AUDIT 段 loop-guard 描述补 reasoning 通道一句、形状计数更正（Three→Five）。
- **四副本同步**：install.sh/.bat、COMPLETION_GATE.md、scripts/ab/{run,obj_eval}.mjs、scripts/scan_secrets.py 在 dev/repo/system/open-source 逐文件 diff -q 全等；OSS 侧顺带补齐 ab/ 与 scan_secrets。

### 验证

- repo：verify_skill.py exit 0（9 checks，含新守卫）；unittest 26/26；audit_selftest 219/6/1（6 既存按 D-lg-1 隔离，无新增失败）。
- dev：assert_artifacts.py --final --existing → 49/49（两轮 RED→GREEN + secret-approved 配对留证）。

---

## 2026-10-12 修改：wave21 —— 确定性记忆投递（gate 插件化 working_note）

### 来源

「Delivery, Not Storage」（arXiv:2607.20972）：预置知识库下模型主动查阅记忆 114 轮 0 次；确定性投递在 138/138 次压缩-恢复全部送达。Graepel 认知状态账本（MIT Tech Review 2026-10-02）。两者共同结论：可靠记忆通道必须由 harness 在正确的生命周期时刻**确定性投递**，不能依赖模型自觉。验证基线：waves16-19 已有 working_note（§A7.15 账本）+ cue triggers（§A7.16 编辑时刻投递），但**压缩边界与会话启动无投递点**——长线程下账本照样丢。

### 修改（vibeweaver-gate.js，单文件接线，零新依赖）

- **通道实证**（先探针后实现）：1.18.35 上 `experimental.session.compacting`（output.context 追加进压缩摘要 prompt）、`session.compacted` 事件、`experimental.chat.messages.transform` 三通道全可用（实测触发 3/3/7 次）；v2 新一代 `ctx.session.hook("compaction"/"context")` 在有 session 域的宿主上守卫式注册（1.18.x 混合适配器不暴露，v1 路径承担）。
- **三处确定性投递**：① `compacting` 钩子把 working_note（≤4KB）+ 恢复规则推进压缩 prompt 上下文（摘要带着账本走）；② `session.compacted` 事件按**会话 ID** 置 pending → 该会话的下一个 `experimental.chat.system.transform` 把 resume bundle 推入 system 数组（每次压缩恰好一次，成功投递后才消费）；③ 会话首次受门管的 write/edit 携带一行 resume 指针（每会话一次；存在→先读；活跃任务无 note→创建指引）。
- **r1 修复（A4.9 揪出，均为实测）**：初版经 `messages.transform` 注入 `{role,content}` 消息——1.18.35 该通道实际吃 `{info,parts}[]`，注入即崩宿主（run2/4 的 UnknownError 为证）→ 改 `system.transform`（input 带 sessionID、output.system 字符串数组，无 schema 风险）；v1 事件信封是 `properties` 非 `data`（会话键控武装据此修正，补回归用例 D3e）；firstTouchCue 会话键控；删除未实证的 v2 `ctx.session.hook` 死码。
- **遥测**：`.vibeweaver/state.json` 新增 `memoryDeliveries` 计数（compactContext/compactResume/sessionCue）——机制是否真的在跑，可数。
- **顺带修复**：stallObserver 的状态读入 `st={ops:[]}` 重置缺陷会吞掉 state.json 其余字段（memoryDeliveries 首当其冲）——改为保留未知字段。
- §A7.15 补「确定性投递」条款：harness 投递文件现状（必须保持 note 新鲜）；测试 +13（compat D 段 v1 钩子/v2 守卫/遥测/one-shot 语义）。

### 验证

- compat harness 69/70（D 段 15 项全过含 properties 回归；唯一失败 G9 为**既存**——clean HEAD 同样失败，属 audit 插件 loop-guard，按范围隔离）；mutation_sweep 41/41；`node --check` 过。
- **真机端到端（r1 终验）**：隔离 HOME + 6000 token 上限强压多次压缩的真实会话，修复版实测 `compactContext:5 + compactResume:4 + UnknownError:0 + 任务正常完成`（run8/proj7；初版"三计数全到 1"实为崩溃前的假绿，已更正）。
- 既存失败记录：audit_selftest T15/T21/T22（latch 相关、顺序污染型，clean HEAD 复现，非本波引入）——留后续波处理。

---

## 2026-10-10 修改：loop-guard 盲区波（reasoning 通道 · counter 墙 · turn 上限 · 标点墙）

### 来源

联网盲区检索（hermes #97630/#127234/#89294、SpecRA 813 样本分类、claude-code #82803、agent-patterns-catalog、dsh/openclaw guard）+ 直测探针确认 4 项 MISS；用户指令「全都修了」。

### 修改

- **P0-a reasoning 通道**：observePart 文本分支泛化 text|reasoning（独立 `reasoningParts` 缓冲 + `*Reasoning` 通道三元组键，预算 2/通道独立）；v2 防御接线 `session.reasoning.delta` + content 项路由。覆盖 hermes #97630 事故形状（`!!!!` 墙整个发生在 reasoning 流、content 为空 → 旧守卫全盲）。
- **P0-b counter 墙检测**：loopFinding 新增 shape-run 段——≥16 连续尾行非数字 shape 相同且**每个数字段严格 +1**。严格 +1 是 FP 关键（hermes 实测数字归一化会误杀合法批量输出；时间戳日志只有末段 tick、`page N of M` 的 M 不动，均被自然排除）。SpecRA 分类中「带增量变化的结构重复」占真实退化样本 46.26%，是最大单一类。
- **P1 per-turn 绝对上限**：`LOOP_TURN_CEILING=65536`（64KB/turn，`sess.turnChars` 计量、messageID 变化清零）超限合成 `runaway` finding，走既有 latch/预算/episode 语义 + 独立纠正文案（「周期类检测对不可见形状的唯一答案是还没到——上限是可证明有限的 bound」，hermes #127234 修复结论）。64KB 取值兼顾合法长输出（完成表/日志可达 8k+）。
- **P2 标点墙**：纯标点 suffix period 仅当墙 ≥2KB 才放行命中（`!`×4000、`!!! `×800 命中；分隔线/ASCII art 干净）。字母墙（`court `×300、单字 `บ` 类）原已覆盖。
- **测试**：T24l/T24m 25 条新 pin（4 缺口 + 3 FP pin + 预算独立/文案/阈值），RED 8 失败留证后全绿；T24k 28 断言零回退；mutation_sweep 41/0。

---

## 2026-10-10 修改：loop-guard "Stop it." 墙漏拦修复（尾部空白种子洞 · 内嵌行 gate 洞 · turn 级 episode）

### 来源

用户实测：某些模型输出 `"Stop it. "` 无限重复墙，loop-guard 未拦，质询「理论上不是所有无意义 repetition 都会被拦截么」。探针复现三个缺口（`loopFinding`/`charPeriodRepeat` 提取直测 + adapter 级 T24k）。

### 修改

- **G1 尾部空白种子洞（charPeriodRepeat）**：周期发现以「最后 32 字节精确重现」为种子，tail 尾随 `\n`/双空格时种子唯一出现即自体 → 整个字符周期路径失明（`R(300)+"\n"`、`R(300)+" "`、prose+内嵌 runaway+`\n` 实测全 MISS）。修复：种子发现与 4 份验证前对 tail 做 `replace(/\s+$/,"")` 归一。partial-unit 截尾（`…Stop it`）本就天然命中（种子窗口与前缀截断重叠），未过度设计。
- **G2 内嵌行 gate 洞（loopFinding）**：char 路径 gate 的 512-monster-line 阈值把 128..512 字符的单行内嵌 runaway 挡在扫描外（≥4 换行上下文）。修复：阈值改 `LOOP_CHAR_GATE_LINE`（512→256）——高于 ×4-of-32（128）下限，换取表行误报安全（代码注释明示）。
- **G3 episode 闩锁洞（maybeGuardCheck）**：闩锁只认「干净文本」re-arm，只会退化的模型在第 1 次干预后守卫永久沉默（墙继续刷）。修复：message 边界 re-arm（`fireMsgID`/`lastMsgID` 相异 = 新 turn = 新 episode）；同 turn 延续仍不 thrash（T24e 语义保留），预算 2/会话/通道硬顶不变。`sess.lastMsgID` 由三个 observe 入口写入。
- **文档**：COMPLETION_GATE AUDIT 段补尾空白容错与 256 阈值一句、episode 语义改为 clean-OR-new-turn（44220B ≤45KB）。
- **测试**：T24k 12 断言（G1×3、G2×1、mid-unit pin、FP bar ×3、turn 序列 ×4）；RED 6 失败留证后 GREEN 12/12；mutation_sweep 41/0 保持。
- **方案比对**（exa 检索 hermes-agent #86581/#94224、dsh-llm-repetition-guard、openclaw text-repetition-guard、opencode doom-loop 跨消息洞）：选最小补丁三处；否决 n-gram/dominance 重写（动已校准 FP bar）与拆闩锁（违 never-thrash，hermes 亦以 2 kills/turn 为界）。

---

## 2026-10-09 修改：stop-guard —— 假停防线（§V12）

**缺口。** 模型在任务中途宣称"上下文耗尽，先到这里"对所有执法层隐形：字节级
loop-guard 只抓退化重复，gate 只在写入时触发，audit 只审计完成声明——裸停机
声明没有牙齿。Cognition 的 context-anxiety 报告与 arXiv:2609.36322（分块
KV-cache 压缩下的相位敏感性）解释了成因：模型作用于一个它无法测量的感知上限。

**机制。** §V12 定义四个合法停点（ALL-PASS · cap/stall 记 ❌ · PAUSED 包 ·
`[Coverage]` 诚实部分完成），"上下文耗尽"是必须有 §V9 依据的预算声明。audit 插件
新增 stop 通道：语法级遁词检测器（中英、剥离引用、元讨论感知、要求终止意图）作用
于最后一条 assistant 消息，会话级终态白名单，每 episode 一次纠正 prompt（预算
2/会话、episode 键控武装、绝不 abort 已完成轮次）、stop-debt 日志（cap 5）重放进
`tests/gate_audit.md`，v1 遥测接线（`message.updated` role/tokens/finish）引用实测
填充率（≥90% 时转为收敛措辞）。v2 降级为仅债务模式（白名单在 v2 不可证）。
`finish:"length"` 截断走同一通道。双对抗评审两轮（22 项发现全部裁决——Critical
是守卫被自己的纠正 prompt 反噬）+ FCV 8/8；fixture 166 / 变异扫描 41。

---

## 2026-10-07 修改：wave17 —— 机制全清波（stall latch · audit B12 final-run 门 · 4b trigger 前缀 lint · backlog_check.py · TESTING_PROTOCOLS 瘦身）

### 来源

wave16 收尾复盘点名：stall 告警洪泛（狼来了）、`--final` 仅约定不可证、trigger 陈旧无检测、C8 无机制层、bash 旁路/cue 劝告性/win32 未记录为边界、TESTING_PROTOCOLS.md 超 45KB 散文预算。用户指令「全部做掉」。

### 修改

- **stall latch（gate 插件）**：停滞签名 `firedKey = 文件@PASS计数`，同一签名只报一次，新 PASS 落地重新武装；状态写入移至判定之后保证 firedKey 持久。根治「计划内多文件连编被连刷 10+ 条 GATE-WARNING」的信噪比坍塌。compat C6（5 连编 fires=1）/C6b（重武装）钉死。
- **audit B12（audit-core）**：收官门行在场 ⇒ 当前任务块（最后一个 `## ` 块）必须含 `- final-run: --final … pass=N/fail=0` 日志行。物理门永远不可能带 `--final`（它无法知道哪次跑是最终跑），日志行是 group 19 真正执行过的唯一机器锚点。T37 BAD→OK 钉死；三处旧夹具按新契约补行（§V2 记录）。
- **assert group 4b（trigger 前缀 lint）**：memory 主题 `triggers:` glob 的字面前缀必须仍存在于仓库（`**` 开头豁免）——陈旧 trigger = 静默不投递，与 stale reference 同类。解析器与 gate.js 对齐（含 CRLF/BOM、scalar/zero-indent/尾注释/无引号行内列表）。T36 钉死。
- **scripts/backlog_check.py（新，C8 机制层）**：backlog.json schema 校验 + 每个 `passes:true` 必须被 verification_log/progress.txt 的行点名（COV-1 在 backlog 层的兑现）。T35×3 钉死；install.sh/install.bat 安装清单收录。
- **边界显式化**：§A4.4.2 记 bash 旁路（`sed -i`/`>`/脚本写文件绕过 gate 与 cue，缓解=收官 `--final` 跑 + B12 看结果树）；§A7.16 记六条已知边界（cue 劝告性、bash 旁路、dup first-wins、4b、safeGlob 上限、win32 仅单测钉未真机）。
- **TESTING_PROTOCOLS.md 瘦身 47791→44993B ≤45KB**：削重复 rationale/示例/引文，复审抽查零 MUST 丢失（两条误删指令经评审恢复）。
- **杂项**：runAssertFixture 30s 超时；project_build.sh 前置 canonical→tests 自动同步（cmp‖cp&&echo，本仓自副本不再手动漂移）；全冻结 event 钉测试 D2c。
- **working_note 首次 dogfood**：本波全程创建→2 更新→蒸馏→删除，group 19 `--final` 实证生命周期可用。

验证：RED 6 项（tests/w17-red.log）→ GREEN：selftest 126 checks、sweep 41/41、compat 57/57、T11 48932B、本仓 `--final` 30/30；scoped 复审 8/8 SOUND 零 Important，6 Minor 同波修尽（w17-final2.log）。

---

## 2026-10-07 修改：wave16 —— 任务级工作记忆（§A7.15）+ cue 锚定触发（§A7.16）+ log-format lint（12b）+ group 19/--final

### 来源

用户授意实施调研结论：SOTA（Anthropic 分层记忆/Manus todo.md/「Delivery, Not Storage」确定性投递/Graepel 认知状态账本）指向同一缺口——任务级「此刻什么成立」的状态层 + 记忆的投递时机机制化。

### 修改

- **tests/working_note.md（§A7.15）**：编年（tests/ 日志）与策展（memory/）之间的任务级状态文档——假设账本（confirmed/doubted/excluded/open）+ 关键位置 + 本任务死胡同 + 下一动作，≤50 行可重写（git 历史即审计）。生命周期：Lane M/L 或第二迭代起创建 → FAIL/迭代边界/compaction 前更新 → §3.3 重入首读 → 任务末蒸馏入 memory/ 后删除。删除由 assert **group 19** 在收官 `--final` 跑机检（中段/物理门不带该旗标，不阻塞迭代）；A7.10 增 check 6；旧 `.session-scratchpad.md` 正式废止（A7.14 rule 3 更替）。
- **cue 锚定触发（§A7.16，机制非 steering）**：memory 主题 frontmatter 可声明 `triggers:` 路径 glob；gate 插件在 write/edit 完成后扫描命中并注入一行 `vibeweaver-cue` 提示（≤3 条、指针式渐进披露、memory/ 自身不触发）。**投递提升于门之上**：RED 门的 block 消息同样携带、tests/ 路径同样投递——任务首次写（门必红）恰是最需要提示的时刻。安全上限 safeGlob：≤2 个 `**` 组/≤200 字符/拒控制字符——**被 harness 编译的记忆文本是代码不是数据**（评审实测 `**/`×10 → 98s 事件循环 wedge，prompt-injection 可达的 ReDoS）。
- **log-format lint（group 12b）**：FAIL 行 diagnosis 须为实质可证伪子句（≥10 字符、拒 `-/?/none/na/idk/unknown/tbd` 占位）；捕获锚定 `| changed:` 防含 alternation 的 diagnosis 被截断成假阳性。
- **r1 评审修复波**：双对抗 reviewer（2 Critical：上述 ReDoS + COMPLETION_GATE covenant 字面量 12↔13 自 wave14 陈旧；9 Important：CRLF/BOM 静默死触发、§3.3 Skipping 1-4 悬挂、§M 重入序陈旧、`--final` 五处调用点缺失、scratchpad 更替矛盾、trust:/status: schema drift、组数/A7 范围 prose 陈旧×8）全部修复 + scoped re-review 14/14 RESOLVED 零回归。

验证：RED 5 项（tests/ab-red.log）→ GREEN：selftest（T33a-d/T34a-c）+ sweep 41/41 + compat 53/53（C5a-i cue 系列 + D2b v2 通道）+ T11 48968B；FCV 独立复核 5/5 PASS（tests/fcv_report_wave16.md）。

---

## 2026-10-07 修改：wave15 —— C8 Outer-Loop 工作流（Ralph 模式吸收）

### 来源

用户给出两个候选改造源：AlphaGo 作者「LLM 不会推理」一文（结论：vibeweaver 既有机制已覆盖其处方，无需改）与 Matt Pocock/Geoffrey Huntley 的 Ralph 循环（结论：有真实增量——跨会话 backlog 级外层循环是 vibeweaver 空白）。判定后实施后者。

### 修改

- **C8 Outer-Loop（WORKFLOWS_EXTENDED.md 新增）**：状态全落盘、每迭代 fresh context、每轮只做一项小任务、显式停止信号。七步模式：`tests/backlog.json` 机检账本（`{id,title,acceptanceCriteria,priority,passes,dependsOn}`，`passes` 为停止条件）· append-only `tests/progress.txt` 编年（与 curated memory 分工：原始编年 vs 蒸馏记忆）· 迭代循环（§3.3 重定向 → jq/gh 计算 frontier 而非散文重建 → 单项全 §1 契约 → 绿才提交，红提交毒化后续全部基线）· 停止信号（COMPLETE/BLOCKED→PAUSED/DECIDE→ADR/预算耗尽非失败）· HITL 先于 AFK · 反馈环上限（循环质量=仓库检查能证明的上限）· steering 落盘（memory/ADR/backlog，非聊天记录）。与内层循环的关系显式声明：cap=5/stall=3× 管单项，迭代预算+空 backlog 管外层。
- **SKILL.md 字节帽净零编辑**：T11 上限 49000B 余量仅 8B，4 处路由新增（§3.1 任务表 C8 行、R9 触发、Part C 标题、Reference Files）+148B 由 5 处冗余压缩 -153B 对冲（48992→48987B），操作纪律录入 memory。

验证：selftest 含 T11 + sweep 41 + compat 43/43 exit 0（tests/c8-final.log）；assert 29/29；安装同步 diff 一致。

---

## 2026-10-02 修改：审计锁存同会话自释 + payload 回归合并（wave14）

**死锁本体。** 一个多波会话在第 1 波被打上 RED 锁存后，无法在同一会话里开始
第 2 波：源码写入被锁存拦截，而能解除锁存的 GREEN 审计又依赖被拦写入才能落地
的证据。三条释放路径（其他会话的接管写入、24 小时 TTL、`VIBEWEAVER_AUDIT=off`）
全在会话之外——需要人肉换会话才能解锁的机械门禁，就是坏掉的门禁。

**修复（两条会话内语义；牙齿与留痕不变）。**
- **新任务键。** 协议规定新任务的第一步就是重写 `tests/acceptance.md`
  （Step 1；`tests/` 在锁存下永远可写）——这次重写会在该会话下一次受门禁写入
  时自动释放锁存，留痕为 `new-task`。`floor(mtime)` 与锁存时间戳做严格比较，
  同毫秒平局判"不释放"（牙齿赢平局）。
- **BAD 签名守卫。** final 审计打分的是整段会话缓冲，而多波缓冲永远保留上一
  波的残留——对"未变化的失败"反复重审不得重新上锁（旧跑步机会在每次 idle 刷新
  锁存时间戳，饿死 TTL 兜底、复活已被释放的锁存）。RED final 只有在**按会话
  键控**的签名变化、或 `[Verification Gate]` marker 计数增长（真正的新完成
  声明，签名相同也会重臂牙齿）时才重新上锁。对抗评审第一轮抓出两处硬伤：
  root 级签名键会赦免**另一个会话**的真实首次失败（模板驱动的 BAD 集跨会话
  相同），以及"一次写文件永久拔牙"——均已修复并由 T29–T32 回归覆盖；第二轮
  复审结论 `ready`。

**回归合并。** 分类波的 18 组 `assert_artifacts.py`（`--class DOC|CONFIG|CODE`、
§V11.9 DOC 资产渲染门、交付时 exec-check）一直没落进 dev canonical——只活在
安装副本和本仓。wave14 将其落地，把 11 个分叉的 payload 文件双向合并
（分类波 ⇄ noop-bash/latch 波），marker 三角（文档清单 == `verify_skill`
MARKERS == canonical 脚本实含）重新收敛到 19。测试套件：112 项 fixture 检查 /
41 项变异扫描 / 43 项兼容性检查，四副本全绿。

---

## 2026-09-28 修改：任务分类 —— 比例化验证路径（COV-13 / §V11）

验证路径不随任务缩放。改一段 README 或 CHANGELOG——没有运行时可测的散文活——和改行为走同一条路：带磁盘证据的测试、基线运行、8 列完成表、记忆门。更糟的是路径本身反过来推着文档动（「流程里有 README 这一步」），不管内容是否真的过期。一个说不出对应风险的 gate 就是流程膨胀。外部研究从四个方向给出同一答案：E3 的 estimate→execute→expand（arXiv 2607.13034——先按最小路径执行，只在验证失败时扩）、bucket→verification-depth 分桶定深、「无名风险的 gate 即流程膨胀」、以及单次分诊结果驱动全部下游决策。

- **COV-13，Class 声明。**由变更集的文件种类判定——`git diff --stat` 加 untracked，绝不靠记忆：`Class: CODE`（含控制流的逻辑源码：分支/状态/校验/变换，含带行为断言的测试文件）优先，其次 `Class: CONFIG`（配置、脚本、标记、CI——无控制流），最后 `Class: DOC`（散文：md/txt/rst、README、CHANGELOG、docs/、memory/、office 资产）。首匹配取序；不确定取高一类；scope 越界或证据点名更高类风险时升类，且只升不降。
- **每类一张 path card（§V11.3），gate↔具名风险。**DOC 把测试、捕获循环、基线运行、8 列表降为 `na (reason)`，保留验收判据、迭代日志、`[Coverage]` 与 gate line——外加三列 lite 表（`| # | Problem | What Changed & Evidence |`），且仅在 gate line 带已填写的 `Class: DOC|CONFIG` 字段时合法。CONFIG 保留 smoke 检查与 COV-9 基线。CODE 不变。类无关集不动：密钥扫描、test-change 守卫、风险层审查、cap=5/stall=3× 边界。
- **doc-drift 触发器（§V11.5）。**README/CHANGELOG/API 文档只在内容确实过期时更新，且漂移必须具名（`docs-drift: <file> — <what went stale>`）；无漂移也要给一行（`docs-drift: none (<why>)`）。「流程里有 README 这一步」不算漂移。
- **Class × Lane（§V11.8）是两个轴。**Lane 管读深与加层，Class 管哪些 gate 跑。DOC-prose 下 Lane-L 增件（计划文件、FCV、对抗评审、覆盖矩阵）走 `na`；DOC-asset 的 FCV 是一次全新重渲（渲染就是它的 oracle）；COV-8 文件计数腿走 `na` 但须报出非散文路径数。风险层/schema/API/行为语义腿在任何类都触发。
- **执法双侧。**`assert_artifacts.py --class`（或任务块的 `- class: <X> — <basis>` 行）为 DOC 跳过记忆与服务生命周期组；审计侧新增已填写 `Class:` 字段检查（未填模板与散文提及一律不构成许可）、gate line↔log 类交叉核对、memory `na` 需真行理由（清单回声不算）、类错报守卫。
- **验证。**fixture 套件增至 103 条断言（类套件：lite 放行、未授权 lite/na/模板拒绝、误报 token（`Class: DOCS`、`DOC/CONFIG`、空格模板）拒绝、tests/ 隐藏与无时间戳写抓获、gate↔log 不匹配抓获、旧任务块不给当前块许可）；变异扫描增至 41。TDD RED：类测试对变更前 core 批量失败。两轮对抗评审（契约一致性、执法绕过）加一轮全新上下文 FCV；一处 spec↔测试冲突按 ADR 裁决而非糊弄过去。

---

## 2026-09-28 修改：DOC-asset render 门与 doc-skill 委托（§V11.9）

office 交付物无家可归。`report.docx`、台账 `.xlsx`、答辩 `.pptx` 既不是代码（无控制流）、不是配置、也不是散文，「不确定取高类」只能把它们推上重路径。而 DOC 的证据规则——diff 加 read-back——恰好是文档工具界反复警告的那件事：文本抽取与文档对象模型会在分页上说谎。误判它们的那道门同样错了：类错报守卫把每次 `.docx` 写入都当谎言。

- **制品种类，不是第四类。**office 资产仍是 `Class: DOC`，由扩展名决定证据模式（散文 → diff 加具名 read-back；资产 → render-and-verify）。类值更少，可误报的点更少。
- **NO RENDER, NO DONE**（openai `doc` skill 与 office-docx 的共识）。`soffice --headless` 转换、渲页、自动 QA（空白页、edge bleed、缺内容、页数）、页图经宣布的 verifier 评级、修、重渲。render→修 循环就是资产的 COV-4 循环，与任何循环一样受 cap=5 / stall=3× 约束。
- **doc-skill 委托（§V11.9）。**readme-weaver 审计 README 类散文（永不编造：每条命令、徽章、路径都对仓库实物核对）；docx / xlsx / pptx-manipulation 负责写作；office-docx 渲染验证；office-mcp 兜底。skill 指令是数据与工具（COV-11）——为管线提供信息，永不压过契约。宏启用容器仅当具名可执行行为检查（`unzip -l` 查 `vbaProject.bin`、PDF `/JS` 扫描、宏表扫描）干净时留 DOC，否则升类，render 门随资产上行。
- **完整性规则（docx-master、skillsdirectory）。**制品即证据——对独立不变量验证（重解析、schema 校验、渲染页），不用系统对自己输出的自我解读自证。落新文件；验证失败即弃候选文件并暴露错误；无静默重试。工具链缺失降级为带旗标的 `render: N/A (<缺失工具>)` 加 layout 风险提示，交付物标 `UNVERIFIED-layout`——绝不悄悄「完成」。
- **验证。**TDD RED：对变更前 core，每次 `.docx` 写入都被误判为类谎言，合法渲染情形亦然。新 fixture 双向钉死 render 门与 exec-check 行。

---

## 2026-09-28 修改：盲区加固 —— file-kind 门、证据绑定、交付时点 exec-check

上面两波之后的盲区猎杀找到真窟窿，其中几个就在已宣称闭环的声称里：两路探针加一路全新上下文语义猎手，九项确认。共同模式：门挂在类值上而不是文件种类上，证据从哪来都收。

- **render 门改为文件种类触发（任何类）。**混合 CODE 波交付样例 `report.docx`、部署波的发布 PDF、CLI 导出的 docx——一视同仁欠渲染。资产不再构成类错报，顺带解开一处升级死锁：宏 →「升 CONFIG」→「资产属 DOC」→ 自相矛盾。门随资产升入更高类。
- **证据绑定。**只有当前任务块与最终回答能绑定；`probe_vision.*`（COV-5 工具输出）永不算文档页；每个交付物一行 `render: <asset> — …`（一张图盖不住两个文件）；引用的页图必须在盘存在；工具链 N/A 必须点名具体工具——占位符（`<missing toolchain>`）与裸 "toolchain" 不是名字；引用回声不构成许可。
- **波次全程，不是工作区。**资产集合取自 `backup: before changes`..HEAD 加未提交与 untracked（`--name-status`，二进制安全；删除不算交付）。第一版修复只看工作区，fixture 证明资产一 commit 就隐形。
- **exec-check 在交付时点。**具名可执行行为检查跑在交付文件上（分类时文件还不存在），记录为 `exec-check: <asset> — clean|escalated`，由新增断言行强制。
- **DOC 类的教训也绑定。**带 FAIL/stall 条目的波次有教训可存；其记忆组不再可跳（COV-7 的 ❌ 入档规则）。
- **layout 诚实通道。**日志与回答里写 `Layout: verified (<pages>)` 或 `Layout: UNVERIFIED-layout (<why>)`，未验证必须落进 `[Coverage] unchecked`。图像交付物（`docs/figures/*.png`）经宣布的 verifier 评级，不默认没事。read-back 给出定义（逐字重读编辑后的文件；只看 diff 不够）。
- **验证。**fixture 103 / 变异 41，含原始四探针作负例与逐资产绑定；FCV 一轮重跑十项探针全部闭环。

---

## 2026-09-28 修改：loop-guard noop-bash —— 工具通道 echo 旁白循环的机械中断

一种弱模型失效形态从 vibeweaver 现有的全部停止机制底下溜了过去：模型反复宣告要调工具（"use Read now"、"final"、"grading"），实际发的却是裸 `echo "…"` bash 调用——一口气 20 多次，每次 exit 0，字面各不相同。文本流 loop-guard（字节级周期/序列/字符周期三检测器）在结构上看不见它；门禁的 stall observer 只盯 write/edit；COV-7 的计数器永远不推进——循环卡在任何验证迭代出现之前。外部研究与此形态完全吻合（reasoning 说调 X、action 发 bash 的意图-动作脱节；byte-identical 守卫抓不住变字面；每次调用都"成功"）。

- **工具通道内容级检测器**（`scripts/vibeweaver-audit-core.js`）。`isNoopBashCommand` 判定字面量 `echo`/`printf`/`true`/`:` 且无副作用（保守偏置：重定向、管道、替换、串联、未闭合引号一律算真实命令）；`noopBashFinding` 在尾部 ≥4 个相异 no-op bash 调用时触发。同一工具 part 的流式重观测按 part id 去重；unknown/仅状态观测既遮不住 run 也不消耗 pid；被截断的命令直接断开 run（截断能伪造出字面量）。已知缺口如实入档而非粉饰：语义级 no-op（`sleep`/`ls`/`pwd`）与 echo/read 交错振荡需要意图-动作一致性检测，明确不在范围内。
- **双通道守卫**（`vibeweaver-audit.js`）。原单通道 `maybeLoopCheck` 改为 `maybeGuardCheck(sessionID, channel)`：text 与 tool 两通道只共享干预机制，各自独立的发作 arming 与每通道 2 次的预算——文本退化发作永远不会饿死工具通道最需要的那次打断。`noop-bash` 的纠正提示要求立即发出真实工具调用（或在判据确已全部通过时输出完成产物），并强制在完成输出前向 `tests/verification_log.md` 写入 `- stall: noop-bash …`——中断本身就是 stall 声明。
- **契约文本**。TESTING_PROTOCOLS §A4.1 Step 2 增加「旁白≠执行」（宣布的工具调用不是调用，echo 标记不是行动）；§A4.10 将 noop-bash 中断列为 stall 声明；SKILL.md 增加状态迁移许可（PRE-OUTPUT 全勾且 `assert_artifacts.py` exit 0 后即可完工，禁止用 echo 调用填充过渡）。两处措辞都如实划定保证范围：裸字面量 run 有机械中断，带装饰的变体没有。
- **测试**。T24a–j 共 25 条断言：分类器 32 个边角、阈值与重置语义、part id 去重、adapter 级干预（每发作恰好一次、预算耗尽仅记日志、`VIBEWEAVER_LOOPGUARD=off`）、文本通道回归、预算隔离、unknown 观测与截断边角。套件 69/0，mutation sweep 27/27。两轮对抗评审：首轮 14 项发现（修复即上文），次轮确认 ready。

---

## 2026-09-27 修改：wave12 —— 客观 A/B 评测方法论（§V8）+ 首轮客观结果

此前的 A/B 轮存在三个测量缺陷，一度得出"新技能更差"的错误结论：循环指标（奖励技能自家新增输出字段）、无盲测（agent 见得到评分标准）、污染轴（fixture 里的故意错误测试惩罚诚实臂、奖励静默改写测试的臂）。本波把评测手册替换为客观指标层级，并记录真实发现。

- **§V8 重写为客观指标层级。** 裁决轴按序：隐藏 fail-to-pass 测试（SWE-bench 范式：金标准断言仅在评分时注入）> 完整性（可见评分测试 hash 未改；规格↔测试冲突任务上，静默改写测试即违规——哪怕套件变绿）> 有效突变分 `EffMS = MS × SPR`（SecMutBench 有效性门：交付套件先在金标准实现上通过，其突变杀伤率才计入）> 成本（墙钟/字节，并列报告，永不做裁决）。合规 token（gate line、`[Coverage]`、`Lane:`）明文降级为循环过程标记。
- **六条测量陷阱固化**（实测中每条都以作废一轮为代价）：投毒 fixture 测试须剔除出套件评分 · 金标准过规范（规格欠定行为）使该任务 SPR 不可解释 · 等价突变体须开跑前用完美套件验证可杀 · 陈旧字节码掩盖同秒同长突变改写（pytest 加 `PYTHONDONTWRITEBYTECODE=1` + 清缓存）· 字符串 task id 禁止用数值同一性分发 · 截断格=budget-invalid，永不计为行为失败。
- **`scripts/ab/obj_eval.mjs`** —— 客观评分器：内嵌金标准实现、隐藏测试电池、语义金标准突变体，以及评分机器自检（完美套件必须 100% 杀伤突变体电池、隐藏测试必须在金标准上通过）。自检在花费任何 agent 时间前抓到 3 个评分 bug。

实测验证（qwen3.8_27b，3 任务 × 每臂 3 trial，N=3 LOW 置信、方向性）：隐藏 F2P B 8/8 vs A 7/8（A 的缺失=冲突任务硬停机未交付实现）；完整性 B 5/5 vs A 3/5——A 两次静默改写矛盾测试刷绿套件，B 分毫未动并旗标冲突、同时按规格实现（Fisher p=0.222）；A 在冲突任务此前的高突变分是篡改溢价，剔除投毒测试后消失；EffMS 仅 bugfix 任务可解释（两臂 1.00 平）；成本 B ≈1.35× A（评审波触发时最高 2.3×）。正确读法：新技能用速度换防篡改纪律——"效果更差"是测量假象。

---

## 2026-09-26 修改：wave11 —— 仪式经济学、行动分诊（AEWM）、诚实的超时

两轮 A/B（28 个有效评分格，deepseek-v4.1-flash 与 qwen3.8-27b）暴露：第一轮升级的纪律全部前置时，弱模型把格子预算烧在协议装载和 ADR 长文上、代码没落地；STOP-优先的冲突语序诱发仪式性停机；420s 截断被误读为行为失败。本轮修经济性、移植 AEWM（arXiv:2609.28416）的污染防护、并让超时诚实化。

- **§V9 仪式经济学。** 交付顺序硬约束：最小代码+测试绿先行（日志一行一条），然后证据，然后完成输出；延迟仪式（memory 主题、评审包、ADR 长文）在完成时从日志组装。每轮迭代入口做预算保留自检（剩余预算还够"代码+一次测试+gate line"吗），不够就收敛、其余写进 `[Coverage] unchecked` 点名。Load Map 让安全规则（契约/完整性/诚实语义）常驻、A4.6/A4.7/A4.9/A4.10 按触发点惰性加载（混合加载，依据技能加载研究）；叙述是一行行动索引，不是长文。
- **§V2 先实现无争议部分。** 测试↔规格冲突时规格为准、无争议部分先落地；冲突在边界旗标（PAUSED/ADR），嫌疑测试保持失败并被点名。仅当争议行为就是全部交付物时才 STOP-before-code。实现期测试保持只读。
- **§V10 行动分诊与状态修订。** 源自 AEWM 的 task-state contamination 分析：每个计划动作在日志行标注 `[C|E|N]`（critical/exploratory/noisy），N 不执行、先改写；证据否决假设时就地改写承载它的工件（edit, don't append）；局部绿永不升格为任务完成。
- **车道、FCV、覆盖诚实。** Lane S/M/L + 客观资格线（S 只压缩读取量——12 条契约与全部 gate 不减）；车道升级只看范围增长，ADR/旗标/PAUSED 不触发；最强绿证是自写测试或 Lane L 时强制全新 context 复核（FCV）；`[Coverage] criteria: N/M | unchecked: …` 与 `UNVERIFIED` 格让"没查过"可点名、不可洗白成 `na`。
- **诚实的超时（§V8）。** 超时格=budget-invalid：从行为正确率剔除、单列完成率；墙钟与输出字节只是 COST 指标，绝不是 pass/fail 轴。fixture 先过无-skill 预算校准。**TDD/新特性 fixture 按 2h/格预算**（`--timeout-tdd`，默认 7200s）。
- **新脚本。** `scripts/scan_secrets.py`（命名式检查的密钥扫描）与 `scripts/ab/run.mjs`（配对 fresh-context A/B harness：确定性断言、Fisher 小样本标 LOW、birthtime 交付顺序检查）。

验证：新内容下包内 CI 全绿（verify_skill.py 9 项、unittest 18/18、audit_selftest 44 项 fixture、mutation_sweep 27/27——引擎字节不变、仅文档层）。1200s 预算下两臂在 bugfix 与规格冲突任务上均完整合规（gate-line 2/2、implements-spec 1/1、测试完整性 8/8、冲突旗标 8/8）；此前 420s 的"B 臂落败"读数确认为截断伪影。deepseek 复跑因上游订阅故障作废并留档。

---

## 2026-09-24 修改：wave10 —— loop-guard 检测边界补齐（无换行流 / ≤640 行大周期块）+ repo README 与 GitHub 同步

### 来源

用户要求补齐 wave9 留下的两个检测盲区（单行无换行流式重复、>192 行周期块），并更新 vibeweaver-repo、README 与 GitHub（明确授权 push）。

### 修改

- **字符级后缀周期（新增 charPeriodRepeat）**：行稀疏/无换行尾窗（最近 2KB <4 换行或末行 >512 字符时启用）检测同一 ≥32 字符单元（含字母数字）连续 ≥4 份；候选周期由末 32 字符种子的复现位置给出（≤16 个，native lastIndexOf）；种子自身短周期时探测其 ≥32 超周期倍数（"very "×40 类逃逸覆盖）。与行路径统一 4 份栏——JSX/HTML 单元素 ×3、纯标点串不触发。
- **行周期上限 192 → 640 行**：尾窗扩到 96KB（约 ≤50 字符/行的现实代码 3 份拷贝全覆盖），候选周期仍按末行复现过滤，精确比对；新增 G10（300 行）/G10b（640 行）块 ×3 触发断言。
- **评审两轮**：首轮 ready-with-fixes（2 Important：单元素 ×3 不一致误伤、短子周期超周期逃逸；4 Minor：陈旧注释、全尾重扫、memory 边界、门控遮蔽延迟）全部修复；scoped re-review 7/7 ADDRESSED `ready`。
- **repo README 更新**：双版本兼容段（{id, server, setup} 单文件）、What-it-does 增 loop-guard 条目、审计段补 C8 一次标记与 loop-guard 三形态、诚实边界段改为双代 API。dev README/COMPLETION_GATE 同步三形态与窗口边界。
- **分发**：payload 五件套（双插件、core、selftest、COMPLETION_GATE）dev→system/open-source/repo 字节一致；repo verify_skill 9 checks + unittest 13/13；repo 提交并 push GitHub（用户授权）。

验证：compat 43/43（G9 重构：×3 clean/×4 fires/super-period fires/JSX clean/标点 clean；G10/G10b 大周期触发）；selftest 44 checks；sweep 27/27；assert 26/26；4 副本 `diff -q` 一致。

---

## 2026-09-24 修改：wave9 —— v1 启动静默 + C8 锁存自解 + 生成退化 loop-guard

### 来源

用户报告：(1) v1 opencode 在任意项目启动时，两个插件都打印"host context lacks ctx.tool.hook/ctx.event.subscribe"——v1 混合桥以残缺上下文调用 v2 `setup` 是预期路径，告警属 UX 缺陷；(2) 希望尽早识别模型输出退化（同段代码反复生成；无意义 echo——实测案例：数字 1 连到 179、字母 a 连到 kf，均靠人为停止）并自动停止+纠正。调查中另发现审计 C8 自锁缺陷：C8 每次审计重扫全部历史 bash 命令，跑过一次禁用命令的会话永远 BAD → RED 锁存不可自解（本开发仓的 wave8 会话即被锁，由设计的「不同会话接管释放」解除并留痕）。

### 修改

- **启动静默**：v2 setup 改为仅当 host 提供 `location` 但缺 hook/event API（真实残缺 v2 host）时 warn 一行；v1 混合桥（无 location/tool/event）静默返回——v1 任意项目启动零插件输出（真机 TUI smoke：0 行）。
- **C8 去重（core）**：`auditProject` 新增 `priorFlagged` 入参与 `newlyFlagged` 出参；同一禁用命令字符串按 project root 持久化去重（`.vibeweaver/audit-state.json` `c8Flagged`，上限 100）。锁存可在后续 GREEN final audit 自解，无需关审计、无需手工改状态；新的不同禁用命令仍会 flag。新增 fixture T21（core 三段：首 flag/不重复 flag/新命令仍 flag）+ T22（插件端到端：pkill→锁存→同会话下次 idle 自解）。
- **loop-guard（审计机新增）**：共享 audit machine 在每次文本观察时做有界尾部扫描（6KB）：(a) 行组重复 ≥3×（行对齐，任意块周期）；(b) ≥12 行裸 token 构成 +1 序列（整数 / 双十进制字母）。命中后一段发作一次干预（armed/re-arm 语义，干净文本后重新武装），v1 `client.session.abort` + `session.prompt` 纠正指令，v2 `ctx.session.interrupt({continue:false})` + `ctx.session.prompt`；每会话预算 2（`audit.json loopGuardMaxInterventions` 可调），第 3 次仅记录；`VIBEWEAVER_LOOPGUARD=off` 完全停用。误报守卫：编号列表（"1. 步骤"非裸 token）、2× 重复不触发。
- **文档**：COMPLETION_GATE AUDIT 段补 loop-guard 与 C8 自解规则；README 功能清单 + 兼容性章节更新。

验证：compat harness 40/40（G1-G8 + G3b 任意周期 + G4b 分隔线/单行阈值：整数/字母/块重复触发，编号列表/2×/off 不触发，预算上限、v1+v2 干预 API 断言）；selftest 44 checks（新增 T21 core 去重三段、T22 锁存自解端到端、T23 mid-then-final 回归）全绿；sweep 27/27；真机 v1 启动 0 插件输出行；真机 v1 门禁 RED 项目写入仍 GATE-BLOCKED；4 副本 payload `diff -q` 字节一致；repo verify_skill 9 checks + unittest 13/13。
A4.9 两轮：首轮 **not ready**（1 Critical：mid 审计消耗 C8 一次性名额致锁存永不触发；3 Important：固定表外周期逃逸/分隔线误报/memory 未写；5 Minor）；全部修复并补 T23/G3b/G4b 回归；scoped re-review 8/8 ADDRESSED，verdict `ready`（tests/review_package_w9.md, tests/review_package_w9r1.md）。

---

## 2026-09-24 修改：wave8 —— opencode v2.0 插件双兼容（v1 + v2 单文件）

### 来源

opencode v2.0 发布，插件系统为三大破坏性变更之一：v1 插件实现（导出异步函数返回 hooks 对象）在 v2 下无法加载（`PluginModule` schema 只解码默认导出的 `{ id, setup }` / `{ id, effect }`，多余键容忍）。用户要求联网检索 v2.0 代码并改造本 skill 的两个插件，使其在 opencode 1.x 与 2.x 中均能正确工作。

### 修改

- **模块形态**：`vibeweaver-gate.js` / `vibeweaver-audit.js` 改为仅默认导出 `{ id, server, setup }`（官方文档的双兼容形态；原命名导出移除，避免未知 legacy loader 迭代时二次注册）。v1 侧由 `readV1Plugin` 检测（v1.18.32 源码核实：file 源插件必须有 `id`，多余 `setup` 键忽略）；v2 侧由 `PluginModule` schema 解码（v2.0.16 源码核实：多余 `server` 键忽略）。
- **gate v2 适配器**：`ctx.tool.hook("execute.after")`（仅 completed；throw 阻断，警告写入 result.content/metadata）+ `ctx.event.subscribe` 监听 `session.status` idle；目录取 `ctx.location.directory`；setup 返回 AbortController 清理函数。共享 `gateCheckWrite/gateIdleCheck`，v1 行为逐行保留（阻断先于 stall 记录）。
- **audit v2 适配器**：`ctx.tool.hook("execute.before")`（RED 锁存阻断 + 工具观察）+ `execute.after`（bash 输出回填）+ 事件订阅 `session.text.delta`（文本增量）/ `session.message.content.updated`（全量替换）/ `session.skill.activated`（skill 检测）/ `session.status` idle（驱动审计）。共享 `createAuditMachine`，锁存状态文件跨版本同构。
- **日志降级**：v2 的 `ctx.app` 只有 `{name, version, channel}` 无 log API → stderr 兜底；v1 仍走 `client.app.log({body})`。
- **混合桥实测**：本机 1.18.32 二进制内置 v2 core loader（partial ctx：仅 agent/aisdk/catalog/command/integration/plugin/reference/skill/options），v2 适配器打印一行说明并安全退出，v1 适配器照常生效（实测 RED 项目写入被 GATE-BLOCKED）。
- **验证设施**：新增 `tests/plugin_compat_test.mjs`（29 项：双 loader 模拟 + 双插件双路径行为对等 + 单注册保证）；`scripts/audit_selftest.mjs` 导入适配新形态（`.default.server`，带旧形态回退）。

验证：compat 30/30；selftest 36 fixtures/0 failures；sweep 27/27；真机 v1（1.18.32）RED 项目写入 GATE-BLOCKED；真机 v2（0.0.0-beta-17823 = v2.0.16 构建）隔离 HOME 下两插件加载零错误；payload 经 install.sh 传播，`diff -q` 字节一致。v2 模型驱动 E2E 因隔离环境内 provider npm 包引导挂起未达成（D-8.4 记录边界与手动验证方法）。
A4.9 两轮：首轮 ready-with-fixes（1 Important：v2 订阅循环单事件异常即死 + 5 Minor）；全部修复（循环内逐事件 try/catch、result 原地变更、output 回退、hook 注册 dispose、验收 #5 按 D-8.5 修正）并补 F4b 韧性回归；scoped re-review 全 ADDRESSED，verdict `ready`。

---

## 2026-09-14 修改：wave7 —— 可信 oracle 与确定性 checker 契约（源自 15 臂实验）

### 来源

wave6 spike 的 15 个评测臂证明：确定性循环只有在喂入"受信 oracle"时才有收益（真测试 4/4；自写测试 1/4；生成测试 1/4 且出现假绿）。用户要求把三条结论全部落地（oracle 分级、checker 契约+修复包、变异式资格验证），注意长度预算，然后做一次双模型强制注入 A/B。

### 修改

- **A4.8 可信 oracle**（SKILL.md 绑定 + TESTING_PROTOCOLS 规范文本）：① 项目/外部验收测试（或可执行验收标准）是唯一可认证层级——greenfield 须把验收标准可执行化，做不到则记录 `- oracle: self-tests (weak)` 并标记；② 独立生成+资格验证（stub 必挂 / gold 必过 / 错误解必挂）为弱证据；③ 自写测试最弱。契约不可见 → 标为 open question，禁止发明接口。
- **checker 契约**：项目单一确定性入口（`script/check.sh` / `tests/check.py` / `vw_check.py`）；引用通过行；输出落盘；测试集变化即拒绝运行（哈希守卫——纪律工具，非安全边界）。
- **APPENDIX §A11**（由 A10 更名，避开 Project Memory 的 §A10 命名冲突）：oracle 分级 + 资格验证协议 + `vw_check.py` 模板（递归 `**/*_test.py` + `**/test_*.py`、排除 vendored 目录、fail-closed 哈希记录、900s 超时、修复包 location+observed+expected）+ `qualify_tests.py` 模板。
- **mini kit 重写**：`vibeweaver-mini/SKILL.md`（1,719B 确定性循环 + oracle/不发明接口规则）+ `scripts/vw_check.py` + 中英 README 按 wave6 实测重写；repo 提交（55c9db8）并同步安装副本。
- **长度纪律**：SKILL 41,554→41,772B（净 +218B，A4.6/A4.7/A4.8/A4.9 补偿修剪）；TESTING_PROTOCOLS 46,040→45,977B（净 −63B）；APPENDIX 26,297→33,036B（≤45KiB）。
- **A4.9 两轮**：首轮 ready-with-fixes（1 Critical + 4 Important：checker 递归 glob 缺陷、哈希守卫可绕过、greenfield 无认证路径、mini 未提交/README 过期、A/B 无法验证功能）；修复后 scoped re-review 全 ADDRESSED，并新增持久回归测试 `tests/test_vw_check.py` 5/5。

验证：selftest 36/0/1、sweep 27/27、doc_lint OK、assert 18/18；19 文件 × 3 副本字节一致；repo verify_skill 9 checks + unittest 13/13；各副本 selftest/sweep 绿；dsh 无契约增量，unit 35/35。
A/B（强制注入；按 D-2 仅验证 SKILL 文本非劣性）：ds 16 题 before 13/16 → after 16/16（Δ+3，3-0 单向，McNemar p=0.25；before 为低抽样——wave6 同尺寸 slim 为 15/16——故结论取"无回归、方向为正"；after 臂验证活动更多：write +65%、steps +18%）；qwen3.6-35B 8 题子集 before 4/8 → after 3/8（Δ−1，一退一进，噪声内，满足非劣判据）。

---

## 2026-09-14 修改：wave6 —— 一致性修复 + A/B 门控的 SKILL.md 根文件瘦身（−15.1%）

### 来源

用户要求：先改、再以强制注入 A/B 验证，只在帕累托改进时才 implement；被测模型 qwen3.6-35B @ biklimax.cn:18002 与 deepseek-v4-flash。计划 WP1-WP6 中本轮执行 WP4（机械一致性修复）+ WP2 的根文件瘦身（内容变更，A/B 门控）；WP1（哈希钉扎/CI）、WP3（任务级 eval 扩展）、WP5（vw CLI）、WP6（遥测）留待后续 wave。

### 修改

- **WP4 一致性修复**：`COMPLETION_GATE.md` "all 11 covenants" → "all 12"（COV-12 引入时的遗留漂移）；`scripts/audit_selftest.mjs` / `scripts/mutation_sweep.mjs` 夹具文本同步；T6 改为 SKIP-on-missing-calibration——`--calib <dir>` 现在真正到达 T6 守卫，目录在而会话文件缺失/不可解析时 SKIP 而非崩溃，summary 输出 skipped 计数；README 同步。
- **WP2 根文件瘦身（A/B 门控）**：`tests/w6/make_candidate.py` 确定性生成候选 `SKILL.md`（41,554B vs 48,955B，−15.1%）；未触碰块逐字节复制（无转写漂移），门线模板与 8 列表头从源文件抽取，cap/recall 字面量对源断言。压缩对象：A4 章节流程细节（完整文本在 R1/R1b 必读配套中）、Part B/C 骨架、MANDATORY CHECKLIST 核心化、intro 精简；§1 covenant 全文、Read Contract、全部机器 token 保留。
- **A/B（强制注入，判据先于结果固定）**：deepseek-v4-flash 16 题 before 15/16 → after 15/16（Δ0，零超时）；qwen3.6-35B 8 题配对子集 3/8 → 3/8（Δ0，一进一出，零超时）。协议缩减记入 `tests/decisions.md` D-1（单槽 llama.cpp 上并发 3 排队把单题墙钟放大到 792-1018s、逼近 2400s 超时 → 改为并发 1 固定配对子集）。字节更小 + 两模型非劣 → 帕累托 → 落地。报告：`tests/w6/AB_REPORT_wave6_2026-09-14.md`。
- **新增 dev-only 工具**：`tests/w6/doc_lint.mjs`（跨文件一致性 lint：covenant 计数含 scripts/、cap 字面量、尺寸预算、死链）、`grade_w6.py`、`pareto_report.py`（复现 IMPLEMENT 判定 + 字节条款）。
- **A4.9 独立评审两轮**：首轮 ready-with-fixes（2 Important + 5 Minor，全部修复）；修复轮 scoped re-review 全部 ADDRESSED，新增 1 Minor（`--calib` 无值崩溃）已修 + 校准块对非会话 JSON 加固。

验证：dev selftest exit 0（36 checks / 0 fail / 1 skip）、sweep 27/27、doc_lint OK、assert 17/17；19 文件 × 3 副本 `cmp` 字节一致；repo `verify_skill.py` 9 checks + unittest 13/13；各副本 selftest 36/0/1 + sweep 27/27；dsh 无契约增量（covenant 文本未变），unit 35/35。

---

## 2026-08-30 修改：wave5 —— 对照 superpowers（obra）：落地 spike 路由 + 任务切分测试，余项多为已覆盖确认

### 来源

克隆 github.com/obra/superpowers 并逐读全部 14 个技能。结论：本 skill 的 C3 计划 / §A4.6 调试四阶段 / §A4.8 TDD / Gate B spec 自审本即衍生自其 writing-plans / systematic-debugging / test-driven-development / brainstorming 自审清单（结构同源），大半内容为已覆盖确认；落地 2 项增量，8 项在案拒绝。

### 修改

- **S1 Spike 路由**（借自 brainstorming 三路径之 spike 支）：§3.1 任务类型表新增一行——可行性问题（"能不能…"）的交付物是答案不是代码；探针计划 2-3 句 → 以正确性允许的最便宜方式求证 → 报告建议（可行/不可行/在什么条件下）；产出代码一律标记 throwaway，**要留 = 新请求**，回 §3.1 重分类（通常 C2）并自带 COV-9 基线，探针代码绝不无门流入生产。全文入 WORKFLOWS_EXTENDED §S1（R9 触发同步扩展）；SKILL.md 表行以 5 处冗余修剪让位（净 -35B → 48,955B）。
- **Task right-sizing**（借自 writing-plans）：C3 任务边界测试——setup/config/脚手架/文档折入交付物所在任务；仅当 reviewer 能有意义地否决一个任务而通过其邻任务时才拆分；每个任务以可独立测试的交付物收尾（REFERENCE.md C3）。
- **在案拒绝**：全路径强制批准门（与 COV-12 AUTO 冲突）、逐节设计批准（与 Gate B 一次性确认冲突）、子代理逐任务执行（破坏验证器连续性/证据环/记忆累积/fresh-run 机检）、git worktree（与基线提交模型冲突）、分支收尾菜单（Class-E + A9 已含）、并行修复代理（证据环单线程为有意设计，记为未来方向）、writing-skills（属 skill-creator 领域）、条件等待（模板 settle sleep 均有注释理由，边际不取）。

验证：baseline partial GREEN 35/36（T6 环境性）→ iter1 与基线完全一致无回归（T11 模板耦合 PASS + 48,955B），sweep 27/27。

---

## 2026-08-30 修改：wave4 —— 借鉴 mattpocock/skills 的五项契约增量（评估后落地）

### 来源

对 github.com/mattpocock/skills（engineering + productivity）六个技能做只读对照评估（to-spec / code-review / grill-me / grill-with-docs / grilling / domain-modeling）。采纳 5 项；拒绝 4 项——issue-tracker 发布与 `ready-for-agent` 标签（外部依赖，违背工件自包含）、spec 禁写文件路径（与 C3 零占位符哲学相反）、双轴并行 reviewer（成本翻倍且与 severity-ranked verdict 冲突）、CONTEXT.md 词汇表（memory topic 文件已覆盖同职能）。

### 修改

- **Test seam**（借鉴 to-spec）：C3 任务块新增测试缝要求——优先已有缝 · 测试在仍能隔离行为的最高缝 · 全代码库缝越少越好（理想 1，缝=测试与内部实现的永久耦合）。SKILL.md C3 紧凑行（字节中性：§A4.9 摘要冗余让位，净 -3B，48,990B）+ REFERENCE.md C3 全文 bullet。
- **Spec-fidelity 三元组**（借鉴 code-review）：A4.9 verdict contract 的 Compliance 维度改为必报三元组——requirements missing/partial · scope creep · looks-implemented-but-wrong，逐条引用判据/spec 原文（TESTING_PROTOCOLS §A4.9，同段三处冗余修剪补偿，净 +110B，46,040B ≤ 45KiB）。
- **Reviewer Smell Baseline**（借鉴 code-review，Fowler《Refactoring》ch.3 十二味）：CODING_PRINCIPLES.md 新章节，含两条约束——repo 文档标准覆盖基线 · 每条 smell 均为 judgement call（跳过工具已强制项）；A4.9 派发 reviewer 时随包携带。
- **Frontier rounds**（借鉴 grilling）：GUIDED 下 ≥2 个 pending Class-I 问题的暂停包升级为分轮访谈——每题编号带推荐答案 · 依赖未决的问题留到后轮 · facts 派子代理自查、只有 decisions 问用户 · frontier 空 = 无静默假设（WORKFLOWS_EXTENDED §P；不改 AUTO 与单点澄清的一次一问）。
- **ADR 三判据**（借鉴 domain-modeling）：§M 增 proactive ADR 准入——hard-to-reverse · surprising-without-context · real-tradeoff 三者俱全才记；强制 Class-I ADR 不受影响。

验证：baseline partial GREEN 35/36（T6 环境性）→ iter1 同基线无回归（T11 模板耦合 PASS + 48,990B），sweep 27/27。

## 2026-08-29 修改：wave3 —— 双模式 + 暂停恢复协议 + 项目画像 + 任务类型扩展

### 问题

两类交互痛点：① 部分卡点（需求模糊/设计门/基线失败/cap-stall）一律停机等人发"继续"，且无恢复协议，"继续"语义不明；② 库/CLI 项目被 assert 组 5 的 start.sh 硬性要求锁死在 exit 1，审计/部署/运维类任务没有工作流。约束：主 skill 不膨胀（48,993B < T11 49000）、编码完成能力不回退。

### 修改

- **COV-12 双模式**：AUTO（默认，Class-I 确认点转 `tests/decisions.md` ADR 后自主继续）/ GUIDED（维持现行为）；Class-E 硬停两模式相同；证据门与模式正交。§A4.11（TESTING_PROTOCOLS）+ §3.4（SKILL）定 ADR/PAUSED 格式与失控界（同子问题 ≥3 ADR 必发暂停包）。
- **§3.4/§P PAUSED 协议**：停必带 `[PAUSED] gate=… | default-if-continue=… | state=…` 包；"继续"= 批准默认选项；§3.3 重入降为轻量（暂停包 + acceptance + 日志尾部）。
- **项目画像**：assert `--profile`/`tests/project_profile.json`（service/backend-api/web-static/cli/library）声明式跳过结构性 N/A 组；`vw-approved` 行内豁免 ⇄ `- secret-approved: <path>` 配对；gate.js 证据路径豁免（tests/memory 首段锚定）+ GATE-BLOCKED 文案前置"写入已成功"。
- **C4-C7 任务类型**（新 companion `WORKFLOWS_EXTENDED.md`，payload 第 10 个 md）：审计只读 / 部署 Class-E 确认 / 运维事故 / 非Web运行时（CLI transcript 证据）。
- **A/B 回归**（deepseek-v4-flash 强制注入）：16 题 BEFORE 15/16 vs AFTER 14/16；polyglot 4 轮均值 BEFORE 87.5% vs AFTER 92.5%（非劣 +2）；SWE 6/6=6/6；112 次运行零冻结。A4.9 评审 Critical/Important 全修 + 复评 ready；断言单测 16/16。
- **四副本 + dsh 传播**：payload 19 文件字节一致；verify_skill coherent（markers 17）；repo `f73684b`、dsh `2e6cd18` 已推送。

## 2026-08-28 修改：AI-native SDLC 加固 —— 完工门内容检查 + 评审结构化（借鉴 Anthropic playbook/CISO 两文）

### 问题

vibeweaver 的任务内纪律很强，但对照 Anthropic《The AI-Native SDLC playbook》(2026-08-21) 与副 CISO 安全文 (2026-07-21) 有三处实质空白：① 完工门只查"证据在不在"，从不查 diff **内容**——凭据提交、测试被悄悄弱化、高风险路径未审，全都裸奔；② A4.9 评审无维度结构、无 nit 上限；③ 无事故复盘模板 / artifact chain 表述 / agent-config 变更重跑规则。另发现 SKILL.md 已被 08-23 编辑顶破 T11 尺寸线（50096B ≥ 49000B 红灯）。

### 修改（P0/P1 范围经用户确认；企业级机制按单用户交互式 skill 裁剪）

- **assert 新增组 14 `secret scan`**：按"每提交补丁"扫描 change-wave diff（净范围会漏掉波内加又删）+ 未跟踪文件整扫；AKIA/私钥块/ghp_/github_pat_/xox/sk-(proj|ant)/JSON 形态 k=v；**引用值豁免**（`os.environ.get`/`process.env`/`config.x`/`self.x` 是安全写法不拦）；占位标记行豁免；`.md` 仅 WARN；永不扫描 assert_artifacts.py 自身。
- **组 15 `test-change guard`**：测试代码文件中被删的断言行（含整文件删除）必须有 `- test-change: <path> — <reason>` 日志理由；写新测试永远自由。
- **组 16 `risk-tier`**：diff/未跟踪文件触及 `auth|security|payment|billing|crypto|migration|permission|acl` 代码路径 → 必须有 `tests/review_package.md`（A4.9 对高风险路径不可跳过）。
- **A4.9 结构化**：发现按 Bugs/Security/Compliance 维度打标；Minor 逐条上限 5 条（余者计数）；新增第 6 步"发现回流规则文件/记忆"；risk-tier 触发器不可跳过。
- **新 §A4.4.3 Artifact Chain**（工件链即审计轨迹）、**APPENDIX §A9 事故复盘模板**（闭环到 A4.8 回归测试 + 记忆 + 可选 standing eval）、REFERENCE C2 Step 6 **agent-config 变更必重跑验证套件**、MEMORY_RULES 跨项目 ⛔ 提升通道、ENGINEERING_STD 生产部署人工确认。
- **A4.9 评审实战**：独立 reviewer 裁决 ready-with-fixes（0 Critical / 4 Important 全修 / Minor 裁定）；修复含删除文件 fail-open、引用值误伤、JSON+现代密钥漏检、@@ 真实行号、健壮性。
- **SKILL.md 减重回绿灯**：修剪第三重冗余（A4.1 Step 0 全树指针化）等 ~1.3KB，50096 → 48978B < 49000；gate-line 模板字节不动（T11 耦合校验 PASS）。

### 验证

TDD 全程：doc-first（§A4.4.1 行 14-16）→ RED（6/8 + 3/11 两轮 watched-failure，证据入 verification_log）→ GREEN 11/11 夹具场景；`tests/assert_artifacts.py --existing` exit 0（15 检查 0 发现）；selftest 35/36（唯一失败 = T6 环境性标定缺失，预先存在）+ sweep 27/27 + T11 PASS；16/16 标记自检。

## 2026-08-23 修改：验证器自适应 —— 多模态模型原生裁判 + 行为探针

### 问题

旧版 vibeweaver 只要装了 mm-sensor 就强制走外部媒体验证，禁用模型自身视觉（self-grading 禁令）。但运行模型本身若支持多模态，直接用它做视觉裁判更快更省；而反过来，**任何模型**（含多模态模型）在拿到"怎么读页面"的指令前，凭一句"页面是否满足要求"做整体判定极其不可靠（幻觉、位置偏差、模态忽视、无法弃权）。

### 修改（SOTA 依据：MJ1 grounded verification chain / WebDevJudge rubric trees / Vision2Web / IRA / CUAAudit）

- **新增 `scripts/mm_probe.py`（stdlib-only 行为探针）**：生成含随机 token+色块的 `tests/probe_vision.png`，模型先 Read 再 `--check` —— 能力由"实际读出像素"证明，**禁止自我声称**（纯文本模型 Read 会直接报错 → 诚实 FAIL）。
- **验证器决策树（COV-5 / §A4.1 Step 0 重写）**：① 自探针 PASS → `Verifier: model-native [image]`，模型用自己的视觉按新协议评审判图；② FAIL + 有 mm-sensor → 原 mm-sensor 流程（`vision.py --probe` + `--detail high`，mm-sensor 模式下 self-grading 仍是违规）；③ 都没有 → `direct read`（此时截图不是证据通道，以 DOM/日志核验为主）。
- **新增 §A4.1.1 Visual Verification Protocol（model-native 模式的强制裁判协议，不可靠性问题的解药）**：观察前置（先逐区域描述再判定）→ 逐标准拆原子声明 → 声明↔观察逐条核对 → **状态类标准强制 DOM/日志交叉核验**（像素证明不了状态）→ **UNCERTAIN=FAIL 弃权制**（禁止猜测）→ 逐标准裁决表（"合格"两个字不算裁决，必须有引证观察/DOM 事实）。
- gate line 增加 `model-native [image]` 模式；自审规则 2、预输出清单、审计 C12 同步三态；mm-sensor 的 Read 禁令仅在 mm-sensor 为验证器时适用（探针图 Read 例外）。
- **配套同步**：vibeweaver-mini §3 探针决策树；mm-sensor description/rules 加工作流作用域例外；TESTING_PROTOCOLS Step 0a 加优先级声明（探针先于任何 mm-sensor 调用）；install.sh/bat 增加 mm_probe.py。

### 验证

`scripts/mm_probe.py` PASS/FAIL 两路实测通过（含真实文本模型 Read 报错 → FAIL 路径）；SKILL.md 50096B——超 49KB 自测线（08-28 波修剪回 48978B 线内）；全库 grep 一致性核对完成；四份副本（系统安装 / dev 树 / open-source 快照 / 本仓库）diff 一致。

## 2026-08-21 修改：RED 锁存会话作用域化 —— 修复跨会话死锁

### 问题（真实故障）

被截断/中止的会话在 final 阶段审计时可能 latch 了 RED（其缓冲文本被 head/tail 截断，或任务未完成就已"完成"），而 `state.roots[root].red` **无会话作用域、无 TTL、只持久化在 `.vibeweaver/audit-state.json`**。后果：

- 新会话的 `write`/`edit` 被上一下留下的 `BLOCKING=yes` 死锁，`tests/**` 之外的文件全部写不了；
- 唯一的解锁路径要求**新会话**自己发出完整 `[Verification Gate]` 完成行，但 mid 阶段（skill 已加载、尚无完成 marker）的 idle 从不重算 red → 新任务在"不能写代码"与"不能合法输出完成行"之间卡死，只能人工 `VIBEWEAVER_AUDIT=off`；
- `tests/**` 豁免只覆盖了顶层 `tests/`，`dev/tests/`（golden 测试）等嵌套测试目录也被锁，连证据修复路径都死锁。

### 判定

latch 拦截本身是**设计**（让 latching 会话自纠）；但"跨会话死锁"是**缺陷**——锁存逃逸出了它本应约束的会话。

### 修改（保持审计牙齿，不削弱任何检查点）

- RED 锁存改为 **session-scoped**：`{ sessionID, ts, bad }`。latching 会话自己继续写 → 仍被拦（自纠闭环不变，T7/T15 回归通过）；**不同会话**首个写入/idle → 自动释放（takeover）；TTL（`redTtlHours`，默认 24h，`audit.json` 可配）兜底；legacy 布尔态（旧格式）立即释放。
- 每次释放**不静默**：记入 `redReleases`（state，有界 5 条）+ app log + 报告 `## Stale RED releases` 段。
- 可写豁免扩到**项目内任意 `test`/`tests` 目录**（`tests/`、`dev/tests/`、`src/test/`…），证据修复路径永不死锁。
- GATE-BLOCKED 文案重写：区分"本会话自纠"与"陈旧锁存自动清除"，不再误导模型等待"会话结束"。

### 验证

`scripts/audit_selftest.mjs` **36 项**全绿（新增 T16 跨会话自动释放 / T17 嵌套 tests 可写 / T18 TTL 兜底 / T19 释放留痕 / T20 legacy 布尔态自愈），`scripts/mutation_sweep.mjs` **27 项**全绿。已对本机两个真实 RED 死锁项目（chatbot、vibeweaver-dsh）经同一代码路径完成迁移释放并留痕。

## 2026-08-19 重大修改：渐进式披露重构 + 机械审计体系

### 修改原因：opencode 工具输出的截断限制（不是 skill 规则）

旧版 `SKILL.md` 是**单文件 79,554 字节 / 1366 行**。opencode 加载 skill 时把整个文件正文作为**一次工具输出**注入上下文，而 opencode 客户端对工具输出有**约 51,200 字节（50KB）的截断上限**——实测在本环境中用 Read 工具读取该文件，输出在第 875 行（51,080 字节）处被截断，返回 `Output capped at 50 KB. Showing lines 1-875`。

后果：模型激活 skill 时只收到前 ~875 行（§1–§A5 中段），§A5.1、Part B/C 工作流、MANDATORY CHECKLIST、Reference Files 索引**全部丢失**。模型的典型第一句话就是 `The skill output is truncated. Let me note the key points:`——它不是幻觉，是真实截断的诚实声明，但也意味着它拿着残缺的契约在干活。

### 修改方案：渐进式披露（progressive disclosure）

依据业界最佳实践重构（Anthropic Agent Skills 官方规范：根文件 <500 行、根作"路由器"、引用一层深、长配套文件加 TOC；SkillJuror 对照实验：渐进式披露让模型实际触及的资源提升 3 倍、任务成功率 +4.1%）：

- **根文件瘦身**：79.5KB → 48.9KB（835 行）。保留激活即需要的绑定契约：11 条 COV 全文、§2 ZERO、§3 模式/记忆、A4 绑定摘要、gate line / 8 列表格规格、核心清单
- **详细协议逐字迁移到配套文件**（内容零删除，章节号不变，交叉引用不断）：
  - `TESTING_PROTOCOLS.md`（33.5KB）：§A4.1 循环全文 · §A4.6 调试 · §A4.7–§A4.10 规范文本
  - `COMPLETION_GATE.md`（28.4KB，新增）：§A4.4 完成输出 · §A4.4.1/§A4.4.2 · §AUDIT 审计协议 · 完整预输出清单
  - `REFERENCE.md`（29.6KB）：Part B/C 工作流全文 · §A5.1 门禁机制
  - `ENGINEERING_STD.md`（10.3KB）：§A6–§A9 全文
- **Read Contract（强制读取契约）**：R1/R1b/R2–R5 触发表——任何代码任务在首个代码动作前必须完整读取 TESTING_PROTOCOLS.md，最终输出前必须读取 COMPLETION_GATE.md，各工作流分支读取 REFERENCE.md 对应章节。配套文件全部 ≤45KB，单次 Read 即可完整返回、不截断
- **截断自愈条款**：根文件顶部声明——若本次注入仍被截断，先 Read 补读到结尾再行动
- **体积守卫**：T11 测试断言根文件 <49KB，防止复发

### 新增：vibeweaver-audit 三层审计体系

audit 插件的核心问题：**skill 的纪律靠模型自律，无法被机器验证**。为此新增 `vibeweaver-audit.js` + 纯核心 `scripts/vibeweaver-audit-core.js`：

| 层 | 机制 | 说明 |
|---|---|---|
| Tier 0 | 被动观察 | 监听 `message.part.updated` / `session.idle` 事件，零模型合作、零 token，记录会话文本与工具调用（有界持久化 `.vibeweaver/audit-state.json`） |
| Tier 1 | 机械三态裁决（OK/BAD/UNCERTAIN） | A 组构件（verification_log/acceptance/媒体/assert 实跑）· B 组 10 项叙述 marker · C 组 15 项声称↔构件交叉核验（Loop/Iterations/Media/E2E/TDD RED/Fresh-run/Code review/Script-only/R-read/Verifier/Baseline/HARD-GATE 值/构件时序）+ C17 skill-absent + C18 na 豁免需理由。BAD → RED 锁存（**绑定产生它的会话**）→ `tool.execute.before` 拦截该会话后续非 test 写入，直至其自纠（修证据 + 修正 gate line，每次 idle/写入都复检）；任何 `test`/`tests` 目录始终可写；跨会话首个写入/idle 或 TTL（默认 24h）自动释放陈旧锁存，全部记入 `redReleases`+app log+报告 `## Stale RED releases`；报告写 `tests/gate_audit.md` |
| Tier 2 | LLM 升级审查 | UNCERTAIN / 确定性抽样 10% / 高风险（≥3 文件或设计文档）→ `escalate=true`，skill 协议要求派 fresh-brain reviewer（复用 §A4.9 契约）对升级包逐项裁决 |

架构依据（2026 SOTA）：OpenAI PRM 过程监督、judge_gate 三态分流（OK/BAD/UNCERTAIN，68% 免费解决、judge 成本占比 50%→16%）、Agent-as-a-Judge（分级：机械过滤 + agent judge 兜底）、agent-org 红队教训（**审计器配置必须放在模型写范围之外**——项目内 `.vibeweaver/audit.json` 被故意忽略，全局配置在 `~/.config/opencode/vibeweaver/audit.json`）。

### 修改后效果（实测）

- **截断消除**：模拟完整 skill 注入输出 49829B < 51,200B（余量 1,371B），模型一次性拿到完整契约
- **内容零丢失**：旧文件 54 个章节标题、47 条长协议句在新结构中 100% 覆盖（脚本核验）；31 个绑定字面 token（gate line、baseline 三行、Design Gate 检查项等）全部单行连续未折断
- **真实会话验证**（expA/expB 端到端 + 真实会话重放校准）：
  - 模型行为教科书级合规（A4.7 循环、TDD RED/GREEN、A4.9 评审、完整 gate line、8 列表格）
  - 审计抓到**真实违规**：`Code review: N/A` 但全文零次 `A4.9 not triggered` 理由；旧协议会话缺 `[Covenant Recall]`/`memory_gate`/`assert` 字段
  - `GATE-BLOCKED` 在真实会话中成功拦截写入，模型读报告后调查
  - 对抗实验（用户明示"不用测试"）：模型完全跳过 skill → 新增 C17 检测此类会话并升级审查
  - 校准消除误报：记录型提交（只动 tests//memory/）不再触发 Fresh-run/时序违规
- **测试体系**：`scripts/audit_selftest.mjs`（36 项 fixture 测试，含真实事件形状回放、红态阻断/解封闭环、跨会话自动释放、TTL 兜底、legacy 态自愈、恶意配置忽略）+ `scripts/mutation_sweep.mjs`（27 项变异扫描——逐项破坏每个检查点验证审计 1:1 捕获，**已借此挖出并修复一个潜伏 bug**：C3 因字符串下标访问从未生效）
- **过程中修复的关键缺陷**（真实会话暴露）：opencode 插件导出契约（每个 export 必须是插件工厂，额外导出会静默禁用整个插件）、event 事件形状（sessionID 在 `properties.sessionID`）、流式文本累计（兼容累计式/增量/去重三种形态）

### 已知边界（设计使然，文档化于 §AUDIT）

- 审计只覆盖加载了 vibeweaver skill 的会话（C17 已收窄"未加载"这一洞为可仲裁的升级项）
- 语义真实性（marker 在但事没做）靠 10% 抽样 + fresh-brain 审查兜底
- 机械层验证的是**过程合规**，不是**结果正确**——用户验收无机械闸门
- 被截断会话的 final 审计可能基于不完整的缓冲文本 latch RED —— 属保守行为，已被"锁存会话作用域化 + takeover/TTL 自动释放 + 全留痕"兜底，绝不死锁后续任务
