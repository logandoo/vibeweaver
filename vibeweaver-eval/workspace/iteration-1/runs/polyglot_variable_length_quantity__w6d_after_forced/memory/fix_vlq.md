---
type: reference
status: verified
created: 2026-09-14
---

# VLQ codec implementation

## ✅ Verified
- `encode(numbers)`: for each integer, take lowest 7 bits as final chunk, prepend `(bits & 0x7F) | 0x80` chunks while bits remain, extend result in reversed order (big-endian groups).
- `decode(bytes_)`: `value = (value << 7) | (byte & 0x7F)`; when continuation bit clear, emit `value` and reset. After the loop, raise `ValueError("incomplete sequence")` if the last byte has the continuation bit set.
- Verified 2026-09-14: all 12 prompt examples, empty inputs, multi-value lists, `0xFFFFFFFF` -> `[0x8F,0xFF,0xFF,0xFF,0x7F]`, incomplete-sequence `ValueError` cases, and exhaustive round-trip for `0..2**20-1`. Log: `tests/verification_log.md`.

## Notes
- 32-bit restriction from the prompt; implementation is not bounded and also works for arbitrary-width unsigned integers.
- `[0x7F, 0xFF]` correctly raises `ValueError` (second value incomplete).
