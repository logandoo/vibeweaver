# pig_latin

- type: project
- updated: 2026-08-29
- trust: ✅ Verified (25/25 executed cases pass, `tests/verification_run.log`)

## Implemented behavior (verified)
- Rule 1: leading vowel, or `"xr"` / `"yt"` prefix → append `"ay"` (apple→appleay, xray→xrayay, yttria→yttriaay).
- Rule 2: leading consonant run moved to end, then `"ay"` (pig→igpay, chair→airchay).
- Rule 3: consonant(s) + `"qu"` moved to end as a unit, then `"ay"` (quick→ickquay, square→aresquay).
- Rule 4: consonant run before a medial `"y"` moved to end, then `"ay"` (my→ymay, rhythm→ythmrhay).
- Multi-word phrases: split on whitespace, translate each word, rejoin (quick fast run → ickquay astfay unray).

## Edge rules to keep (do not regress)
- A leading `"y"` is a CONSONANT (yellow→ellowyay); a medial `"y"` after ≥1 leading consonant is a VOWEL (rhythm→ythmrhay).
- `"qu"` after consonants travels with the consonants (square→aresquay); `"q"` not followed by `"u"` is a plain consonant (qat→atqay).
- `"xr"` / `"yt"` prefixes always trigger rule 1 even though they start with consonants.
