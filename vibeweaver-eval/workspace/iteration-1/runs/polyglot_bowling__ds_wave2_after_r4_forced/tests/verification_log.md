# Verification Log — bowling.py (ten-pin bowling scoring)

## Task: implement BowlingGame.roll/score per prompt.md

- Baseline verified GREEN — run-once import check of existing stub (`import bowling` OK, `score()` returned None as expected from stub). Commit `e6b3f14 backup: before changes`.

- iter 1 FAIL: criterion 2 | diagnosis: test harness fed an incomplete 3-frame game (5 rolls) to score(), whose 10-frame walk ran past the roll list (IndexError); code itself not implicated | changed: (test data only, corrected to full 10-frame games)
- iter 2 PASS: criteria 1–8 | evidence: inline python3 invocation transcript (9/9 cases), all expected scores matched: prompt example=48, perfect=300, gutter=0, 10th X1/=20, 10th XXX=30, 10th 5/7=17, all-spares=150, two strikes+open=47, mixed=44 | changed: bowling.py (final tree)
- fresh-run check PASS: `python3 -m py_compile bowling.py` -> compile OK; fresh perfect-game run -> 300 on the exact delivered tree.
- code review (A4.9): independent reviewer APPROVE — 0 Critical / 0 Important; 4 Minor findings adjudicated (type annotations cosmetic; incomplete-game IndexError out of scope per spec "score() called only at game end"; no pin validation not required; frame-10 rolls[i+2] safe for all valid games) -> deferred to memory, no fixes required.
