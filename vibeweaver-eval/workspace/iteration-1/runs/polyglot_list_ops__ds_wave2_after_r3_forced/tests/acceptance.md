> cap=5  stall=3×

# Acceptance Criteria — list_ops exercise (C7 non-web library)

Verifier: direct read (non-web). Each criterion is a yes/no checkable on
observable function output via the verification driver transcript.

1. `append(list1, list2)` returns a new list containing all items of list1
   followed by all items of list2; neither input list is mutated.
2. `concat(lists)` returns a single flattened list combining all items from
   all lists in the given series, in order.
3. `filter(function, list)` returns a new list of all items for which
   `function(item)` is True, preserving order.
4. `length(list)` returns the total number of items in the list (0 for an
   empty list).
5. `map(function, list)` returns a new list of `function(item)` applied to
   every item, preserving order.
6. `foldl(function, list, initial)` folds from the left, calling
   `function(accumulator, item)` for each item in order, returning the final
   accumulator.
7. `foldr(function, list, initial)` folds from the right, calling
   `function(accumulator, item)` over items in reverse order, returning the
   final accumulator.
8. `reverse(list)` returns a new list with all original items in reversed
   order; the input list is not mutated.
9. Every operation is implemented by explicit iteration/construction — none
   delegates to a builtin higher-order list operation (map/filter/reduce/
   sorted/sum/reversed as the implementation).
10. The module imports cleanly (`python3 -c "import list_ops"`) with no
    syntax or runtime errors, and handles empty-list edge cases.
11. No file matching the exercise test-suite discovery patterns
    (`test_*.py` / `*_test.py`) is created or modified; the verification
    driver is named `verify_list_ops.py` to stay out of pytest collection.
