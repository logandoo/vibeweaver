# MEMORY — polyglot_bowling

## Project
- Exercism-style single-file exercise: `bowling.py` implements `BowlingGame` with
  `roll(pins)` and `score()`.
- No build system, no service lifecycle, no UI/HTTP. Verifier: direct read (non-web).

## ✅ Verified
- `bowling.py` scoring algorithm (rolls list + 10-frame index walk with strike/spare
  lookahead) passes 9/9 inline assertions plus two-strike lookahead: gutters=0,
  all-spares=150, perfect=300, prompt example=48, 10th-frame fill cases.
- `python3 -m py_compile bowling.py` → exit 0.

## ⛔ Forbidden / Constraints
- Do NOT create or modify test files for this exercise.
- Do NOT run repo-wide `git add -A`; workspace sits inside the parent eval repo.
