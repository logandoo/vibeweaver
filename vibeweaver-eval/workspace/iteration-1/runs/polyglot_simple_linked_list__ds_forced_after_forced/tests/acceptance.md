> cap=5  stall=3×
1. `len(LinkedList()) == 0` (empty list length 0).
2. `len(LinkedList([1])) == 1` (singleton length 1).
3. `len(LinkedList([1,2,3])) == 3` (non-empty length 3).
4. `LinkedList().head()` raises `EmptyListException` with message `"The list is empty."` (args[0]).
5. `LinkedList([1]).head().value() == 1` (singleton head value).
6. `LinkedList([1,2]).head().value() == 2` (head is most recently pushed).
7. `LinkedList([1,2,3]).push(4)` yields `len == 4` (push to non-empty).
8. `LinkedList().push(5)` yields `len == 1` and `head().value() == 5` (push to empty changes head).
9. `LinkedList([3,4,5]).pop() == 5`, then `len == 2` and `head().value() == 4` (LIFO pop).
10. `LinkedList([1]).pop() == 1` and subsequent `head()` raises `EmptyListException` (singleton pop clears head).
11. `LinkedList().pop()` raises `EmptyListException` with message `"The list is empty."` (pop empty).
12. `LinkedList([1,2]).push(3)` then pop → 3,2,1 then `len == 0`, then `push(4)` → `len == 1`, `head().value() == 4` (push/pop interleaved).
13. `LinkedList([1]).head().next() is None` (singleton head has no next).
14. `LinkedList(range(10))` traverses 9,8,...,0 then `None` (next() chain).
15. `list(LinkedList()) == []` (empty iteration).
16. `list(LinkedList([1])) == [1]` (singleton iteration).
17. `list(LinkedList([1,2,3])) == [3,2,1]` (LIFO iteration).
18. `list(LinkedList([]).reversed()) == []` (reverse empty).
19. `list(LinkedList([1]).reversed()) == [1]` (reverse singleton).
20. `list(LinkedList([1,2,3]).reversed()) == [1,2,3]` (reverse non-empty).
21. `simple_linked_list.py` imports and compiles with no syntax or runtime errors.
