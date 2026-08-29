# Review Package — variable_length_quantity (VLQ encode/decode)

## Scope
Single-file implementation of the Exercism "variable-length quantity" exercise
in `variable_length_quantity.py`. The workdir is a fresh exercise scaffold; the
diff is starter-stub → implementation (the whole change; 1 file, +26/-2).

## Acceptance criteria
`tests/acceptance.md` (28 criteria). Hidden grader runs the canonical pytest
suite `variable_length_quantity_test.py` (26 test cases).

## Diff (starter → implementation)
```
diff -u starter/variable_length_quantity.py variable_length_quantity.py
@@ -1,6 +1,32 @@
 def encode(numbers):
-    pass
+    encoded = []
+    for number in numbers:
+        if number == 0:
+            encoded.append(0)
+            continue
+        chunks = []
+        while number:
+            chunks.append(number & 0x7F)
+            number >>= 7
+        for index, chunk in enumerate(reversed(chunks)):
+            if index < len(chunks) - 1:
+                chunk |= 0x80
+            encoded.append(chunk)
+    return encoded
 
 
 def decode(bytes_):
-    pass
+    decoded = []
+    value = 0
+    in_sequence = False
+    for byte in bytes_:
+        value = (value << 7) | (byte & 0x7F)
+        in_sequence = True
+        if byte & 0x80:
+            continue
+        decoded.append(value)
+        value = 0
+        in_sequence = False
+    if in_sequence:
+        raise ValueError("incomplete sequence")
+    return decoded
```

## Key contract details (from prompt.md + hidden tests)
- VLQ: base-128 big-endian; byte bit 7 = "more bytes follow", clear on last byte.
- encode: 32-bit unsigned ints → list of bytes; 0 → [0x00].
- decode: raises `ValueError("incomplete sequence")` when the byte stream ends
  with a continuation bit set — including `[0x80]` where the accumulated value
  is 0 (must track an explicit in_sequence flag, not `value != 0`).
- Numbers restricted to 32-bit unsigned per the exercise spec.

## Verification evidence
- Canonical suite: `26 passed` (tests/pytest_canonical.log)
- Round-trip 2000 random 32-bit values + prompt table + edge cases
  (tests/roundtrip.log)
- TDD RED: `26 failed` against the stub (tests/red_pytest_canonical.log)

## Reviewer verdict (A4.9 dispatch 2026-08-29)
- **Assessment: ready.** No Critical or Important findings.
- 5 Minor findings, all out-of-spec scope-limits or style (recorded in
  memory/verified_vlq.md with rulings — all deferred, none affect the hidden
  canonical grader):
  1. `encode(-1)` would not terminate (Python arithmetic shift) — negative
     input out of contract.
  2. No 32-bit width / byte-range validation on encode/decode — out of contract.
  3. No input-type guards — natural Python TypeError, not contract-required.
  4. `in_sequence = True` ordering slightly redundant — functionally correct.
  5. No docstrings/type annotations — not required.
- Rulings: all Minors deferred to memory; no fixes required before completion.
