---
type: reference
status: verified
topic: vlq-encode-decode
date: 2026-08-29
---

# ✅ Verified: VLQ encode/decode implementation

## What
`encode(numbers)` → list of ints: each 32-bit number split into 7-bit groups (LSB first),
continuation bit `0x80` set on every byte except the final one; `0` encodes to `[0]`.
`decode(bytes_)` → list of ints: accumulates `(acc << 7) | (byte & 0x7F)`, flushes a value
when a byte has bit 7 clear; raises `ValueError("incomplete sequence")` if a continuation
byte is never terminated.

## Why it works (key invariants)
- 7 bits per byte, MSB-first on the wire, high bit = "more bytes follow".
- Numbers restricted to 32-bit unsigned per spec, so no range validation needed.
- Incomplete-sequence detection must NOT rely on `value != 0`: `[0x80]` accumulates to 0
  yet is still an error — tracked with an explicit `in_sequence` flag.

## Evidence
- Canonical suite: `26 passed in 0.02s` (tests/pytest_canonical.log)
- Round-trip: 2000 random 32-bit values + 12-case prompt table + edge cases (tests/roundtrip.log)

## Follow-up notes
- If hidden tests ever change the error message, update the literal string in `decode`.
- Non-canonical encodings (e.g. `[0x80, 0x00]` → 0) decode successfully by design; not tested by canonical suite.

## A4.9 independent review (2026-08-29) — verdict: approve (no Critical/Important)
Minors deferred to memory (out-of-contract, spec limits inputs to 32-bit unsigned):
1. encode(-1) hangs — negative input is out of contract (spec: 32-bit unsigned only).
2. encode does not reject >0xFFFFFFFF values — out of contract; would emit >5 bytes.
3. decode accepts overlong/non-canonical encodings — not required by canonical tests.
4. Missing type annotations / docstring on signatures.
5. No byte-range (0-255) validation on decode input elements.
Rulings: all deferred (out of spec contract; would add validation the canonical suite doesn't demand). Revisit only if the task expands the input contract.
