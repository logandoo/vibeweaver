> cap=5  stall=3×

# Acceptance Criteria — Variable Length Quantity (encode/decode)

1. encode([0x0]) returns [0x0] (zero → single zero byte).
2. encode of any value in 0..0x7F returns a single byte equal to that value (0x40 → [0x40], 0x7F → [0x7F]).
3. encode([0x80]) returns [0x81, 0x0] (continuation bit 0x80 set on every byte except the last).
4. encode([0x2000]) returns [0xC0, 0x0]; encode([0x3FFF]) returns [0xFF, 0x7F].
5. encode([0x4000]) returns [0x81, 0x80, 0x0]; encode([0x100000]) returns [0xC0, 0x80, 0x0].
6. encode([0x200000]) returns [0x81, 0x80, 0x80, 0x0]; encode([0xFFFFFFF]) returns [0xFF, 0xFF, 0xFF, 0x7F].
7. encode([0xFFFFFFFF]) returns [0x8F, 0xFF, 0xFF, 0xFF, 0x7F] (max 32-bit unsigned).
8. encode([]) returns [].
9. encode of multiple values concatenates each value's VLQ in order ([0x0, 0x0, 0x0] → [0x0, 0x0, 0x0]).
10. encode([-1]) raises ValueError.
11. encode([0x100000000]) raises ValueError (2**32 exceeds 32-bit unsigned restriction).
12. decode([0x7F]) returns [0x7F]; decode([0xC0, 0x0]) returns [0x2000]; decode([0xFF, 0xFF, 0x7F]) returns [0x1FFFFF].
13. decode([0x81, 0x80, 0x80, 0x0]) returns [0x200000]; decode([0x8F, 0xFF, 0xFF, 0xFF, 0x7F]) returns [0xFFFFFFFF].
14. decode([]) returns [].
15. decode([0xFF]) raises ValueError with message "incomplete sequence".
16. decode([0x80]) raises ValueError with message "incomplete sequence" (incomplete even when value is zero).
17. decode of a concatenated multi-value sequence returns the ordered value list.
18. Round-trip: decode(encode(v)) == v for the full canonical table and a randomized sweep of 32-bit values; encode(decode(x)) == x for canonical encodings.
