> cap=5  stall=3×

# Acceptance Criteria — polyglot_pig_latin (Exercism "pig-latin")

Implement `translate(text)` in `pig_latin.py` per the four rules in `prompt.md`.
Grading runs `python3 -m pytest -q pig_latin_test.py` against the injected hidden
test suite (canonical Exercism tests). The task prohibits creating or modifying
test files inside the workdir; verification therefore runs the canonical suite in
a `/tmp` replica of the grader.

| # | Criterion | Check | Status |
|---|-----------|-------|--------|
| 1 | Word starting with a vowel → `word + "ay"` (apple→appleay, ear→earay, igloo→iglooay, object→objectay, under→underay) | | |
| 2 | Word starting with `xr` or `yt` → `word + "ay"` (xray→xrayay, yttria→yttriaay) | | |
| 3 | Word starting with one+ consonants → shift consonant cluster to end + `ay` (pig→igpay, koala→oalakay, chair→airchay, school→oolschay, therapy→erapythay, thrush→ushthray, xenon→enonxay) | | |
| 4 | Word starting with 0+ consonants followed by `qu` → shift consonants+`qu` + `ay` (queen→eenquay, square→aresquay, quick→ickquay) | | |
| 5 | Word starting with one+ consonants followed by `y` → shift consonants + `ay`, `y` acts as vowel only after index 0 (my→ymay, rhythm→ythmrhay, yellow→ellowyay) | | |
| 6 | `q` without following `u` still shifts (qat→atqay); vowel-start overrides `qu` handling (equal→equalay) | | |
| 7 | Multi-word phrases: split on whitespace, translate each word, rejoin with single spaces (quick fast run→ickquay astfay unray) | | |
| 8 | Hidden test suite passes: `python3 -m pytest -q` in grader replica → 22 passed | | |

## Definition of Done

- [ ] C1–C8 all PASS, evidenced by the canonical hidden suite run in a `/tmp`
      grader replica (full 22-vector coverage) plus a standalone CLI run.
- [ ] No `test_*.py` / `*_test.py` created inside workdir (pytest-collectible).
- [ ] `tests/verification_log.md`, `tests/decisions.md`, `memory/` updated; 
      `tests/assert_artifacts.py` passes.
