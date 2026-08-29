---
topic: fix_pig_latin_translate
type: fix
status: ⏳
date: 2026-08-29
commit: N/A
---

# Fix tracking — pig_latin.translate

## Problem
Stub `def translate(text): pass` returned None for every input. Prompt.md defines the 4-rule Exercism Pig Latin algorithm.

## Symptom
`translate('apple')` -> None (expected 'appleay'); all 21 harness cases returned None (RED: 0/21).

## Root cause
No translation logic existed (stub).

## Solution
Character-scan algorithm: rule-1 prefix (vowel / xr / yt) -> +ay; else scan from index 1 for first vowel or 'y', shift split past a 'q'u boundary, move prefix to end +ay; multi-word join with single space.

## Verification
- Inline harness (not a saved test file): 21/21 prompt+canonical cases pass; edge sweep 9/9 pass (incl. xylophone, yes->esyay, queen->eenquay, squir+).
- py_compile + import clean.
- A4.9 independent review: Assessment ready (0 Critical / 0 Important / 5 Minor deferred).

## Deferred Minors (A4.9)
1. word[0] indexing assumes non-empty token (safe post-split) — guard if refactored.
2. for...else + split pattern slightly clever — comment if touched.
3. No module-level docstring (stylistic).
4. Whitespace-only input collapses (out of scope).
5. All-consonant words return word+"ay" (undefined by spec; reasonable).

## Status
⏳ Unverified — awaiting grader/hidden-test confirmation before promotion to ✅ Verified.
