---
type: fix
updated: 2026-09-14
---

# Fix — Bowling Scoring

✅ **Verified** (iter 1, 9/9 criteria) — `bowling.py:1`.

Approach: append every roll to `self.rolls`; `score()` iterates exactly 10
frames with a roll index. Strike (`rolls[i]==10`): add 10 + next two, advance
1. Spare (`rolls[i]+rolls[i+1]==10`): add 10 + next one, advance 2. Open: add
both, advance 2. The 10th-frame fill balls are consumed naturally by the
lookahead — no special-casing needed.

Verified edge cases (tests/verification_run.log): gutter 0 · all-ones 20 ·
spare+3 16 · strike+3,4 24 · perfect 300 · 10th spare fill 13 · 10th strike
fill 17 · prompt mixed 48.

⚠ **Not implemented** (out of scope per prompt): input validation, partial-game
queries, roll count limits.
