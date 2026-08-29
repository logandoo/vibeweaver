> cap=5  stall=3×

# Variable Length Quantity — Acceptance Criteria

Derived from prompt.md (VLQ spec + 12 worked examples) and the canonical
Exercism problem-specifications suite (hidden tests: tasks/polyglot_variable_length_quantity/hidden_tests/variable_length_quantity_test.py).

1. `encode([0])` returns `[0]`.
2. Single-byte encoding is identity for values in `0x00..0x7F` (e.g. `encode([0x40]) == [0x40]`, `encode([0x7F]) == [0x7F]`).
3. Multi-byte encodings match all 12 examples in the prompt table (0x80 → `[0x81, 0x00]`, 0x2000 → `[0xC0, 0x00]`, 0x3FFF → `[0xFF, 0x7F]`, 0x4000 → `[0x81, 0x80, 0x00]`, 0x100000 → `[0xC0, 0x80, 0x00]`, 0x1FFFFF → `[0xFF, 0xFF, 0x7F]`, 0x200000 → `[0x81, 0x80, 0x80, 0x00]`, 0x08000000 → `[0xC0, 0x80, 0x80, 0x00]`, 0x0FFFFFFF → `[0xFF, 0xFF, 0xFF, 0x7F]`, plus 0x00000000/0x40/0x7F singles).
4. Maximum 32-bit value: `encode([0xFFFFFFFF]) == [0x8F, 0xFF, 0xFF, 0xFF, 0x7F]`.
5. Multiple values encode in input order (two-multi-byte `[0x4000, 0x123456]` and many-multi-byte cases).
6. `decode` inverts `encode` for every canonical decode case (1- to 5-byte values, max 32-bit, multiple values).
7. `decode` raises `ValueError("incomplete sequence")` for truncated sequences, including `[0xFF]` and `[0x80]` (value-accumulates-to-zero case).
8. Empty inputs: `encode([]) == []` and `decode([]) == []`.
9. Round-trip property: `decode(encode(vals)) == vals` holds for 2000 random 32-bit values and 20 small batches.
10. Implementation lives in variable_length_quantity.py only; no test files created or modified (grader's hidden suite untouched).
