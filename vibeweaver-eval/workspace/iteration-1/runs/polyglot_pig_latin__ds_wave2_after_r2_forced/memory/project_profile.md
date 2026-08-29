---
topic: project_profile
type: project
status: ✅
date: 2026-08-29
---

# Project profile — pig_latin exercise workspace

- Kind: pure Python library module (single-file `translate()`), no UI, no HTTP, no service lifecycle.
- Verifier preset: `direct read (non-web)` (COV-5).
- Lifecycle: no `script/` dir; no build/start/stop needed (COV-2 N/A).
- Workspace constraint: harness-managed eval run dir — untracked subdir of shared repo; agent does not create git commits here (see tests/decisions.md D-2).
- Evidence artifacts live under `tests/` (acceptance.md, verification_log.md, decisions.md) — markdown logs, not test code (harness rule "no test files" read as: no Python test files).
