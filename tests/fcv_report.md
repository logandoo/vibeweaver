# FCV report — W2-ISO（fresh-context verify，2026-10-23）

独立 fresh-context 复核：重跑 `tests/fcv_brief.md` 的命令序列，逐条判据给出观察证据。
本文件为该复核的归档 + 唯一失败项的二次复核结论。

## 逐判据结论（fresh-context，原样归档）

- `criterion #45: PASS` — `/tmp/fcv-mock/isolation.json`: `"work_files": ["hello.txt"]`，
  `sandbox_outside_work` 只有 `home/.cache|config|local/...` 运行态（无 `hello.txt`），
  `"host_repo_delta": []`，`"violations": []`；`test_mock_agent_isolated_hidden_test_outside … ok`；
  `test_contamination_fails_closed … ok`（断言 `verdict == "indeterminate"`）；干净 mock 运行 `verdict: pass`。
- `criterion #46: PASS` — stub 回执 `VW-STUB cwd=… pwd=… home=… argv=…` 经 `realpath` 比较都指向 worktree；
  `test_agent_binds_to_worktree_despite_stale_pwd … ok`；真实运行 `/tmp/fcv-real/trajectory.json`：
  `"cwd": "…/vw-eval-s05hkua4/work"`，`"cmd": "opencode run --standalone … /…/work Create a file named hello.txt …"`，
  且 `--format json` 的 `tool_use` 里 `"path": "/private/var/folders/…/work/hello.txt"`。
- `criterion #47: PASS` — `diff /tmp/fcv_before.txt /tmp/fcv_after_mock.txt` → `DIFF_EXIT=0`；
  `diff /tmp/fcv_before.txt /tmp/fcv_after_real.txt` → `DIFF_BEFORE_EXIT=0`（宿主 repo 零新增）；
  mock/real `isolation.json` 均 `"host_repo_delta": []`、`"violations": []`，任务产物只在 `work_files`；
  fail-closed 源码：`if iso["violations"]: verdict = "indeterminate"`。
  （备注：`work/` 之外存在文件 = 临时 HOME 的运行态；判据的「零写入」指任务产物与宿主树。）
- `criterion #48: PASS` — `/tmp/fcv-real` 产出 4 个 json；`verdict.json`: `"verdict": "pass"`、
  `"hidden_test": {"exit": 0, "output": "PASS: hello.txt\n"}`、`"agent_exit": 0`、`"isolation_violations": []`；
  三值映射由 `test_verdict_three_valued` / `test_setup_failure_is_indeterminate` /
  `test_subject_cannot_forge_setup_failure` / `test_hidden_test_capture_failure_is_indeterminate` 钉住；
  隐藏测试只在评分时从 lab 执行（`work_files` 无 `smoke_test.py`）。
- `criterion #49: PASS` — `trajectory.json`: `"home": "…/vw-eval-s05hkua4/home"`（≠ 宿主 `~`），`"stderr": ""`
  （无 `GATE-BLOCKED` 噪音）；`isolation.json` 显示沙箱 HOME 只有 `opencode.jsonc` + auth/cache/db，**无 `plugins/`**。

## 二次复核（唯一失败项：命令 9）

原复核在命令 9 `python3 tests/assert_artifacts.py --existing --json` 上 exit 1（15b 证据封条 stale，
因封条尚未重跑——属收尾步骤）。封条重跑后由**另一个 fresh-context 代理**复核：

```
criterion #9 (assert_artifacts --existing): PASS — evidence: {"ok": true, "passes": 34, "fails": []} / EXIT=0
criterion #9b (evidence_seal --check): PASS — evidence: evidence_seal.py: seal VERIFIED / EXIT=0
```

## 结论

`FCV verdict: pass`（#45-#49 逐条 PASS，命令 9/9b 复核 PASS）。
