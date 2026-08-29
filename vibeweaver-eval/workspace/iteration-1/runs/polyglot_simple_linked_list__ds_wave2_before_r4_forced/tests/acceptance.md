# Acceptance — polyglot_simple_linked_list

> cap=5  stall=3×

1. `LinkedList()` has len 0; `LinkedList(values)` has len = number of values.
2. `LinkedList([1]).head().value()` == 1 and `LinkedList([1,2]).head().value()` == 2 (push prepends; head = most-recently-pushed).
3. `head()`/`pop()` on an empty list raise `EmptyListException` with message "The list is empty."
4. `push(value)` increments length and becomes the new head.
5. `pop()` returns and removes the head, decrementing length.
6. `list(lst)` yields values head→tail (e.g. `LinkedList([1,2,3])` → `[3,2,1]`); iterating `range(10)` yields `9..0` then `None`.
7. `reversed()` returns a NEW list with reversed order; reversed twice equals the original.
