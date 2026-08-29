---
name: Fix: VLQ encode/decode implementation
description: Canonical variable-length-quantity encode/decode for a 32-bit-unsigned restricted exercise
type: fix
date: 2026-08-29
status: ⏳
commit: N/A
file_refs:
  - path: variable_length_quantity.py
    range: "1-32"
    sha_at_time: N/A
last_validated: 2026-08-29
---

# Fix: VLQ encode/decode implementation

**Problem:** Starter file provided `encode(numbers)` / `decode(bytes_)` stubs returning `None`; the exercise requires canonical VLQ encoding and decoding restricted to 32-bit unsigned integers.

**Root Cause:** No implementation existed.

**Correct Fix:** Implemented bit-grouping encode and streaming decode in `variable_length_quantity.py`:
- `encode`: validates each number is in `[0, 0xFFFFFFFF]` (raises `ValueError("negative integer")` / `ValueError("integer too large")`), emits 7-bit groups least-significant-first collected into a list then reversed, with `0x80` continuation bit set on every byte except the last. Zero → `[0]`.
- `decode`: streams bytes, accumulating `(value << 7) | (byte & 0x7F)`; each byte with bit 7 clear terminates a value; if the stream ends mid-sequence raises `ValueError("incomplete sequence")`.

**Failed Approaches (DO NOT retry):**
- None (single implementation wave, all 34 canonical tests + 8019-check differential sweep passed first try).

**Rejected Alternatives:**
- String/binary-based chunking (bin(n) → 7-bit groups) — rejected for the implementation as roundabout; used ONLY as the independent reference for differential testing.
- Unrestricted VLQ (no 32-bit cap) — rejected; prompt explicitly restricts to 32-bit unsigned.

**Verification:** 34/34 canonical-suite tests pass (tests/canonical_suite_run.log); independent string-based reference sweep 8019 checks / 0 failures (tests/differential_sweep_run.log), including round-trip, multi-value, random-byte-sequence, and error-message checks. Status ⏳ (verified by tests but not user-confirmed).
