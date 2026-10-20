> cap=5  stall=3×

# Acceptance Criteria — vibeweaver-repo: eval-harness work + four-copy sync (2026-08-29)

1. run_eval.py supports arms ds_forced_before/ds_forced_after and expands $EVAL_ROOT in repo_path — proven by 32/32 executed task runs.
2. grade_swebench.py excludes vibeweaver byproducts from the agent diff — proven by 12/12 swebench grades with patch_applied=True.
3. Four-copy sync completes byte-identical (18 payload files) and origin/main fast-forwards to the sync commit.

# Acceptance Criteria — README 首段重写（科学方法隐喻，双语）

1. README_zh.md 首段：意识流→科学方法（预注册/双盲评审/实验台账/可复现）→ vibeweaver 机制映射（判据预注册/盲审/台账蒸馏/机械拦截），保留原签名句。
2. README.md 英文同构镜像，结构一致。
3. 机制映射全部有实物依据（§A4.1 Step1 / A4.9+FCV / verification_log+working_note→memory/ / GATE-BLOCKED）；lint 不新增事实类告警。

# Acceptance Criteria — EN 段落可读性重写（wave20b）

1. README.md Why 章开头两段改为地道英文（去直译腔），信息不变。
2. lint 对比无新增罚分；verify_skill 绿。

# Acceptance Criteria — README benchmark 代际标注 + 可渲染流程图（2026-10-20）

Source: user report 2026-10-20 (benchmark section stale? mermaid not rendering) → option A chosen: compress + generation labels.

1. 双语 README 的每个 benchmark 表都带 skill 代际标签（G1/G2/G3）；显式写明当前安装包（G3）尚无 16-task 轮次；删除「当前 skill」「Best config / 最优形态」等已失效措辞。
2. 旧表全部 n/16 数字保留且中英一致（两文件 token 集合相同）；英文 benchmark 段从 268 行压到 ≤150 行。
3. 两个 README 不再包含 ```mermaid 代码块，改为提交到仓内的 SVG 流程图 + 可编辑 .mmd 源文件；SVG 经 mmdc 渲染 exit 0，截图在 900px 宽度下可读。
