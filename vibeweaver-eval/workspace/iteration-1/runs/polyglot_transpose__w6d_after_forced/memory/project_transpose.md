# Project — transpose exercise

- **Goal:** `transpose(text)` per `prompt.md` (Exercism "transpose").
- **Algorithm:** split on `\n`; for each column, emit chars from row 0 through the
  LAST row that actually owns that column (`len(line) > column`); pad missing
  upper cells with a space. This preserves real trailing spaces (`"h   "`, `"ei "`)
  while dropping only padding below the last owning row.
- **Files:** `transpose.py` (implementation only).
- **Verified:** 14/14 (12 canonical + 2 prompt examples), `tests_verification.log`.

## ✅ Verified
- Canonical Exercism suite 12/12 + both prompt examples pass (iter 1).
- `py_compile` exit 0.

## ❌ Failed
- Left-padding (rjust) + transpose: contradicts canonical expected output. Rejected.

## ⏳ Unverified / Minor (from A4.9 review — deferred)
- CRLF robustness: `split("\n")` leaves `\r` in data (`"AB\r\nCD"` → `"AC\nBD\n\r"`).
  Out of spec (canonical inputs are LF-only); not fixed to avoid over-engineering.
- Perf nit: `max(...)` recomputed per column — O(rows × width). Irrelevant at
  exercise sizes.

## ⛔ Forbidden
- Do not create/modify test files for this exercise (user constraint).
