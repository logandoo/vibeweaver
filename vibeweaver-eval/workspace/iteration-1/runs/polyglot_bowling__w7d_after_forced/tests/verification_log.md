# Verification Log — Bowling Scorer

Mode: AUTO → Modify-Existing (starter stub present). Verifier: direct read (non-web).
Trusted oracle: `polyglot_bowling/hidden_tests/bowling_test.py` (Exercism canonical suite, 31 tests).

- Baseline (pre-change stub): 31/31 oracle tests FAIL — see tests/evidence/pytest_bowling_baseline.txt.
- COV-9 skipped — Modify-Existing task starts from an unimplemented stub, so a GREEN pre-change baseline is structurally impossible; the pre-change RED baseline is recorded above instead.
- iter 1 PASS: implemented `BowlingGame` in `bowling.py` as a frame-based state machine with per-roll validation; oracle run from an isolated temp dir — 31/31 tests pass. Evidence: tests/evidence/pytest_bowling_after.txt.
- iter 1 PASS: `python3 -m py_compile bowling.py` exit 0 (syntax gate).
- iter 1 PASS: boundary coverage — negative roll, roll > 10, frame sum > 10, 10th-frame fill-ball rules, score-on-unstarted/incomplete, and roll-after-complete are each exercised by the oracle (31 cases, tests/evidence/pytest_bowling_after.txt).
- iter 2 PASS: end-to-end grade harness — `grade_polyglot.py` reported passed=true with 31/31 (tests_passed=31, tests_total=31).
- iter 2 PASS: independent reviewer (fresh context) differential-fuzzed 115,552 games and exhaustively swept all 1,464 tenth-frame sequences — 0 mismatches, verdict APPROVE. Package: tests/review_package.md.
