# fix_variable_length_quantity

## Status
RESOLVED (iter 1 PASS)

## Root cause (starter state)
`variable_length_quantity.py` shipped as `def encode(numbers): pass` / `def decode(bytes_): pass` — always returns `None`; all 26 hidden tests failed (baseline RED evidence, tests/red_evidence.log).

## Diagnosis / fix
Implemented the canonical 7-bit chunking algorithm:

- `encode`: split each number into 7-bit chunks from the LSB (`number & 0x7F`, `number >>= 7`), prepend continuation chunks with the high bit set (`0x80 | chunk`), concatenate per input in order.
- `decode`: accumulate `value = (value << 7) | (byte & 0x7F)`; flush the value when the high bit is clear; track `in_sequence = bool(byte & 0x80)` so a final byte with the continuation bit raises `ValueError("incomplete sequence")` — this also rejects `[0x80]`, where the value accumulates to zero and a last-byte test alone is insufficient.

## Files
- variable_length_quantity.py (only source change)

## Tests
- tests/canonical_suite.log — 26/26 hidden tests pass, exit 0
- tests/differential_check.log — 30/30 independent prompt-table + property checks, exit 0
