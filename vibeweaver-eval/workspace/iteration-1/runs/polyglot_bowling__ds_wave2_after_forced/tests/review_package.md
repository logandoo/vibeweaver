# A4.9 Independent Review Package

Wave: `796962b..0314ec9` (bowling implementation, behavior-semantic new feature — review dispatched).
Reviewer: independent read-only subagent (`general`), verdict contract applied over `git diff 796962b..HEAD -- bowling.py`.

## Findings & Adjudication

| # | Severity | Dimension | Finding (file:line) | Ruling |
|---|----------|-----------|---------------------|--------|
| M1 | Minor | Quality | `_frame_state()` returns `ball = len(frame_rolls) + 1` (next-ball semantics) gated on `ball >= 2`; works but naming is confusing | Accepted — deferred to memory; no functional impact, keep YAGNI minimal code |
| M2 | Minor | Quality | Frames 1-9 walk duplicated in `_frame_state()` and `_is_complete()` | Accepted — deferred to memory; single shared walker would reduce duplication but risks behavior churn on a passing, fully-verified implementation |
| M3 | Minor | Quality/Compliance | Pin-range checks run before game-over check, so `roll(-1)`/`roll(11)` on finished game raises ValueError not IndexError; both are Exception, tests pass | Accepted — deferred to memory; canonical suite asserts only Exception, current order is defensible |
| M4 | Minor | Quality | `roll()` performs two walks per call; negligible at ≤21 rolls | Accepted — deferred to memory; performance irrelevant at this scale |

## Verdict
APPROVE — 0 Critical, 0 Important, 4 Minor (quality, no functional impact). Reviewer independently re-ran 31 canonical tests (pass) and 400k fuzz sequences vs a reference (zero mismatches).

## Recording
Minors deferred to memory/MEMORY.md (see D-notes below). No code changes required.
