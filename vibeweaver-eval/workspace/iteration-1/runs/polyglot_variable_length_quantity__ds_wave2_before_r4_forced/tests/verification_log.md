# Verification Log — variable_length_quantity

- COV-9 skipped — reason: fresh exercise workspace (single stub module, no script/, no existing test baseline, dir not tracked by repo git) — nothing to baseline-test.
- iter 1 PASS: criteria 1-22 | diagnosis: n/a (first run, all green) | changed: variable_length_quantity.py | evidence: tests/verify_iter1.log (RESULT: ALL PASS, exit 0) — 12 prompt encode examples + 5 decode cases + empty-list + multi-value + incomplete-sequence ValueError + 11 round-trips.
- COV-8 review: IMPORTANT-Bug found at variable_length_quantity.py:21 — `decode([0x80])`/`decode([0x80, 0x80])` returned [] (zero-accumulation continuation bytes not detected). Fixed by checking last byte's continuation bit. Criterion 23 added to acceptance.md.
- iter 2 PASS: criteria 1-23 | diagnosis: fixed incomplete-sequence detection at source (last-byte continuation check) | changed: variable_length_quantity.py | evidence: tests/verify_iter2.log (ALL PASS) + inline ValueError edge cases + py_compile OK.
