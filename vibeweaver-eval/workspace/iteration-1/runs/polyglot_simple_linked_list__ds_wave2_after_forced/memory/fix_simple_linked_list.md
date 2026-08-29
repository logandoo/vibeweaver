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

## Review adjudication (A4.9 — minors, non-blocking)
- M1 quality: `new_node._next = self._head` reaches into Node internals (simple_linked_list.py:41). Ruling: accepted — module-internal, canonical pattern.
- M2 bugs(edge): str input yields char-by-char list. Ruling: accepted — contract is list/range only.
- M3 quality: `_len -= 1` before value extraction (simple_linked_list.py:48). Ruling: accepted — safe today (Node.value never raises).
- M4 quality: duplicated message string (lines 36/47). Ruling: accepted — trivial.

## Notes
- Do not add test files to the workspace (harness constraint).
- Library-only run; script/linux/{start,stop,restart}.sh are COV-2 lifecycle stubs (no persistent server).
