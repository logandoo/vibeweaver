---
name: vibeweaver-mini
description: |
  MANDATORY for every coding task: run the checker, fix the first failure, repeat
  until it prints ALL CHECKS PASS. Do not claim done before that line.
---

# Mini — the deterministic loop

You are a small model. Do not rely on memory, judgment, or planning. Follow
this loop exactly. It is mechanical on purpose.

1. Run `python3 vw_check.py` — if it is not in the project root, copy it there
   from the skill's `scripts/vw_check.py` (or run the project's `script/check.sh`).
2. Read its output. It tells you exactly what is missing or failing.
3. Fix ONLY the first problem it names. Save the file.
4. Run the checker again.
5. Repeat until it prints exactly: `ALL CHECKS PASS`.
6. Report done ONLY by quoting that line. Nothing else counts as done.

If there are no tests at all, build the feedback first:
- List EVERY function, class, method, and error message named in the spec. One line each.
- Write `spec_test.py`: one test per requirement, expected values copied from the spec's own examples.
- Then run the loop above.

Hard rules:
- The project's own tests are the only oracle that certifies. A suite you wrote
  yourself is weak evidence — say so when you report.
- Never edit, delete, or weaken a test to make it pass. The checker refuses to
  run if the test set changed. Fix the CODE.
- Read the assertion: left = your output, right = expected. Change the code to match.
- Do not invent interfaces: a required function/class/method not visible in the
  spec or starter is an open question — flag it, do not guess.
- One fix per iteration. No essays. If the same check fails 3 times, re-read the
  spec line it comes from before changing anything again.
