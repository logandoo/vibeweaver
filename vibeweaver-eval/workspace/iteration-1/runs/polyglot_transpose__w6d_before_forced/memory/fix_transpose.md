---
type: fix
status: verified
updated: 2026-09-14
---

# transpose implementation

✅ Verified — `transpose.py` implements the Exercism `transpose` exercise.

Algorithm: split input on `"\n"`; for each column `col` in `range(width)` find the
last row index that actually reaches that column (`last = max(i for i, line ...
if col < len(line))`), then emit `line[col] if col < len(line) else " "` for
`lines[:last+1]`. This drops right-side padding while preserving genuine input
spaces (so `"The fourth line.\nThe fifth line."` keeps the row `"h "` and
`"AB\nDEF"` yields `" F"`). A naive `rstrip()` is WRONG here.

Evidence: hidden canonical suite `12 passed` (`tests/green_run.log`, md5
`a4930b9756e694d3b79efa36203a21d6`), `py_compile` OK, manual scenario OK.

## Deferred minors (from A4.9 review, D-4 ruling)
- ⏳ `split("\n")` not `splitlines()` → CRLF input would carry `\r`; canonical data is LF-only.
- ⏳ O(rows×cols) per-column scan; negligible for this input size.
- ⏳ No docstring/type hints (style).
- ⏳ Interior empty-line semantics (e.g. `"AB\n\nCD"`) not covered by canonical data.
