# Project Memory — variable_length_quantity (polyglot exercise)

## Index
- [verified_vlq.md](verified_vlq.md) — ✅ Verified reference: VLQ encode/decode implementation (canonical tests green, A4.9 reviewed)

## Session notes (2026-08-29)
- Task: implement VLQ encode/decode per Exercism spec (prompt.md); graded by hidden pytest suite `variable_length_quantity_test.py` injected by the harness grader.
- Implementation: integer bit-shift approach, stdlib only. `encode` splits each 32-bit number into 7-bit groups LSB-first, emits MSB-first with `0x80` continuation bit on all but the last byte; `0` → `[0x00]`. `decode` accumulates `(acc << 7) | (byte & 0x7F)` and raises `ValueError("incomplete sequence")` when the stream ends with a continuation bit set — tracked with an explicit `in_sequence` flag (a `value != 0` check would wrongly pass `[0x80]`).
- Verified: canonical suite 26/26 pass (TDD RED 26-fail against stub first), round-trip of 2000 random 32-bit values, 12-case prompt example table, `py_compile` clean.
- A4.9 independent review: verdict ready, no Critical/Important; 5 Minors all out-of-spec scope-limits/style → deferred (see verified_vlq.md).
