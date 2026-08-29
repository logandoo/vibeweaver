---
name: Eval Workspace Agent
description: Autonomous agent role in a vibeweaver eval workspace — implement exercises without touching provided test files, verify via on-disk logs, follow forced skill workflow
type: user
date: 2026-08-29
---

# Eval Workspace Agent

This workspace is an automated evaluation harness. The agent is graded by an independent grader against hidden tests.

**Why:** The task constraint is explicit: do NOT create or modify the exercise's test files; only verify the code has no syntax/runtime errors.

**How to apply:** Keep all verification harness files out of pytest collection (name them `verify_*.py`, `diff_sweep.py`, `consumer_smoke.py`, never `test_*.py`/`*_test.py`), keep evidence as `.run.log` transcripts, and leave the provided `test_*.py` untouched.
