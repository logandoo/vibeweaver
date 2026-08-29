> Mode: AUTO (declared at task start). All auto-decisions made autonomously; each ADR block records context, decision, and consequences.

# ADR-001 — Verifier selection fallback (COV-5)
- Context: mm_probe.py --generate failed (model cannot read images; token 0/6 on --check), mm-sensor not listed as available.
- Decision: Verifier = `direct read` (test-output + exit-code cross-check per Step 0c); announced at task start.
- Consequences: media grading N/A; evidence is byte-checkable logs + assert_artifacts.py exit 0.

# ADR-002 — Independent test oracle for the differential sweep
- Context: requirement #23 wants round-trip/edge robustness; a self-written oracle would share implementation bugs.
- Decision: encode_ref/decode_ref implemented independently in the string-based temp runner; the workspace implementation never imports it.
- Consequences: 8019 checks with 0 failures; sweep assumptions documented (non-canonical input re-encodes to canonical form; decode outputs >32-bit correctly rejected by encode).

# ADR-003 — 32-bit unsigned scope
- Context: prompt.md restricts inputs to 32-bit unsigned; canonical suite tests only that range.
- Decision: encode validates against 0..0xFFFFFFFF with exact error messages ("negative integer", "integer too large"); decode may produce any value but encode rejects out-of-range on re-encode.
- Consequences: out-of-scope inputs (random byte sequences decoding >32 bits) excluded from acceptance; documented in acceptance.md #23.

# ADR-004 — Concurrent-harness commit isolation
- Context: eval harness commits other runs' files into the same repo concurrently; a blanket `git add -A` swept 354 unrelated files into the baseline.
- Decision: baseline reset and re-created surgically (only this run's files); every add scoped to this workspace's paths; review range pinned to a056e23^..a056e23.
- Consequences: clean single-feature diff; review package records its exact range per A4.9 Step 1.
