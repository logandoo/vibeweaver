# Project Memory — polyglot_simple_linked_list

Index of topic knowledge for this coding exercise.

## Project
- **simple_linked_list.py** — Exercism "Simple Linked List" (Python). Implements a
  LIFO singly linked list: `EmptyListException`, `Node(value/next)`, and
  `LinkedList` (`__init__(values)`, `__iter__`, `__len__`, `head`, `push`, `pop`,
  `reversed`). Head = last-pushed value; `list(LinkedList([1,2,3])) == [3,2,1]`;
  `reversed()` returns `LinkedList(self)` so its iteration is `[1,2,3]`.
- Empty-list operations (`head`, `pop`) raise `EmptyListException("The list is empty.")`.

## Verified (✅)
- ✅ 2026-09-14 — Official Exercism suite `simple_linked_list_test.py` (20 tests) passes 20/20.
- ✅ 2026-09-14 — `py_compile` OK; direct smoke of push/pop/len/head/reversed/empty-raise OK.

## Review findings (Minor — deferred, COV-8/A4.9)
- Minor [Compliance] `push` sets `node._next` directly (encapsulation note); matches official reference, no defect.
- Minor [Compliance] `EmptyListException` has no `.message` attribute (bare `Exception`); official tests only use `args[0]`.

## Forbidden / Constraints (⛔)
- ⛔ Do NOT create or modify any test files in the workspace (task constraint). Official
  suite is run from `/tmp/sll_test` via `PYTHONPATH=<workspace>`.
