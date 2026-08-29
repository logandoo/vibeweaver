> cap=5  stall=3×
1. LinkedList([]) / LinkedList() has length 0 and raises EmptyListException on head() and pop().
2. LinkedList([1]) has length 1 and head().value() == 1.
3. push() prepends: after push(1),push(2) → len==2, head==2, head.next().value()==1.
4. pop() returns the head value and removes it; pop on empty raises EmptyListException.
5. Iteration yields values head-first: list(LinkedList([1,2,3])) == [3, 2, 1].
6. reversed() returns a fresh LinkedList with opposite order: list(LinkedList([1,2,3,4]).reversed()) == [1, 2, 3, 4]; original unchanged.
7. Node exposes value() and next(); module imports without syntax/runtime errors.
