# simple_linked_list

- type: project
- updated: 2026-08-29
- trust: ✅ Verified (25/25 executed cases pass, `tests/verification_run.log`)

## Implemented behavior (verified)
- `LinkedList(values=None)` builds by pushing each value onto the head (LIFO):
  `LinkedList([1,2,3])` iterates as `[3,2,1]`, `len == 3`, `head().value() == 3`.
- `push(value)` inserts at head; `pop()` removes+returns head value (LIFO).
- `head()` / `pop()` on an empty list raise `EmptyListException` whose
  `args[0] == "The list is empty."` (message attribute also set).
- `Node.value()` / `Node.next()`; head `next()` chain ends at `None`.
- `reversed()` returns a NEW `LinkedList` built from `self` iteration
  (input-ordered result: `reversed([1,2,3])` iterates `[1,2,3]`); does not
  mutate the original.

## Contract details to keep (do not regress)
- `EmptyListException` must keep `args[0]` message AND `.message` attribute —
  implemented via `super().__init__(message)` in addition to `self.message`.
- `__init__(values=None)` must treat `None` as empty; `values=[]` must equal an
  empty list (test `reversed([])` depends on it).
- No other files were created/modified beyond `simple_linked_list.py` + skill
  artifacts (`tests/`, `memory/`, `script/linux/`).

## A4.9 review rulings (2026-08-29, Minor findings accepted as-is)
- `push` sets `new_node._next` directly — matches canonical reference, harmless.
- Generator `__iter__` vs canonical `LinkedIterator` class — functionally equivalent.
- No docstrings/type hints — consistent with the stub's bare style.
