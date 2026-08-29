---
topic: variable_length_quantity
status: verified
date: 2026-08-29
---

# fix_variable_length_quantity

## Problem
Implement VLQ encoding/decoding for 32-bit unsigned integers (Exercism-style).

## Solution
- `encode(numbers)`: per value, emit low-7-bit groups LSB-first into a list, set
  `0x80` continuation bit on every group except the final (most-significant) one;
  concatenate across values. Raise ValueError on negative or >0xFFFFFFFF.
- `decode(bytes_)`: accumulate `value = (value << 7) | (byte & 0x7F)`; a byte with
  bit 7 clear terminates a group. If the stream ends mid-group (last byte has
  continuation bit set, e.g. [0xFF], [0x80]) raise ValueError("incomplete sequence").

## Verification
- tests/canonical_suite_run.log: all 13 canonical vectors + multi-value + errors, PASS
- tests/differential_sweep_run.log: 20000 + 20000 random + 3000 multi-value round-trips, 0 mismatches
- tests/fresh_run_canonical.log: py_compile OK + fresh canonical run PASS

## Pitfall (verified)
0xFFFFF = 2^20-1 encodes to [0xBF, 0xFF, 0x7F] — a naive "all high bytes are
0xFF" expectation is wrong (MSB 7-bit group is 0x3F).
