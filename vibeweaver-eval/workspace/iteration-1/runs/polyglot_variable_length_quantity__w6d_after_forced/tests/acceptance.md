> cap=5  stall=3×

# Acceptance Criteria — variable_length_quantity

1. `encode(numbers)` returns the VLQ byte list for each 32-bit unsigned integer (big-endian 7-bit groups, continuation bit set on all but the final byte).
2. `encode([])` returns `[]`.
3. `decode(bytes_)` reconstructs the original integer list from a complete VLQ byte sequence.
4. `decode([])` returns `[]`.
5. `decode` raises `ValueError` when the input ends with a continuation bit set (incomplete sequence).
6. All 12 prompt examples round-trip: encode(number) == expected bytes and decode(expected) == [number].
7. `0xFFFFFFFF` round-trips to `[0x8F, 0xFF, 0xFF, 0xFF, 0x7F]`.
8. The module imports and runs with no syntax or runtime errors under Python 3.
