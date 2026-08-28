# phone_number

- type: project
- updated: 2026-08-29
- trust: ✅ Verified (hidden pytest suite 21/21 pass; `tests/verification_run.log` 25/25)

## Implemented behavior (verified)
- Clean: strip spaces/dashes/dots/parens/`+`; drop a leading `1` country code (11-digit inputs) → 10-digit `.number`.
- Validation order is load-bearing (exact `ValueError` messages asserted by the suite):
  1. letters → `"letters not permitted"`
  2. disallowed punctuation → `"punctuations not permitted"`
  3. <10 digits → `"must not be fewer than 10 digits"`; >11 → `"must not be greater than 11 digits"`
  4. 11 digits not starting with 1 → `"11 digits must start with 1"`
  5. area-code first digit 0/1 → `"area code cannot start with zero/one"`
  6. exchange-code first digit 0/1 → `"exchange code cannot start with zero/one"`
- `.area_code` = first 3 digits; `.pretty()` = `(NXX)-NXX-XXXX` (e.g. `(223)-456-7890`).

## Edge rules to keep (do not regress)
- Allowed separators only: digit, space, `.`, `(`, `)`, `-`, `+`; anything else = "punctuations not permitted".
- The letters/punctuation checks run BEFORE digit-count checks (e.g. `523-abc-7890` → letters error, not the 9-digit error).
- Country code validation only applies to 11-digit inputs (only `1` is valid; `+1`/`1 ` prefixes stripped).
