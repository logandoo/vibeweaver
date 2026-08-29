# A4.9 Independent Review Package

Reviewer: independent general agent (no knowledge of implementation history).
Reviewed artifact: change-wave diff to `variable_length_quantity.py` (stub → VLQ
implementation) plus tests/canonical_suite.log and tests/differential_check.log.

## Scope
The reviewer received only the diff, final solution, and evidence logs. It ran its
own adversarial verification in an isolated scratch dir:
- `python3 -m py_compile` OK
- 10 spec assertions (prompt examples, max 32-bit, multi-value order, incomplete-sequence
  ValueError incl. `[0x80]`, empty inputs, round-trip over 1000 sequential + boundaries)
- adversarial checks: `decode([0x80,0x00])==[0]`, `encode(0x7F)`, `encode(0x80)`,
  `decode([0x00,0x81,0x00])==[0,0x80]`, byte-range validation, exhaustive round-trip over
  5258 values — all passed

## Verdict
APPROVE — no Critical or Important findings.

## Findings
- Minor (no change): `chunks.insert(0, …)` is O(n) per call; bounded by 5 chunks (32-bit) — negligible.
- Minor (no change): decode's `if value or (bytes_ and bytes_[-1] & 0x80)` is a redundant but
  harmless double condition; the second clause is required for the zero-accumulation case `[0x80]`.

## Diff reviewed
```
def encode(numbers):
-    pass
+    encoded = []
+    for number in numbers:
+        chunks = []
+        chunks.append(number % 0x80)
+        number //= 0x80
+        while number:
+            chunks.insert(0, number % 0x80 + 0x80)
+            number //= 0x80
+        encoded.extend(chunks)
+    return encoded


def decode(bytes_):
-    pass
+    numbers = []
+    value = 0
+    for byte in bytes_:
+        value = (value << 7) | (byte & 0x7F)
+        if byte & 0x80:
+            continue
+        numbers.append(value)
+        value = 0
+    if value or (bytes_ and bytes_[-1] & 0x80):
+        raise ValueError("incomplete sequence")
+    return numbers
```
