# Verification Log — bowling.py

- Baseline verified GREEN — skip: no pre-existing runtime/test harness in this workspace (only `bowling.py` stub + `prompt.md`); nothing to baseline-test before the change (COV-9 state-skip).

## BowlingGame implementation (vibeweaver)

- iter 1 PASS: criteria 1-22 | diagnosis: n/a (first implementation) | changed: bowling.py
  - Evidence: `python3 -m py_compile bowling.py` → `SYNTAX OK`.
  - Evidence: canonical Exercism test suite (fetched live from
    raw.githubusercontent.com/exercism/python/.../bowling_test.py, parsed and run
    programmatically, 31/31 tests) → `CANONICAL SUITE: PASS=31 FAIL=0`. Covers criteria 2-21
    (16 score tests: gutter=0, [3,6]*10=90, spare-then-zeros=10, spare-bonus=16, consecutive
    spares=31, last-frame spare bonus=17, single strike=10, strike bonus=26, consecutive
    strikes=81, last-frame strike bonus=18, [10,7,3]=20, XXX=30, [10,10,0,1]=31, [7,3,10]=20,
    perfect=300, [10,10,6]=26; 15 error tests: negative pins, roll>10, frame sum>10,
    10th-frame bonus validation, incomplete/unstarted score, roll-after-complete).
  - Evidence: prompt 3-frame example → `prompt example score: 48` (expected 48) — criterion 22.
  - Scope: single file, `bowling.py`; no UI/HTTP (non-web library task).
  - A4.8 note: logic is exercised test-after via canonical suite (UI/E2E exemption n/a);
    no new test files created per task instruction "Do NOT create or modify any test files".
