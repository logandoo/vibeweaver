# A4.9 Independent Review Package — phone_number.py

## Task context
Exercise: clean user-entered NANP (North American Numbering Plan) phone numbers
for SMS. Rules from prompt.md:
- Strip punctuation/spacing; 10-digit NANP: area code `NXX` + exchange `NXX` +
  subscriber `XXXX`; `N` = 2-9, `X` = 0-9.
- Optional country code `1` or `+1` prefix may be present; only `1` is valid.
- Output must be the cleaned 10-digit number.

## Files changed (isolated change-wave)
- `phone_number.py` — implemented `PhoneNumber` class (27 lines).
- (support: `tests/acceptance.md`, `tests/verification_log.md`,
  `tests/red_green.log`, `tests/fresh_run.log`, `tests/baseline_import.log`,
  `tests/assert_artifacts.py`, `memory/`)

## Isolated diff (phone_number.py)
```diff
--- a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_phone_number__ds_wave2_before_r3_forced/phone_number.py
+++ b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_phone_number__ds_wave2_before_r3_forced/phone_number.py
@@ -1,3 +1,27 @@
+import re
+
+
 class PhoneNumber:
     def __init__(self, number):
-        pass
+        digits = re.sub(r"\D", "", number)
+
+        if len(digits) == 11:
+            if digits[0] != "1":
+                raise ValueError("11 digits must start with 1")
+            digits = digits[1:]
+
+        if len(digits) != 10:
+            raise ValueError("number must be 10 or 11 digits")
+
+        if digits[0] in "01":
+            raise ValueError("area code cannot start with zero or one")
+
+        if digits[3] in "01":
+            raise ValueError("exchange code cannot start with zero or one")
+
+        self.number = digits
+
+    def area_code(self):
+        return self.number[:3]
+
+    def pretty_print(self):
+        return f"({self.number[:3]}) {self.number[3:6]}-{self.number[6:]}"
```

## Verification evidence (executed)
- `tests/red_green.log`: RED on stub 0/28 → GREEN 28/28 cases pass (prompt
  examples, punctuation/spacing variants, 9/10/11/>11-digit lengths,
  country-code stripping, area/exchange 0-1 prefix rules, area_code(),
  pretty_print()).
- `tests/fresh_run.log`: fresh run on delivered tree 16/16 PASS.
- `tests/assert_artifacts.py --existing --backend-only --profile library`:
  exit 0 (9/9 checks).
