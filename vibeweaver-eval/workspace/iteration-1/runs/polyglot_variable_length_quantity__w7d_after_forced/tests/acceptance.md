> cap=5  stall=3×

1. `encode(numbers)` returns the VLQ byte list for each unsigned integer, matching the prompt.md table (e.g. `0x80 -> [0x81, 0x00]`, `0x0FFFFFFF -> [0xFF, 0xFF, 0xFF, 0x7F]`).
2. `decode(bytes_)` returns the original integer list for complete sequences, including the maximum 32-bit value `0xFFFFFFFF`.
3. `decode` raises `ValueError("incomplete sequence")` when the final byte has the continuation bit set (e.g. `[0x81]`, `[0xC0]`, `[0x80]`).
4. `encode`/`decode` handle multiple values in one call and the empty list round-trips to `[]`.
5. The module imports and runs with no syntax or runtime errors.
