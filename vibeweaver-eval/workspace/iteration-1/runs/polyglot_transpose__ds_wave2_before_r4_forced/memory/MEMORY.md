# MEMORY.md — transpose exercise workspace

## Project
- Minimal coding-exercise workspace: `prompt.md` (task), `transpose.py` (implementation), `run.log` (transcript). No `script/`, no config, no test runner.

## Verified
- ✅ transpose(text): column-wise transpose where the trailing **padding** cells (rows whose length <= column index, at the bottom of each output row) are stripped, but **real** trailing spaces from the input are preserved. This distinction is the key non-obvious requirement (canonical cases like `"h   "`, `"ei "`, `" .n"`, `"  "`).
- ✅ Algorithm validated against all 12 Exercism canonical cases (tests/transpose_verify_green.log).

## Constraints (from eval harness)
- Do NOT create or modify test files.
- Do NOT commit (no backup commit either).
- Keep function signature `transpose(text)`.
