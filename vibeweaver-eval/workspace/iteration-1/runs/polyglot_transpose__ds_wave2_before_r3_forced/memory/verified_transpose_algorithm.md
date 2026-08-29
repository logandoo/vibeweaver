# verified: transpose padding-marker algorithm

type: verified
date: 2026-08-29

## Why this approach
A naive `else " "` + `rstrip()` corrupts real trailing spaces (mixed-length case: column 1 is
"h   ", three REAL input spaces that must be kept). Approach: build each output column by walking
rows top→bottom, appending the char when the row is long enough, otherwise a `None` padding marker;
then strip TRAILING `None` markers (don't pad right) and render remaining markers as spaces
(pad left). Verified 12/12 exercism cases + prompt examples on 2026-08-29.

## A4.9 review (independent reviewer, 2026-08-29): APPROVED
No Critical/Important findings. Minors deferred with rulings:
- docstring/type hint on transpose() — ruling: accepted as-is (minimal stub-replacement exercise; no-comment code style).
- readability of `" " if cell is None else cell` — ruling: correct and idiomatic; not worth changing.
- cells strip loop form — ruling: clear, O(cols); not worth changing.
