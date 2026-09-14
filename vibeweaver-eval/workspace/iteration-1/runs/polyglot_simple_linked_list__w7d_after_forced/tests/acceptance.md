> cap=5  stall=3×

# Acceptance Criteria — simple_linked_list (Exercism "Simple Linked List")

Derived from the canonical Exercism Python test suite (fetched during ZERO research).

1. `LinkedList()` has `len == 0`.
2. `LinkedList([1])` has `len == 1`; `LinkedList([1,2,3])` has `len == 3`.
3. `head()` on an empty list raises `EmptyListException` with `args[0] == "The list is empty."`.
4. `head().value()` returns the most recently pushed value (LIFO): `LinkedList([1,2]).head().value() == 2`.
5. `push(v)` prepends and increases length by 1; pushing to an empty list sets the head.
6. `pop()` removes and returns the head value and decreases length; popping an empty/singleton-to-empty list raises `EmptyListException("The list is empty.")`.
7. `list(linked_list)` yields values from head to tail (`LinkedList([1,2,3]) -> [3,2,1]`).
8. `reversed()` returns a new list whose iteration is the reverse of the original; empty -> `[]`, singleton -> same, `[1,2,3] -> [1,2,3]`.
9. `Node.next()` is `None` for the tail (singleton head has no next).
10. Traversal via repeated `.next()` visits every node and ends with `None`.
11. Module imports and executes without syntax or runtime errors.

Owner: user (task spec + canonical Exercism tests). Immutable once set.
