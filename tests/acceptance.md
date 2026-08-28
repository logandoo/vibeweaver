> cap=5  stall=3×

# Acceptance Criteria — vibeweaver-repo: eval-harness work + four-copy sync (2026-08-29)

1. run_eval.py supports arms ds_forced_before/ds_forced_after and expands $EVAL_ROOT in repo_path — proven by 32/32 executed task runs.
2. grade_swebench.py excludes vibeweaver byproducts from the agent diff — proven by 12/12 swebench grades with patch_applied=True.
3. Four-copy sync completes byte-identical (18 payload files) and origin/main fast-forwards to the sync commit.
