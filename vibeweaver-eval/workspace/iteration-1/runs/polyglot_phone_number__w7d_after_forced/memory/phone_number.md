---
topic: phone_number
type: fix
status: unverified
updated: 2026-09-14
---

# phone_number.py — NANP cleaning

## ✅ Verified
- `PhoneNumber(number)` stores the cleaned 10-digit string in `.number` and the first
  three digits in `.area_code`; `.pretty()` returns `"(NXX)-NXX-XXXX"`.
- Cleaning removes `()`, `.`, `+`, `-`, and whitespace via `re.sub(r"[().+\-\s]", "", number)`.
- Validation order (exact messages, canonical Exercism):
  1. letters → `letters not permitted`
  2. other non-digits → `punctuations not permitted`
  3. `< 10` digits → `must not be fewer than 10 digits`
  4. `> 11` digits → `must not be greater than 11 digits`
  5. 11 digits not starting with `1` → `11 digits must start with 1`
  6. area code starts `0`/`1` → `area code cannot start with zero|one`
  7. exchange code starts `0`/`1` → `exchange code cannot start with zero|one`
- Evidence: `tests/verification_run.log` GREEN — 21/21 canonical tests pass.

## ⏳ Unverified
- Grader/hidden-suite confirmation on the delivered tree.

## ❌ Failed / avoided
- None.

## Notes
- Single file, no build/service lifecycle → COV-2 na; COV-9 commit skipped (shared eval repo).
