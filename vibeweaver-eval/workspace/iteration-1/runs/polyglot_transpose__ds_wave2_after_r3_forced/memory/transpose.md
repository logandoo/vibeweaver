---
type: project
topic: transpose
status: verified
date: 2026-08-29
---

# Transpose implementation

## Verified (✅)
- Approach A (row-wise column join; padding cell = `" "` when the input row is shorter than the column; then strip only trailing cells whose source row is too short — never strips a real input space) passes 12/12 canonical hidden tests and all prompt.md worked examples.
- Key correctness rule: "pad to the left, don't pad to the right" = missing cells become `" "` at the left/middle of an output row, while trailing cells are dropped ONLY when they are padding (source row shorter than the column) — real trailing spaces in the input survive (e.g. `"The fourth line.\nThe fifth line."` → row `"h "`).
- Edge cases verified: empty string `""` → `""`; blank/trailing empty rows (`"A\n\n"` → `"A"`); interleaved padding in jagged rows (`"  3 56"`); single line → one char per line.

## Notes
- Grader = hidden `transpose_test.py` (Exercism canonical, 12 tests) via `python3 -m pytest -q`.
- Do not create/modify test files in workspace; run suites from /tmp copies.
- `.rstrip()` on output rows would be WRONG — it strips real trailing spaces (fails the `"h "` case); the trailing-strip must be conditioned on the source row being too short.
