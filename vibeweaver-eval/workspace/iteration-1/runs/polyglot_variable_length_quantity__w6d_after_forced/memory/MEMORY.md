# Project Memory — variable_length_quantity

## Overview
Exercism-style single-file Python exercise: implement Variable-Length Quantity (VLQ) encoding/decoding for 32-bit unsigned integers.

## Key facts
- Deliverable: `variable_length_quantity.py` with `encode(numbers)` and `decode(bytes_)`.
- VLQ: big-endian 7-bit groups; continuation bit (0x80) set on all but the final byte.
- `decode` raises `ValueError` on a trailing byte with the continuation bit still set.
- No service/build lifecycle; no `script/` directory; verification is direct Python execution.

## Topic files
- [fix_vlq.md](fix_vlq.md) — implementation approach and verified behavior.
