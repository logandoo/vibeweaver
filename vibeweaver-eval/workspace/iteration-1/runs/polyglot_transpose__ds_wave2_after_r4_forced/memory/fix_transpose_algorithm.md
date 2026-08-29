---
type: fix
topic: transpose algorithm
status: verified
date: 2026-08-29
---

# fix_transpose_algorithm.md — transpose implementation (✅ Verified)

## Symptom / Problem
`transpose.py` was a stub (`pass`) — no transposition logic.

## Root cause
Starter stub; the exercise requires implementing the transpose of text where
rows become columns.

## Solution (chosen approach)
Position-aware pad markers:
- Split input into rows via `splitlines()` (handles `\n`, empty input, middle
  empty rows).
- For each output row (input column index): walk every input row; take the
  character at that column when present (a real char, possibly a real space),
  else mark a pad position.
- Strip only **trailing pad positions** (`while cells and cells[-1] == "":
  cells.pop()`) — this is the "don't pad to the right" rule.
- Convert remaining interior pad positions to spaces (`cell or " "`) — this is
  the "pad to the left with spaces" rule.
- Real input spaces are stored as `" "` (never the empty marker), so they are
  NEVER stripped — satisfies "all characters from the input must be present in
  the output".

Rejected alternatives: (a) sentinel substitution (exercism canonical) — risks
collision when the input contains the sentinel char (verified: `"a_b"` would be
corrupted); (b) `itertools.zip_longest` + naive `rstrip()` — would destroy real
trailing input spaces (fails `test_mixed_line_length`).

## Verification (✅ Verified)
- `python3 -m py_compile transpose.py` — OK.
- 15/15 canonical+prompt cases pass (12 Exercism canonical tests + 3 prompt
  matrix examples), then 21/21 total including edge sweep, exit 0.
- On-disk evidence: `tests/verification_evidence.txt`.
- Independent review (A4.9): APPROVED, no Critical/Important; 5 Minors
  adjudicated (2 informational-correct, 2 cosmetic declined, 1 accepted and
  applied: `cell or " "`).

## Fix-tracking
- First submission: iter 1 PASS, 15/15 → no FAIL iteration, no diagnosis needed.
