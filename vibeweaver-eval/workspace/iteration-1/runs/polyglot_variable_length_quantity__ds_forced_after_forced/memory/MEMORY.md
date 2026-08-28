# Project Memory — variable_length_quantity (polyglot exercise)

## Index
- [verified_vlq.md](verified_vlq.md) — ✅ Verified implementation of VLQ encode/decode (canonical tests green)

## Session notes (2026-08-29)
- Task: implement VLQ encode/decode per Exercism spec; graded by hidden pytest (`variable_length_quantity_test.py`).
- Implementation: integer bit-shift approach, no dependencies. decode raises `ValueError("incomplete sequence")` when a continuation byte (bit 7 set) is unterminated — including the `[0x80]` case where the accumulated value is 0.
- Verified: canonical suite 26/26 pass; round-trip of 2000 random 32-bit values; prompt example table; `py_compile` clean.
