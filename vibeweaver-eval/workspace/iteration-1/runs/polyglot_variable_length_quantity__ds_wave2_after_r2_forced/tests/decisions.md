# AUTO ADRs — polyglot_variable_length_quantity (ds_wave2_after_r2_forced)

Mode: AUTO. Verifier: direct read (non-web), COV-5 preset for non-web library tasks (C7).

| id | trigger | options | chosen | why | revisit-if |
|----|---------|---------|--------|-----|------------|
| D-1 | web research rate-limited (exa 429) | retry / use canonical Exercism suite + prompt spec | canonical suite + prompt spec as authoritative reference | spec fully derivable from prompt.md's 12 worked examples + the grader's hidden suite (canonical problem-specifications); fetched content would only restate the same spec | research provider recovers and a discrepancy appears |
| D-2 | COV-9 baseline on an unimplemented stub | skip baseline / record expected-RED | record expected-RED, mark COV-9 skipped | baseline run proves the RED state (26 failed, tests/red_evidence.log); pre-implementation, not a regression | baseline turns GREEN later |
| D-3 | shared git repo, concurrent runs commit to HEAD | commit scoped to run dir / commit nothing | git add <run-dir> && git commit -- <run-dir> (pathspec) | eval expects commits; pathspec bounds blast radius and avoids staging other runs' files | lock/collision observed |
| D-4 | decode must reject [0x80] (value accumulates to zero) | in_sequence flag / last-byte continuation check | in_sequence flag (last byte's continuation bit) | rejects both 0xFF-style residue and 0x80-style zero-value truncation; matches the canonical hidden tests | hidden suite behavior changes |
| D-5 | artifact layout for a library task | minimal / mirror sibling-run pattern | tests/acceptance.md, tests/verification_log.md, tests/decisions.md, tests/assert_artifacts.py (canonical), tests/project_profile.json, memory/, script/linux/ | matches the established sibling-run pattern in this eval; no test files created (constraint honored) | eval harness changes contract |
| D-6 | COV-10 Design Gate for this change-wave | write design docs / skip per §A5 table | skip (COV-10 skipped — bugfix / minor tweak: Modify-Existing, one library file, no design doc per §A5 table) | §A5 table classifies minor library tweaks as no-design-doc; assert group 7 skipped via --existing | change becomes a new system/API |
