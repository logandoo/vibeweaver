# Verification Log — BowlingGame (polyglot_bowling)

Verifier: direct read (non-web) — pure Python library, no browser-rendered output.
Mode: AUTO. Task type: Modify-Existing (stub → implementation), routed C7 non-web.
Evidence: `tests/verification_run.log` (inline executed test transcript), `bowling.py`.

## Baseline (COV-9)
- Baseline commit: `69311a6 backup: before changes` (scoped to this exercise dir).
- Baseline check: `python3 -c "import py_compile; py_compile.compile('bowling.py', doraise=True)"` → syntax OK; `import bowling` → OK.
- Baseline verified GREEN — no runtime errors; stub `score()` returned `None` (expected, no tests shipped).

## Iterations
- iter 1 PASS: criteria #1-#9 | diagnosis: N/A (first run) | changed: bowling.py (frame-indexed scorer).
  Evidence: `python3 /tmp/vw_bowling_check.py .` → `RESULT: ALL PASS (9/9)`, exit 0. Full transcript in tests/verification_run.log.
  - criterion 1 PASS: score() returns int
  - criterion 2 PASS: gutter = 0
  - criterion 3 PASS: all ones = 20
  - criterion 4 PASS: spare+3 = 16
  - criterion 5 PASS: strike+3,4 = 24
  - criterion 6 PASS: perfect = 300
  - criterion 7 PASS: 10th spare fill = 13
  - criterion 8 PASS: 10th strike fill = 17
  - criterion 9 PASS: prompt mixed = 48

[Convergence] BowlingGame scoring: 1 iter | 9/9 pass | 0 stalls | 0 cap-hits

## A4.9 Independent Review (COV-8)
- Trigger: behavior-semantic change (stub -> scorer); `git diff --stat 69311a6 -- bowling.py` = 1 file, +15/-3.
- Reviewer: read-only opencode task subagent (independent fuzz vs canonical reference: 200,000 random valid games, 0 mismatches).
- Verdict: Strengths = correct frame-indexed scoring + 10th-frame fill balls; no Critical/Important; Minor = no input validation/partial-game handling (prompt states score() called only at game end -> out of contract).
- Adjudication: Minor deferred to memory/fix_scoring.md (out of scope). No Critical/Important -> no re-review round. Rounds used: 1.
