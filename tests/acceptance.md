> cap=5  stall=3×

# Acceptance Criteria — vibeweaver-repo: eval-harness work + four-copy sync (2026-08-29)

1. run_eval.py supports arms ds_forced_before/ds_forced_after and expands $EVAL_ROOT in repo_path — proven by 32/32 executed task runs.
2. grade_swebench.py excludes vibeweaver byproducts from the agent diff — proven by 12/12 swebench grades with patch_applied=True.
3. Four-copy sync completes byte-identical (18 payload files) and origin/main fast-forwards to the sync commit.

# Acceptance Criteria — README 首段重写（科学方法隐喻，双语）

1. README_zh.md 首段：意识流→科学方法（预注册/双盲评审/实验台账/可复现）→ vibeweaver 机制映射（判据预注册/盲审/台账蒸馏/机械拦截），保留原签名句。
2. README.md 英文同构镜像，结构一致。
3. 机制映射全部有实物依据（§A4.1 Step1 / A4.9+FCV / verification_log+working_note→memory/ / GATE-BLOCKED）；lint 不新增事实类告警。
