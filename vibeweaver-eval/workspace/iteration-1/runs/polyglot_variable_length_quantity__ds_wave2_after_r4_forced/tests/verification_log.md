# Verification Log — Variable Length Quantity

- COV-9 skipped — reason: library-stub exercise workspace: no `script/` directory and no existing test runner/start script to baseline against; single-file change verified below by canonical-vector + randomized-sweep + fresh-run evidence.
- iter 1 FAIL: criterion 9 (multi-value encode [0xFFFFFFFF, 0x0, 0xFFFFF]) | diagnosis: hand-written expected vector wrong — 0xFFFFF = 2^20-1 (twenty 1-bits) encodes to [0xBF,0xFF,0x7F], not [0xFF,0xFF,0x7F]; implementation output independently verified via divmod (0xFFFFF/128: 8191 r127, 63 r127, 0 r63) | changed: tests/canonical_suite_run.log expected vector (no production code change)
- iter 2 PASS: criteria 1-18 | evidence: tests/canonical_suite_run.log — all 13 encode vectors (00→8F FF FF FF 7F), multi-value/empty, error cases; decode round-trips + incomplete-sequence ValueErrors
- iter 3 PASS: criterion 18 (round-trip) | evidence: tests/differential_sweep_run.log — 20000 random 32-bit decode(encode(v))==v, 20000 encode/decode, 3000 multi-value concatenated sequences, boundary values, 0 mismatches
- iter 4 PASS: full re-run on final tree | evidence: tests/fresh_run_canonical.log — py_compile OK, canonical table + error cases all PASS, exit 0
