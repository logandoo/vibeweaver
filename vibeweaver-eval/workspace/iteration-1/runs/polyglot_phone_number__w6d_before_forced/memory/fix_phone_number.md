# fix_phone_number

## ✅ Verified
- `phone_number.py` implements `PhoneNumber`: strip `[() +.\-]`, reject letters/punctuation, strip leading country code `1`, validate NXX NXX-XXXX, expose `.number`/`.area_code`/`.exchange_code`/`.subscriber_number`/`.pretty()`.
- Hidden suite (`tasks/polyglot_phone_number/hidden_tests/phone_number_test.py`): 21/21 pass.
- Exact messages: `must not be fewer than 10 digits`, `must not be greater than 11 digits`, `11 digits must start with 1`, `letters not permitted`, `punctuations not permitted`, `area code cannot start with zero|one`, `exchange code cannot start with zero|one`.

## ❌ Failed / rejected directions
- None (single approach passed).

## ⏳ Unverified / deferred (from A4.9 review)
- Non-string input (`None`/int) raises `TypeError` from `re.sub`, not `ValueError` — prompt defines string input; not handled.
- Tabs/newlines are not stripped (only ASCII space); length/messages can be distorted for such input.
- `exchange_code`/`subscriber_number` attributes exposed but not asserted by the hidden suite.

## Notes
- Validation order matters for exact messages: alpha check -> punctuation check -> ASCII check -> length/country-code -> NXX.
- Length checks guarantee exactly 10 digits before indexing `digits[3]` (no IndexError).
