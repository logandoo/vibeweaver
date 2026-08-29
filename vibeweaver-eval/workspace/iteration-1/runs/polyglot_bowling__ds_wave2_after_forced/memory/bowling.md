---
type: project
topic: bowling
status: verified
date: 2026-08-29
---

# Bowling implementation

## Verified (✅)
- Approach A (flat rolls list + `_frame_state()`/`_is_complete()` walkers + `score()` frame-walk) passes 31/31 canonical hidden tests and a 5000-game differential vs an independent frame-object reference (0 mismatches on score, validation parity 0/4000, incomplete-score parity 0/2000).
- Validation rules: pins<0 → ValueError; pins>10 → ValueError; frame total >10 → ValueError (regular frames and 10th-frame strike-bonus second roll); rolling after game over → IndexError; score on incomplete/unstarted/missing-bonus → IndexError.
- 10th frame: fill ball logic — spare → 1 fill, strike → 2 fills, fill balls counted once; XXX → 30.

## Notes
- Grader = hidden `bowling_test.py` (Exercism canonical, 31 tests) via `python3 -m pytest -q`.
- Do not create/modify test files in workspace; run suites from /tmp copies.
