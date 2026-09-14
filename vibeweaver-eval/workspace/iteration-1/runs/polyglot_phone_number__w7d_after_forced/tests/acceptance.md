> cap=5  stall=3×

# Acceptance Criteria — phone_number.py (NANP cleaning)

1. `PhoneNumber("(223) 456-7890").number` equals `"2234567890"`.
2. `PhoneNumber("223.456.7890").number` equals `"2234567890"`.
3. `PhoneNumber("223 456   7890   ").number` equals `"2234567890"`.
4. `PhoneNumber("12234567890").number` equals `"2234567890"` (leading country code `1` stripped).
5. `PhoneNumber("+1 (223) 456-7890").number` equals `"2234567890"`.
6. `PhoneNumber("2234567890").area_code` equals `"223"`.
7. `PhoneNumber("2234567890").pretty()` equals `"(223)-456-7890"`; same for an 11-digit input.
8. Fewer than 10 digits raises `ValueError("must not be fewer than 10 digits")`.
9. More than 11 digits raises `ValueError("must not be greater than 11 digits")`.
10. 11 digits not starting with `1` raises `ValueError("11 digits must start with 1")`.
11. Letters raise `ValueError("letters not permitted")`.
12. Disallowed punctuation raises `ValueError("punctuations not permitted")`.
13. Area code starting with `0`/`1` raises the matching `ValueError` (also after country-code stripping).
14. Exchange code starting with `0`/`1` raises the matching `ValueError` (also after country-code stripping).
15. `phone_number.py` imports and instantiates with no syntax or runtime errors.
