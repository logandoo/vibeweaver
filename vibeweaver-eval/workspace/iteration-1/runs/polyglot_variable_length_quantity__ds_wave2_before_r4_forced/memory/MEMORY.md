# MEMORY — variable_length_quantity (polyglot exercise)

## Project
- Exercism-style "variable length quantity" (VLQ) exercise. Single module: `variable_length_quantity.py` implementing `encode(numbers)` and `decode(bytes_)`.
- Spec: 7-bit groups, bit #7 set on all-but-last byte, restricted to 32-bit unsigned (encode handles arbitrary ints harmlessly).
- Verified: prompt's 12 encode examples, 5 decode cases, empty/multi-value, incomplete-sequence ValueError, 11 round-trips (tests/verify_iter1.log, verify_iter2.log).

## ✅ Verified
- Bit-manipulation loop (LSB chunks reversed, continuation bit on non-final groups) is correct and simplest.
- Incomplete-sequence detection MUST check the last byte's continuation bit (not just accumulated value) — `decode([0x80])` must raise ValueError; plain `if current:` misses zero-accumulation continuation bytes. (Found by independent review; fixed.)

## ❌ Failed
- (none)

## ⏳ Unverified
- Overlong encodings like `[0x80, 0x00]` decode to `[0]` (accepted; spec doesn't forbid). No input byte-range validation (0–255 masked). Out-of-scope per spec.
