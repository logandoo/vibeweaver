---
type: project
trust: verified
updated: 2026-09-14
---

# fix_pig_latin — Pig Latin translate

✅ Verified: `pig_latin.py` implements the four Exercism rules with an iterative
consonant scan:
- Rule 1 first: leading vowel, or `xr`/`yt` → append `ay`.
- Scan leading consonants; stop before a `y` that is not the first character
  (Rule 4), or consume a `q`+`u` pair (Rule 3); otherwise Rule 2.
- `translate()` splits on whitespace and joins per-word results.

Edge cases confirmed against `problem-specifications/exercises/pig-latin/canonical-data.json`:
`equal→equalay`, `qat→atqay`, `liquid→iquidlay`, `yellow→ellowyay`,
`rhythm→ythmrhay`, `my→ymay`, `quick fast run→ickquay astfay unray`.

Evidence: 23/23 canonical cases + 6 edge cases pass (`tests/verification_log.md`).

⏳ Deferred Minor (independent review, A4.9): uppercase/mixed-case input is not
normalized (`"Apple"→"eApplay"`). Spec defines lowercase only, so out of scope;
normalize with `.lower()` if case-insensitive input is ever required.
