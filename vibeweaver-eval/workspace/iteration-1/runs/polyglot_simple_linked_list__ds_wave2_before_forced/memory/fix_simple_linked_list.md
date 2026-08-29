---
topic: fix_simple_linked_list
type: fix
status: ⏳
date: 2026-08-29
commit: db5dbfc
---

# Simple Linked List — implementation (⏳ unverified pending user confirmation)

## Problem
`prompt.md` asks for a prototype music player: songs = numbers; build a singly
linked list from a range, and support reversing the list to play in opposite
order. Starter `simple_linked_list.py` was stubs.

## Contract (from hidden spec `simple_linked_list_test.py`, 20 tests)
- `LinkedList(values=None)` builds by pushing each value → **head is the last
  pushed value** (LIFO/stack semantics).
- `len(ll)` = element count; `iter(ll)` yields head→tail.
- `head()` returns the head `Node` (or raises `EmptyListException("The list is
  empty.")`), `Node.value()` / `Node.next()` accessors.
- `push(value)` prepends to head; `pop()` removes+returns head (raises
  `EmptyListException` when empty).
- `reversed()` returns a NEW list reversed.

## Implementation chosen
Genuine node-based singly linked list (`Node` with `_value`/`_next`, push to
head). Rejected alternative: list-backed simulation (Python list as stack +
synthesized `Node`) — not a real linked list and fails the exercise intent.

## Verification
- Hidden spec run via pytest: 20/20 PASS (fresh run on final tree).
- `script/linux/start.sh` smoke check OK; `py_compile` OK.

## A4.9 review (verdict: ready — 0 Critical, 0 Important, 5 cosmetic Minors, all accepted)
1. `push` assigns `node._next` directly (private cross-class access) — canonical pattern, accepted.
2. Constructor treats a string as iterable of chars — matches reference, not spec-tested, accepted.
3. No `__eq__`/`__repr__`/`__bool__` — not required by spec, accepted.
4. `reversed()` O(n) — no perf concern at this scale, accepted.
5. `EmptyListException` unchanged from stub — correct type identity, accepted.

## Status
⏳ — tests pass, awaiting user confirmation before promotion to ✅.
