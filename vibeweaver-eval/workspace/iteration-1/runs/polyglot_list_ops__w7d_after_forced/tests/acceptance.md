> cap=5  stall=3×

# Acceptance Criteria — polyglot_list_ops

Task: implement the 8 basic list operations in `list_ops.py` without using the
existing library functions they are meant to reimplement.

1. `append(list1, list2)` returns a new list containing all items of `list1`
   followed by all items of `list2`; empty inputs yield `[]`.
2. `concat(lists)` returns one flattened list of all items in all input lists
   (exactly one level of flattening; nested lists stay nested).
3. `filter(function, list)` returns a list of every item for which
   `function(item)` is truthy, preserving order.
4. `length(list)` returns the total number of items in the list (0 for empty).
5. `map(function, list)` returns a list of `function(item)` for every item,
   preserving order.
6. `foldl(function, list, initial)` folds left-to-right, calling
   `function(accumulator, item)` for each item, starting from `initial`.
7. `foldr(function, list, initial)` folds right-to-left, calling
   `function(accumulator, item)` for each item, starting from `initial`.
8. `reverse(list)` returns a new list with the same items in reversed order
   (does not flatten a list of lists).
9. The module imports cleanly under Python 3 with no syntax or runtime errors,
   and each function returns the expected value on the canonical cases.

Verifier: direct read (non-web) — observable output = Python exit code + stdout transcript.
