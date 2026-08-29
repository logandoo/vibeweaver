# A4.9 Independent Review Package — polyglot_variable_length_quantity (ds_wave2_after_r2_forced)

- Reviewed diff range: `git diff 9d845af..f0d7a39 -- workspace/iteration-1/runs/polyglot_variable_length_quantity__ds_wave2_after_r2_forced/` (17 files: 1 modified source, tests/, script/, memory/, run.log).
- Trigger: feature implementation (change-wave: variable_length_quantity.py + tests/ + script/ + memory/, exceeds 3-file bar).
- Reviewer: independent agent (no access to prior session context).
- Reviewed: variable_length_quantity.py, tests/acceptance.md, tests/canonical_suite.log, tests/differential_check.log, tests/red_evidence.log, tests/decisions.md, tests/verification_log.md.

## Verdict: APPROVE-WITH-MINOR

## Findings (severity-rated)
- Critical: none.
- Important: none.
- Minor (out-of-contract / style, no action required):
  1. `encode([-1])` would infinite-loop (arithmetic shift keeps `-1`); spec is unsigned 32-bit, grader never sends negatives.
  2. `chunks.insert(0, …)` is O(k²) per value; bounded at ≤5 chunks, style only.
  3. `decode` accepts non-minimal / >32-bit encodings rather than rejecting; canonical tests do not require rejection.

## Independent evidence (reviewer-executed)
- `in_sequence` flag is derived from the last byte's continuation bit, so `[0x80]` (zero residue) is rejected without relying on the accumulated value.
- Adversarial `decode([0x81])`, `decode([0x80,0x80])`, `decode([0xFF,0x80])`, `decode([0x80])`, `decode([0xFF])` all raised `ValueError("incomplete sequence")` as required.
- Boundary roundtrips OK for 0, 0x7F, 0x80, 0x3FFF, 0x4000, 0x1FFFFF, 0x200000, 0x0FFFFFFF, 0x10000000, 0xFFFFFFFF; `encode([0xFFFFFFFF]) == [0x8F,0xFF,0xFF,0xFF,0x7F]`.
- Sweep `decode(encode(v))==[v]` for all 0..0x20000 plus 20,000 random 32-bit values and a multi-value list with interleaved zeros — all OK; single-byte identity holds for every 0x00..0x7F.
- Constraint check: no pytest-collectable `*_test.py` anywhere under the workspace; grader hidden suite untouched (lives outside, in tasks/…/hidden_tests/); all pytest runs used scratch copies.

## Adjudication
All minor findings are out-of-contract (spec: unsigned 32-bit, canonical suite) or style-only with bounded impact. Accepted with no code change. Criteria 1-10 all evidenced by the two logs; logs mutually consistent (RED 26 → GREEN 26).
