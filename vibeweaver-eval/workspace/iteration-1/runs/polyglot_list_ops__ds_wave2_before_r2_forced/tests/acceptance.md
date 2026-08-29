# Acceptance Criteria — list-ops exercise

> cap=5  stall=3×

Source: prompt.md (exercise instructions) — canonical behavior cross-checked against the Exercism Python track list-ops test suite (exercism/problem-specifications list-ops canonical-data.json).

1. `append(list1, list2)` returns a new list containing all items of `list1` followed by all items of `list2` (empty inputs handled; input lists not mutated).
2. `concat(lists)` returns a single-level flattened list of all items across a series of lists (including empty lists; nested lists flattened one level only).
3. `filter(function, list)` returns a new list of every item for which `function(item)` is True (empty list → empty list).
4. `length(list)` returns the number of items in the list (empty list → 0).
5. `map(function, list)` returns a new list of `function(item)` for every item (empty list → empty list).
6. `foldl(function, list, initial)` folds items left-to-right, applying `function(acc, item)` (empty list → `initial`).
7. `foldr(function, list, initial)` folds items right-to-left, applying `function(acc, item)` with items consumed from the right end (empty list → `initial`).
8. `reverse(list)` returns the list with the original items in reversed order, without flattening nested lists (empty list → empty list).
9. All eight functions are implemented in list_ops.py; the module imports with no syntax errors.
