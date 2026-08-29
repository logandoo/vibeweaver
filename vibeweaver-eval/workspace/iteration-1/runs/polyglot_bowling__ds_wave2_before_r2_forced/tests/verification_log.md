# Verification Log — polyglot_bowling

## Task: polyglot_bowling — implement BowlingGame (roll/score) | 2026-08-29

- Baseline verified GREEN — stub imports cleanly (`python3 import bowling` OK, score() returns None); no pre-existing failures in the tree
- probe: not applicable — backend-only library task (no browser-rendered output); COV-6 §A4.7 test loop replaces the A4.1 Playwright loop; no media captured, verifier = direct-read of executed test results
- iter 1 FAIL: criteria #1-#8 (score() returns None for every game; perfect game != 300) | diagnosis: stub bodies are bare `pass` — no scoring or validation logic exists | changed: bowling.py (stub -> full implementation: roll log + end-of-game frame walk)
- iter 2 PASS: all criteria 1-8 (evidence: tests/grading.log — hidden bowling_test.py suite 31/31 passed, pytest exit 0; inline assertions 31/31 = 16 score + 10 roll-error + 5 score-error cases)
