> cap=5  stall=3×
1. Module imports with no syntax errors.
2. `LinkedList()` creates an empty list (`len == 0`), and iterating yields `[]`.
3. `LinkedList(values)` builds the list so iterating yields values head→tail, i.e. the last value is the head (LIFO stack semantics).
4. `push(value)` prepends a new node; the pushed value becomes `head()` and `len` increases.
5. `pop()` returns and removes the head value; `len` decreases.
6. `pop()` / `head()` on an empty list raise `EmptyListException` with message `"The list is empty."`.
7. `head()` returns the head `Node`; `Node.value()` returns its value and `Node.next()` returns the next node (`None` for the tail).
8. `reversed()` returns a NEW `LinkedList` that iterates in reverse order and leaves the original unmodified.
9. The canonical Exercism `simple-linked-list` test suite passes (20/20).
