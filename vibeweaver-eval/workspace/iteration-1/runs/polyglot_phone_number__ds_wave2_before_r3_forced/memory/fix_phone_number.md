---
type: fix
status: verified
topic: phone-number
---

# fix_phone_number — NANP phone number cleaning

## Symptom
Stub `phone_number.py` returned nothing; any attribute access raised
AttributeError.

## Root cause
Starter stub had an empty `__init__` (`pass`).

## Solution (validated)
1. `re.sub(r"\D", "", number)` strips all non-digit punctuation/spacing.
2. If 11 digits and first digit is `1`, drop the country code; if 11 digits
   and first digit is not `1` → `ValueError`.
3. Length != 10 after that → `ValueError`.
4. `digits[0] in "01"` (area code) and `digits[3] in "01"` (exchange code)
   → `ValueError`.
5. Expose cleaned value as `self.number`; add `area_code()` (first 3) and
   `pretty_print()` → `(NXX) NXX-XXXX`.

## Verification
- RED: 0/28 battery cases on stub (AttributeError).
- GREEN: 28/28 cases pass — prompt examples, punctuation/spacing variants,
  digit-length edge cases, country-code stripping, area/exchange 0-1 rules
  (`tests/red_green.log`).

## Trust
✅ Verified — independent of exercise harness; matches canonical NANP rules.
