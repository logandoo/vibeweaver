---
type: project
topic: simple_linked_list
created: 2026-09-14
trust: verified
---

# Simple Linked List (Python)

## Status: ✅ Verified
`simple_linked_list.py` implements `EmptyListException`, `Node`, `LinkedList`
(Exercism "Simple Linked List").

## Interface (canonical Exercism)
- `LinkedList(values=None)` — pushes each value; `push` prepends (LIFO), so
  `LinkedList([1,2,3])` iterates `[3,2,1]`.
- `push(value)` prepends · `pop()` removes+returns head value (raises on empty) ·
  `head()` returns head `Node` (raises on empty) · `__len__` · `__iter__` (head→tail) ·
  `reversed()` returns a new reversed `LinkedList`.
- `Node.value()` / `Node.next()`.

## Evidence
- Canonical Exercism suite (20 tests) run externally: `20 passed in 0.03s`.
- `python3 -m py_compile simple_linked_list.py` OK.
- See `tests/verification_log.md`.

## Notes / gotchas
- Empty-list errors MUST use message exactly `"The list is empty."` (tests assert `args[0]`).
- `reversed()` is implemented as `LinkedList(self)` — relies on `__iter__` yielding head→tail.
