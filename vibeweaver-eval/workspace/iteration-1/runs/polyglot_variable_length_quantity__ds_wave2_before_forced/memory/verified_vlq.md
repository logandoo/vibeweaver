---
name: Verified VLQ encode/decode implementation
description: Verified reference implementation of Variable Length Quantity encoding/decoding for the polyglot variable_length_quantity exercise (canonical Exercism tests green)
type: reference
status: verified
date: 2026-08-29
last_validated: 2026-08-29
---

# ✅ Verified: VLQ encode/decode implementation

## What
`encode(numbers)` → list of ints: each 32-bit unsigned number is split into
7-bit groups LSB-first; groups are emitted MSB-first with the continuation bit
`0x80` set on every byte except the final one; `0` encodes to `[0x00]`.
`decode(bytes_)` → list of ints: accumulates `(acc << 7) | (byte & 0x7F)`,
flushes a value when a byte has bit 7 clear; raises
`ValueError("incomplete sequence")` if the stream ends mid-sequence.

## Why it works (key invariants)
- VLQ is base-128 big-endian: 7 bits per byte, MSB-first on the wire, high bit
  = "more bytes follow" (Wikipedia variable-length integer / MIDI spec; matches
  the prompt's example table).
- Numbers restricted to 32-bit unsigned per the exercise spec, so no range
  validation is needed for the canonical grader.
- Incomplete-sequence detection MUST NOT rely on `value != 0`: `[0x80]`
  accumulates to 0 yet is still an error — the explicit `in_sequence` flag is
  the correct mechanism (hidden test asserts the message exactly).

## Evidence
- TDD RED: canonical suite against the stub → `26 failed in 0.07s`
  (tests/red_pytest_canonical.log)
- Canonical suite: `26 passed in 0.01s` (tests/pytest_canonical.log)
- Round-trip: 2000 random 32-bit values, the prompt's 12-case example table,
  ValueError cases, empty inputs, `py_compile` clean (tests/roundtrip.log)

## A4.9 independent review (2026-08-29) — verdict: ready (no Critical/Important)
All 5 Minor findings deferred (out-of-spec scope-limits or style — the exercise
contract limits inputs to 32-bit unsigned):
1. `encode(-1)` would hang (Python arithmetic shift) — negative input is out of
   contract (spec: 32-bit unsigned only).
2. `encode`/`decode` do not validate 32-bit width / byte range — out of
   contract; canonical tests don't demand it.
3. No input-type guards (natural Python `TypeError`) — not contract-required.
4. `in_sequence = True` assignment ordering slightly redundant — functionally
   correct.
5. No docstrings/type annotations — not required by spec.
Rulings: all deferred; revisit only if the task expands the input contract.

## Follow-up notes
- If hidden tests ever change the error message, update the literal string in
  `decode`.
- Non-canonical/overlong encodings (e.g. `[0x80, 0x00]` → 0) decode by design;
  not tested by the canonical suite.
