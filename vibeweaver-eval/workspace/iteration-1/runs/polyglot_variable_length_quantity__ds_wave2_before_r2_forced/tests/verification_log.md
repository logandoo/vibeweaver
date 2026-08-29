# Verification Log — variable_length_quantity (VLQ encode/decode)

## Task: implement variable_length_quantity.py

- Baseline verified GREEN — trivial single-stub starter file; baseline = running the empty stubs (no-op), no pre-existing runtime.

## iter 1 PASS: criteria 1-6 | diagnosis: all criteria pass
- Evidence: executed `python3` against the implemented module (commands below). All 12 rows of the prompt example table produce the exact expected VLQ byte sequences and decode back to the original number. Edge cases pass: empty input round-trips, `encode([0,0]) == [0,0]`, max 32-bit value `0xFFFFFFFF` round-trips as `[0x8F, 0xFF, 0xFF, 0xFF, 0x7F]`, and an incomplete sequence `[0x80]` raises `ValueError`.
- changed: variable_length_quantity.py
- No code changed after this verification run (fresh run on final tree).

## iter 2 PASS: criteria 1-6 | diagnosis: review fixes applied and verified
- Independent review (COV-8) returned APPROVE; 2 Important findings fixed:
  (1) encode now raises `ValueError` for inputs outside 0..0xFFFFFFFF (was silently emitting/accepting out-of-domain values); (2) encode no longer silently drops negatives (now raises). Decode also rejects values > 32 bits.
- Re-ran full example-table + edge suite: all 12 table rows exact-match in both directions; edges pass (empty round-trip, `encode([0,0])`, `0xFFFFFFFF` → `[0x8F,0xFF,0xFF,0xFF,0x7F]` round-trip, multi-value stream `[0x2000,0x2000]`, incomplete-sequence `ValueError`, and new range-guard `ValueError` for `encode([-1])`, `encode([0x100000000])`, `decode([0xFF,0xFF,0xFF,0xFF,0x7F])`).
- changed: variable_length_quantity.py (range guards)
- No code changed after this verification run (fresh run on final tree).
