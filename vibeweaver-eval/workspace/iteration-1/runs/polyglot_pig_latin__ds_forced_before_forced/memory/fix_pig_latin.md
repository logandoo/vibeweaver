---
name: Fix Pig Latin translate
description: Implemented Exercism pig-latin translate(text) in pig_latin.py — single-pass prefix scan approach; all 23 canonical cases pass
type: fix
date: 2026-08-29
status: ⏳
commit: N/A (eval workspace — no commit made; parent repo is the harness's)
---

# Fix: Pig Latin `translate(text)`

**Problem:** Starter stub `translate(text)` body was `pass`, returning None for every input.

**Attempted Fix:** Single-pass prefix scan (stdlib only). For each word: Rule 1 if it starts
with a vowel or `xr`/`yt` → append "ay"; else find the first index where the char is a vowel
or a non-initial `y`, treating a `u` immediately preceded by `q` as a consonant (keeps the
`qu` cluster in the prefix) — split at that index, move the prefix to the end, append "ay".
Phrases are split on whitespace and each word translated independently.

**Rejected Alternatives:**
- Regex rule-table (4 ordered patterns for qu / y / etc.) — more readable but adds
  branch-ordering pitfalls and regex cost for the same output; rejected for simplicity.
- Helper-function decomposition (`first_vowel_index()`) — same behavior, extra indirection.

**Review note (A4.9 Minor, accepted):** vowel-less fallback `return word + "ay"` (e.g.
`nth`→`nthay`) is an unspecified-but-reasonable extension consistent with rule-1 form;
kept intentionally. No Critical/Important findings from independent review.

**Files:** `pig_latin.py`

**Status:** ⏳ Pending — graded by hidden canonical tests (`tasks/polyglot_pig_latin/hidden_tests/pig_latin_test.py`); local verification 23/23 canonical cases + 4/4 edge cases pass (tests/verification_output.log).
