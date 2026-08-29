> cap=5  stall=3×
1. `PhoneNumber("+1 (613)-995-0253").number` equals `"6139950253"`.
2. `PhoneNumber("613-995-0253").number` equals `"6139950253"`.
3. `PhoneNumber("1 613 995 0253").number` equals `"6139950253"`.
4. `PhoneNumber("613.995.0253").number` equals `"6139950253"`.
5. Cleaning strips dots, spaces, dashes, parentheses and a leading `+1`/`1` country code (e.g. `"223 456   7890   "` → `"2234567890"`).
6. An 11-digit input starting with `1` drops the country code and yields the 10-digit number.
7. Inputs that reduce to fewer than 10 digits (e.g. 9 digits, letters, stray punctuation) raise `ValueError`.
8. An 11-digit input not starting with `1` raises `ValueError`.
9. Inputs with more than 11 digits raise `ValueError`.
10. Area code (first 3 digits) starting with `0` or `1` raises `ValueError` — also when it follows a stripped country code.
11. Exchange code (digits 4-6) starting with `0` or `1` raises `ValueError` — also when it follows a stripped country code.
12. `phone_number.py` imports and instantiates without syntax or runtime errors.
