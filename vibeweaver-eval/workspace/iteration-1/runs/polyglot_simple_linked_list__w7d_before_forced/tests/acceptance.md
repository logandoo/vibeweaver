> cap=5  stall=3×

1. `simple_linked_list.py` imports cleanly (no syntax/runtime error) and defines `EmptyListException`, `Node`, `LinkedList`.
2. `LinkedList(values)` builds a LIFO singly linked list; `list(LinkedList([1,2,3])) == [3,2,1]`.
3. `len(LinkedList(values))` returns the element count (0 for empty).
4. `head()` returns the head `Node`; `head().value()` is the last-pushed value; on empty raises `EmptyListException("The list is empty.")`.
5. `push(v)` inserts at the head; `pop()` removes and returns the head value and decrements length; `pop()` on empty raises `EmptyListException("The list is empty.")`.
6. `reversed()` returns a new `LinkedList` whose iteration is the reverse of the original (`list(LinkedList([1,2,3]).reversed()) == [1,2,3]`).
7. The official Exercism `simple_linked_list_test.py` suite (20 tests) passes 20/20.
8. No test file is created or modified in the workspace.
