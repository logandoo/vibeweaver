# Acceptance Criteria

> cap=5  stall=3×
> Source: `prompt.md` (task spec) + ground-truth grading suite `../../tasks/polyglot_phone_number/hidden_tests/phone_number_test.py` (interface + exact ValueError messages). Prompt examples are criteria #1–#4.
1. `PhoneNumber("+1 (613)-995-0253").number` returns `"6139950253"` (country code `+1` and punctuation stripped).
2. `PhoneNumber("613-995-0253").number` returns `"6139950253"` (dashes stripped).
3. `PhoneNumber("1 613 995 0253").number` returns `"6139950253"` (leading `1` country code + spaces stripped).
4. `PhoneNumber("613.995.0253").number` returns `"6139950253"` (dots stripped).
5. `PhoneNumber("(223) 456-7890").number` returns `"2234567890"` (parens stripped).
6. `PhoneNumber("223 456   7890   ").number` returns `"2234567890"` (multiple spaces + trailing whitespace stripped).
7. `PhoneNumber("12234567890").number` returns `"2234567890"` (11 digits with leading `1` → country code dropped).
8. 9 digits raise `ValueError("must not be fewer than 10 digits")`.
9. 11 digits not starting with `1` raise `ValueError("11 digits must start with 1")`.
10. More than 11 digits raise `ValueError("must not be greater than 11 digits")`.
11. Inputs containing letters raise `ValueError("letters not permitted")`.
12. Inputs containing disallowed punctuation (`@:!`) raise `ValueError("punctuations not permitted")`.
13. Area code starting with `0` raises `ValueError("area code cannot start with zero")` (also for 11-digit inputs).
14. Area code starting with `1` raises `ValueError("area code cannot start with one")` (also for 11-digit inputs).
15. Exchange code starting with `0` raises `ValueError("exchange code cannot start with zero")` (also for 11-digit inputs).
16. Exchange code starting with `1` raises `ValueError("exchange code cannot start with one")` (also for 11-digit inputs).
17. `PhoneNumber("2234567890").area_code` returns `"223"`.
18. `PhoneNumber("2234567890").pretty()` returns `"(223)-456-7890"`; `PhoneNumber("12234567890").pretty()` returns `"(223)-456-7890"`.
19. `phone_number.py` imports and runs with no syntax or runtime errors.
