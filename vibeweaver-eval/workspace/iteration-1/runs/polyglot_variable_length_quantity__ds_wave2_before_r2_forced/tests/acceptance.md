> cap=5  stall=3×
1. `encode([0]) == [0x00]`
2. `encode` matches every row of the prompt's example table
3. `decode(encode(n)) == n` for all example table values
4. `encode` handles multi-value input and `decode` returns one number per VLQ terminator
5. `decode` raises `ValueError` on an incomplete (continuation-terminated) sequence
6. Empty input round-trips (`encode([]) == []`, `decode([]) == []`)
