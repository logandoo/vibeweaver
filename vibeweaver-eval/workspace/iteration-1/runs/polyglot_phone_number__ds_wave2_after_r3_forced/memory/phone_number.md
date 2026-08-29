---
name: PhoneNumber implementation
description: NANP phone-number cleaning for the PhoneNumber exercism exercise in phone_number.py — validation order, interface, verified behavior
type: fix
date: 2026-08-29
status: ⏳
commit: N/A
last_validated: 2026-08-29
---

# PhoneNumber implementation

**Problem:** `phone_number.py` shipped as a stub (`__init__` empty); hidden test
suite failed 21/21 (RED).

**Implemented behavior (executed-test verified — `tests/verification_run.log`):
25/25 spec cases + hidden pytest suite 21/21 pass.**
- Clean: strip spaces/dashes/dots/parens/`+`; drop a leading `1` country code (11-digit inputs) → 10-digit `.number`.
- Validation order is load-bearing (exact `ValueError` messages asserted by the suite):
  1. letters → `"letters not permitted"`
  2. disallowed punctuation → `"punctuations not permitted"`
  3. <10 digits → `"must not be fewer than 10 digits"`; >11 → `"must not be greater than 11 digits"`
  4. 11 digits not starting with 1 → `"11 digits must start with 1"`
  5. area-code first digit 0/1 → `"area code cannot start with zero/one"`
  6. exchange-code first digit 0/1 → `"exchange code cannot start with zero/one"`
- `.area_code` = first 3 digits; `.pretty()` = `(NXX)-NXX-XXXX` (e.g. `(223)-456-7890`).

**How to apply / edge rules to keep (do not regress):**
- Allowed separators only: digit, space, `.`, `(`, `)`, `-`, `+`; anything else = "punctuations not permitted".
- The letters/punctuation checks run BEFORE digit-count checks (e.g. `523-abc-7890` → letters error, not the 9-digit error).
- Country-code validation only applies to 11-digit inputs (only `1` is valid; `+1`/`1 ` prefixes stripped).

**Failed Approaches / Rejected Alternatives:**
- Single full-match regex for the whole number — rejected: cannot emit the per-rule ordered `ValueError` messages the suite asserts.
- Manual char-by-char filtering — rejected: more code, no benefit over `re.sub(r"\D", ...)`.

**Status:** ⏳ Unverified — executed tests pass; awaiting grader/user validation (no user confirmation in AUTO mode).
