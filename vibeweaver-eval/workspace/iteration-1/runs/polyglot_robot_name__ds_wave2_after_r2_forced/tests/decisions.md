# Decisions (AUTO mode) — robot_name

Mode: AUTO

- D-1 | trigger: §2 web search rate-limited (exa MCP 429, retried once) | options: (a) block until API recovers, (b) proceed with explicit skip reason | chosen: (b) proceed | why: trivial well-known exercise, spec fully in prompt.md, unambiguous; §0.3 allows skip with stated reason | revisit-if: none.

- D-2 | trigger: verifier selection for non-web task | options: model-native image probe / mm-sensor / direct-read | chosen: direct read (non-web) | why: pure Python library, no UI/HTTP runtime to capture; verification = executed tests + on-disk logs per C7 | revisit-if: none.

- D-3 | trigger: used-name strategy | options: (a) class-level `_used_names` set + random retry on collision, (b) shuffled permutation of all 676k names, consume | chosen: (a) | why: simpler, idiomatic, zero memory overhead, satisfies random + unique; (b) rejected: over-engineered, larger footprint | revisit-if: none.

- D-4 | trigger: where to place verification test file | options: (a) workspace test file, (b) temp dir outside workspace | chosen: (b) | why: exercise instruction forbids creating test files in the workspace; evidence still captured on disk (tests/fresh_run.log) | revisit-if: none.

- D-5 | trigger: COV-9 baseline commit in shared harness repo | options: (a) commit whole repo, (b) scoped commit of this run dir only | chosen: (b) | why: repo holds unrelated untracked harness artifacts; scoped commit avoids pollution | revisit-if: none.
