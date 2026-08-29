# Verification Log — two_bucket.measure

## Task: implement two_bucket.measure (Exercism two-bucket kata) | 2026-08-29

- Baseline verified GREEN — stub `two_bucket.py` imports cleanly, `measure(3,5,1,'one')` executes and returns `None` placeholder with exit 0; no existing test suite/build to run (no script/, no tests/ at baseline)

## RED (A4.8 test-first, on baseline stub)

- iter 1 FAIL: diagnosis: stub returns `None` for every input because it contains only `pass`; expected — this is the RED baseline proving the tests bite before implementation. `python3 /tmp/verify_two_bucket.py` → 11/11 failures on stub (9 value cases returned `None`, 2 raise-cases returned `None` instead of ValueError) — recorded `tests/verify_red.run.log`

## GREEN (A4.8, after BFS implementation)

- iter 2 PASS: canonical verification `python3 /tmp/verify_two_bucket.py` → ALL PASS, 9 value cases + 2 ValueError cases (exit 0) — `tests/verify_green.run.log`
- iter 3 PASS: differential sweep vs independent reference BFS `python3 /tmp/diff_sweep.py` → 1152 inputs (b1 1..8 × b2 1..8 × both starts × goals 1..b1+b2), 0 mismatches; reference self-checked against 9 canonical value + 2 canonical raise cases first (exit 0) — `tests/diff_sweep.run.log`
- iter 4 PASS: consumer smoke `python3 /tmp/consumer_smoke.py` → import + 2 value cases + 1 raise case (exit 0) — `tests/consumer_smoke.run.log`
- iter 5 PASS: `python3 -m py_compile two_bucket.py` → OK (exit 0) — covers acceptance criterion 12 (no syntax/runtime errors)
