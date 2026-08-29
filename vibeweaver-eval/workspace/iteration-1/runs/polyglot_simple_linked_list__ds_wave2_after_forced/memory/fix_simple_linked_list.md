---
title: simple_linked_list implementation
status: verified
date: 2026-08-29
tags: [linked-list, exercism, python]
---

# simple_linked_list

## Verified
- Implemented `Node`, `LinkedList`, `EmptyListException` in `simple_linked_list.py`.
- Semantics: LIFO stack — constructor pushes values in order (head = last value), `push` prepends, `pop` removes head, `__iter__` yields head→tail, `reversed()` returns a new reversed `LinkedList`, empty `head()`/`pop()` raise `EmptyListException("The list is empty.")`.
- Canonical Exercism test suite passes 20/20 (run from temp dir; no test files added to workspace).
- Evidence: `tests/verification_log.md` iter 1 PASS; transcript in temp dir `sll_verify/run_transcript.txt`.

## Notes
- Do not add test files to the workspace (harness constraint).
- No script/ dir in this run; pure library, no build/lifecycle.
