# MEMORY

- variable_length_quantity (2026-08-29) — ✅ Verified: encode/decode implemented in variable_length_quantity.py; all canonical Exercism vectors + 20000-value random sweeps pass (tests/canonical_suite_run.log, tests/differential_sweep_run.log, tests/fresh_run_canonical.log).
  - topic: [fix_variable_length_quantity.md](fix_variable_length_quantity.md) — solution + verification + 0xFFFFF pitfall.
- Key facts: encode packs low-7-bit groups LSB-first, sets 0x80 continuation bit on all but last byte; decode accumulates `(v<<7)|(b&0x7F)` and raises ValueError("incomplete sequence") if a byte with continuation bit set is last. Range checks: negative → ValueError, >0xFFFFFFFF → ValueError. 0xFFFFF encodes to [0xBF,0xFF,0x7F] (not [0xFF,0xFF,0x7F]).
