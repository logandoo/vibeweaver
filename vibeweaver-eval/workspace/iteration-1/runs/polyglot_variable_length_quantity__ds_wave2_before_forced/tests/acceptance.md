> cap=5  stall=3×

Acceptance criteria for the Variable Length Quantity exercise:

1. `encode([0x0])` returns `[0x0]`.
2. `encode([0x40])` returns `[0x40]` (arbitrary single byte).
3. `encode([0x7F])` returns `[0x7F]` (largest single byte).
4. `encode([0x80])` returns `[0x81, 0x0]` (smallest double byte).
5. `encode([0x2000])` returns `[0xC0, 0x0]` (arbitrary double byte).
6. `encode([0x3FFF])` returns `[0xFF, 0x7F]` (largest double byte).
7. `encode([0x4000])` returns `[0x81, 0x80, 0x0]` (smallest triple byte).
8. `encode([0x100000])` returns `[0xC0, 0x80, 0x0]` (arbitrary triple byte).
9. `encode([0x1FFFFF])` returns `[0xFF, 0xFF, 0x7F]` (largest triple byte).
10. `encode([0x200000])` returns `[0x81, 0x80, 0x80, 0x0]` (smallest quadruple byte).
11. `encode([0x8000000])` returns `[0xC0, 0x80, 0x80, 0x0]` (arbitrary quadruple byte).
12. `encode([0xFFFFFFF])` returns `[0xFF, 0xFF, 0xFF, 0x7F]` (largest quadruple byte).
13. `encode([0x10000000])` returns `[0x81, 0x80, 0x80, 0x80, 0x0]` (smallest quintuple byte).
14. `encode([0xFF000000])` returns `[0x8F, 0xF8, 0x80, 0x80, 0x0]` (arbitrary quintuple byte).
15. `encode([0xFFFFFFFF])` returns `[0x8F, 0xFF, 0xFF, 0xFF, 0x7F]` (maximum 32-bit input).
16. `encode([0x40, 0x7F])` returns `[0x40, 0x7F]` (two single-byte values).
17. `encode([0x4000, 0x123456])` returns `[0x81, 0x80, 0x0, 0xC8, 0xE8, 0x56]` (two multi-byte values).
18. `encode([0x2000, 0x123456, 0xFFFFFFF, 0x0, 0x3FFF, 0x4000])` returns the expected 15-byte stream (many multi-byte values).
19. `decode([0x7F])` returns `[0x7F]` (one byte).
20. `decode([0xC0, 0x0])` returns `[0x2000]` (two bytes).
21. `decode([0xFF, 0xFF, 0x7F])` returns `[0x1FFFFF]` (three bytes).
22. `decode([0x81, 0x80, 0x80, 0x0])` returns `[0x200000]` (four bytes).
23. `decode([0x8F, 0xFF, 0xFF, 0xFF, 0x7F])` returns `[0xFFFFFFFF]` (maximum 32-bit integer).
24. `decode([0xFF])` raises `ValueError` with message `"incomplete sequence"`.
25. `decode([0x80])` raises `ValueError` with message `"incomplete sequence"` (incomplete even when value is zero).
26. `decode([0xC0, 0x0, 0xC8, 0xE8, 0x56, 0xFF, 0xFF, 0xFF, 0x7F, 0x0, 0xFF, 0x7F, 0x81, 0x80, 0x0])` returns `[0x2000, 0x123456, 0xFFFFFFF, 0x0, 0x3FFF, 0x4000]` (multiple values).
27. Encode/decode round-trip holds for 2000 random 32-bit values (property check).
28. `encode`/`decode` on empty inputs return empty lists; module has no syntax errors (`py_compile` clean).
