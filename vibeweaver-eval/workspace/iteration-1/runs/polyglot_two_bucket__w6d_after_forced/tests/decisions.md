# Decisions — two_bucket (Mode: AUTO)

D-1 | trigger: skill mandates tests/ artifacts vs. user instruction "do NOT create or modify any test files" | options: (a) create no artifacts at all, (b) create non-executable evidence logs under tests/ + memory, no test code | chosen: (b) | why: acceptance.md/verification_log.md are documentation logs, not test files; they satisfy the skill's evidence gate without violating the user's ban on test files | revisit-if: user clarifies that no files under tests/ are permitted

D-2 | trigger: approach selection (BFS vs. two-strategy simulation) | options: (a) BFS over all reachable states, (b) simulate the two pour directions and take the minimum | chosen: (a) | why: BFS is provably minimal under the arbitrary forbidden-state rule; the two-strategy shortcut is only valid for the unconstrained puzzle | revisit-if: state space becomes too large for BFS (not the case here)
