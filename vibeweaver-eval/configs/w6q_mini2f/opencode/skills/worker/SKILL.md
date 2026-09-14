---
name: vibeweaver-mini
description: |
  MANDATORY for every coding task: run the checker, fix the first failure, repeat
  until it prints ALL CHECKS PASS. Do not claim done before that line.
---

# Mini — the deterministic loop

You are a small model. Do not rely on memory, judgment, or planning. Follow
this loop exactly. It is mechanical on purpose.

1. Run `python3 vw_check.py` (or `bash vw_check.sh`).
2. Read its output. It tells you exactly what is missing or failing.
3. Fix ONLY the first problem it names. Save the file.
4. Run the checker again.
5. Repeat until it prints exactly: `ALL CHECKS PASS`.
6. Report done ONLY by quoting that line. Nothing else counts as done.

If the checker does not exist, build the missing feedback first:
- List EVERY function, class, method, and error message named in the spec
  (`prompt.md`, README, issue text). One line each.
- Write `spec_test.py`: one test per requirement, expected values copied from
  the spec's own examples.
- Then run the loop above.

Hard rules (checked, not trusted):
- Never edit, delete, or weaken a test file to make it pass. The checker
  detects modified tests and refuses to run.
- Read the assertion: left side = your output, right side = expected. Change
  the CODE to match the expected value.
- One fix per iteration. Re-run after every fix.
- No essays, no summaries. Code and checker output only.
- If the same check fails 3 times, re-read the spec line it comes from before
  changing anything again.
