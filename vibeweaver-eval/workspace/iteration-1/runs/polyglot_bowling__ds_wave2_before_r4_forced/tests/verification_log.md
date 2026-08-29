# Verification Log — Bowling Game (polyglot_bowling)

## Task: Bowling Game scoring | 2026-08-29

- Baseline verified GREEN — stub `bowling.py` (e6b3f14) imports and runs inertly; `score()` returns None, no pre-existing failures. Backup commit `bcfd72d` (COV-9).
- probe: verifier not applicable — pure-library logic, no UI/runtime-rendered output; Playwright capture loop N/A (COV-4 skip reason: no browser output). Verification = executed tests with on-disk logs (§A4.8 TDD + full hidden-suite run).

- iter 1 FAIL: criteria 1-11 (28/31 hidden tests error during roll()) | diagnosis: _build_frames conflated "structurally invalid" with "game incomplete" — roll() rejected valid in-progress prefixes because fewer than 10 frames returned None; _build_frames belongs to completeness checks (score()/_game_over), roll() needs a prefix validator | changed: bowling.py — added _valid_prefix for roll() validation; _build_frames kept for score()/_game_over — RED evidence in tests/pytest_red.log
- iter 2 PASS: all criteria 1-11 (31/31 hidden tests OK in 0.002s) — evidence: tests/pytest.log; plus fresh inline spot-checks: prompt example X|5/|90=48, perfect game=300, all zeros=0, no strikes/spares=90, 10th-frame 7,3,10=20 / 10,10,10=30 / 10,7,3=20, and error paths (frame sum>10, score unstarted/incomplete, 2nd-bonus-strike-after-non-strike, roll after game over, negative pins, pins>10) | scope: full exercism canonical-data suite + prompt examples | changed: bowling.py
