# Pig Latin translator

## What we built
Implemented `translate(text)` in `pig_latin.py` (Exercism "pig-latin"), replacing
the `pass` stub. Single-pass split-point algorithm in helper `_translate_word`.

## Rules implemented (prompt.md)
1. Vowel / `xr` / `yt` start → append "ay", no shift (apple→appleay, xray→xrayay, yttria→yttriaay).
2. Leading consonant cluster shifts to end + "ay" (pig→igpay, xenon→enonxay — x is a consonant).
3. Consonants + `qu` shift together (queen→eenquay, square→aresquay): when the first
   vowel is `u` preceded by `q`, extend the head by one. `qat→atqay` still shifts only `q`.
4. Consonants + `y` shift; `y` counts as vowel only at index>0 (yellow→ellowyay, my→ymay, rhythm→ythmrhay).

## Key algorithm notes
- Phrase = whitespace split, each token translated, rejoined with single spaces.
- `VOWELS = "aeiou"` (y handled specially, never a member).
- Iteration 2 (second attempt) reached GREEN; iter 1 was the stub baseline (RED, 22 failed).

## Verification
- Grader replica in /tmp: `python3 -m pytest -q pig_latin_test.py` → 22 passed.
- 22-vector standalone CLI check → 0 failures.
- Evidence: tests/grading_run.log, tests/verification_log.md.

## Caveats / open items
- Task forbids creating/modifying test files in workdir → verification runs in /tmp only.
- No memory from prior tasks on this exercise (fresh implementation).
