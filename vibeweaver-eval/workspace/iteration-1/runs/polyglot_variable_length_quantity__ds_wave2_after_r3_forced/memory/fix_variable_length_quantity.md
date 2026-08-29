---
name: Fix: VLQ encode/decode implementation
description: Canonical variable-length-quantity encode/decode for a 32-bit-unsigned restricted exercise
type: fix
date: 2026-08-29
status: ⏳
commit: TBD
file_refs:
  - path: variable_length_quantity.py
    range: "1-32"
    sha_at_time: 8d26effb62a553d228a20ae6e094b95e865dd449d63417df197fd6480eca4d41
last_validated: 2026-08-29
---

# Fix: VLQ encode/decode implementation

**Problem:** Starter file provided `encode(numbers)` / `decode(bytes_)` stubs returning `None`; the exercise requires canonical VLQ encoding and decoding restricted to 32-bit unsigned integers.

**Root Cause:** No implementation existed.

**Correct Fix:** Implemented bit-grouping encode and streaming decode in `variable_length_quantity.py`:
- `encode`: validates each number is an int in `[0, 0xFFFFFFFF]` (raises `ValueError("negative integer")` / `ValueError("integer too large")`), emits 7-bit groups least-significant-first collected into a list then reversed, with `0x80` continuation bit set on every byte except the last. Zero → `[0]`.
- `decode`: streams bytes, accumulating `(value << 7) | (byte & 0x7F)`; each byte with bit 7 clear terminates a value; if the stream ends mid-sequence raises `ValueError("incomplete sequence")`.

**Failed Approaches (DO NOT retry):**
- None for the solution (single implementation wave, 26/26 canonical tests + 108002-check differential sweep passed).
- My first differential-reference implementation split `bin(n)[2:]` directly into 7-bit groups WITHOUT zero-padding the leading group to a full 7 bits — produced wrong reference bytes for values whose bit length is not a multiple of 7 (4837 mismatches). Fixed by `bits.zfill((-len(bits)) % 7 + len(bits))` BEFORE the uniform 7-bit split.

**Rejected Alternatives:**
- String/binary-based chunking for the implementation — rejected as roundabout; used ONLY as the independent reference for differential testing.
- Unrestricted VLQ (no 32-bit cap) — rejected; prompt explicitly restricts to 32-bit unsigned.

**Verification:** 26/26 canonical-suite tests pass (tests/canonical_suite_run.log); independent bit-string reference sweep 108002 checks / 0 failures (tests/differential_sweep_run.log), including table values, ~262k scanned points over 0x0..0xFFFFFFFF, 12000 random values, 2000 multi-value lists, and round-trip decode(encode(x))==x everywhere. Status ⏳ (verified by tests but not user-confirmed).
