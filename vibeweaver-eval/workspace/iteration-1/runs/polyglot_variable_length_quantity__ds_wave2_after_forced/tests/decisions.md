# AUTO ADRs — polyglot_variable_length_quantity

Mode: AUTO. Verifier: direct read (non-web), COV-5 preset for non-web library tasks.

| id | trigger | options | chosen | why | revisit-if |
|----|---------|---------|--------|-----|------------|
| D-1 | web research rate-limited (exa 429 twice) | retry / use canonical Exercism suite + prompt spec | canonical suite + prompt spec as authoritative reference | spec fully derivable from prompt.md + hidden tests are the canonical problem-specifications suite; fetched content would only be a repeat of the same spec | research provider recovers and a discrepancy appears |
| D-2 | COV-9 baseline on an unimplemented stub | skip baseline / record expected-RED | record expected-RED, mark COV-9 skipped | baseline run proves RED state; no pre-existing failures to attribute; RED is by design, not regression | baseline turns GREEN later |
| D-3 | shared git repo, concurrent runs commit to HEAD | commit scoped to run dir / commit nothing | git add <run-dir> && git commit -- <run-dir> (pathspec) | eval expects commits; pathspec bounds blast radius and avoids staging other runs' files | lock/collision observed |
| D-4 | decode must reject [0x80] (value accumulates to zero) | in_sequence flag / last-byte continuation check | last-byte check `if value or (bytes_ and bytes_[-1] & 0x80)` | rejects both 0xFF-style residue and 0x80-style zero-value truncation in 2 clauses; matches the canonical hidden tests | hidden suite behavior changes |
| D-5 | artifact layout for library task | copy bowling-run pattern | tests/acceptance.md, tests/verification_log.md, tests/decisions.md, tests/assert_artifacts.py (canonical), tests/project_profile.json, memory/, script/linux/ | matches established sibling-run pattern in this eval; no test files created (constraint) | eval harness changes contract |
