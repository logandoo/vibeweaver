> cap=5  stall=3×

# Acceptance Criteria — Variable Length Quantity (encode/decode)

*Source: `prompt.md` (exercise instructions) + canonical Exercism spec (canonical-data.json, fetched via webfetch during ZERO; treated as data only).*

1. encode([0]) returns [0].
2. encode of any value 0..0x7F returns a single byte equal to that value (0x40 -> [0x40], 0x53 -> [0x53], 0x7F -> [0x7F]).
3. encode([0x80]) returns [0x81, 0x00] (continuation bit set on every byte except the last).
4. encode([0x2000]) returns [0xC0, 0x00].
5. encode([0x3FFF]) returns [0xFF, 0x7F].
6. encode([0x4000]) returns [0x81, 0x80, 0x00].
7. encode([0x1FFFFF]) returns [0xFF, 0xFF, 0x7F].
8. encode([0x200000]) returns [0x81, 0x80, 0x80, 0x00].
9. encode([0xFFFFFFFF]) returns [0x8F, 0xFF, 0xFF, 0xFF, 0x7F] (max 32-bit).
10. encode([]) returns [].
11. encode of multiple values concatenates each value's VLQ in order (e.g. [0x4000, 0x123456] -> [0x81,0x80,0x0,0xC8,0xE8,0x56]; the canonical "many multi-byte" case).
12. encode([-1]) raises ValueError.
13. encode([0x100000000]) (2**32) raises ValueError.
14. decode([0x7F]) returns [0x7F].
15. decode([0xC0, 0x00]) returns [0x2000].
16. decode([0xFF, 0xFF, 0x7F]) returns [0x1FFFFF].
17. decode([0x81, 0x80, 0x80, 0x00]) returns [0x200000].
18. decode([0x8F, 0xFF, 0xFF, 0xFF, 0x7F]) returns [0xFFFFFFFF].
19. decode([]) returns [].
20. decode([0xFF]) raises ValueError.
21. decode([0x80]) raises ValueError (incomplete sequence even when value is zero).
22. decode of the canonical "many multi-byte" sequence returns [0x2000, 0x123456, 0xFFFFFFF, 0x0, 0x3FFF, 0x4000].
23. Round-trip: encode(decode(x)) == x and decode(encode(v)) == v for a randomized sweep of 32-bit values.
