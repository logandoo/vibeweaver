---
type: project
updated: 2026-09-14
---

# pig_latin.py

✅ Verified — `translate(text)` implements all four Exercism pig-latin rules with a single
left-to-right scan (`pig_latin.py`): Rule 1 special-cases vowel / `xr` / `yt`; the scan stops
at the first vowel, consumes `qu` as a unit, and stops at a `y` preceded by ≥1 consonant.
20/20 prompt + edge cases passed (`tests/verification_log.md`).

⏳ Unverified / deferred Minors (from independent review, COV-8):
- whitespace normalization: `split()` + `" ".join` collapses runs of spaces (accepted per spec).
- `_translate_word("")` would IndexError (unreachable via `translate`).
- verification harness lives in a temp path, not the repo (test-file creation was forbidden by the task).
