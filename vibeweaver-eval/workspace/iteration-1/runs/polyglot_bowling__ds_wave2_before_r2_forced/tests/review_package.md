# A4.9 Independent Review Package — bowling.py

## Task
polyglot_bowling: implement `BowlingGame.roll/score` (exercism bowling kata).

## Reviewer
Independent read-only subagent (no shared context with implementer), scope = `git diff HEAD~1 HEAD` for the run dir + hidden suite.

## Verdict
**APPROVE-WITH-MINORS** — BLOCKERS: none.

## Findings & Adjudication
1. **MINOR — `IndexError` semantically odd for "game over"/"cannot score yet".** ACCEPTED, no change. Hidden suite uses `assertRaisesWithMessage(Exception)` — any Exception subtype with a non-empty message passes; exercism spec does not dictate the type. IndexError retained (see memory/fix_bowling_score_kata.md rejected alternatives).
2. **MINOR — run copy of `assert_artifacts.py` not byte-identical to canonical.** RESOLVED, no defect. The skill repo's canonical was being edited concurrently by its external author (mtime 20:49, after the 20:46 copy; the `(?![\w.\-])` lookahead change landed mid-session). Copy was identical at copy time; re-synced `tests/assert_artifacts.py` is now byte-identical to the current canonical and still passes all 9 checks (exit 0).
3. **MINOR — acceptance.md criterion 7 omitted the 10th-frame partial-bonus constraint.** FIXED — criterion 7 now enumerates it (e.g. `[0,0]x9 + [10,6]` then roll 10 rejected).

## Reviewer's independent verification (from review task)
- Re-ran hidden suite in temp dir: 31/31 passed.
- Walked every canonical scoring case mentally (81, 300, 17, 20, 31, 26, consecutive spares 31, 20, 26) — all correct.
- Confirmed `_next_roll_context` and the `score()` walk are structurally identical → `"over"` only returned when enough rolls exist (no out-of-bounds path; `[10]*10`/`[10]*11` correctly incomplete).
- Confirmed `strike_bonus_2` partial-frame rule fires (6+10>10 error after `[0,0]x9 + [10,6]`).
- Predicted zero failures; empirically confirmed zero.
- Verified skill artifacts all present and verification_log.md honest.

## Gate status
A4.9 review complete with 0 blockers; minors adjudicated (1 accepted, 1 resolved-as-moot, 1 fixed). Reviewer cleared the implementation for completion.
