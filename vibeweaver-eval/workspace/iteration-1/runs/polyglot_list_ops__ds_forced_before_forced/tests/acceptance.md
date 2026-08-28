> cap=5  stall=3×

# Acceptance Criteria — list_ops.py (basic list operations)

1. `append(list1, list2)` returns a list with all items of `list2` added to the end of `list1` (`append([1, 2], [2, 3, 4, 5]) == [1, 2, 2, 3, 4, 5]`).
2. `append` handles empty operands (`append([], []) == []`, `append([], [1, 2, 3, 4]) == [1, 2, 3, 4]`, `append([1, 2, 3, 4], []) == [1, 2, 3, 4]`).
3. `concat(lists)` flattens a series of lists into one list, one level deep (`concat([[1, 2], [3], [], [4, 5, 6]]) == [1, 2, 3, 4, 5, 6]`; `concat([]) == []`).
4. `filter(function, list)` returns only the items for which `function(item)` is True (`filter(lambda x: x % 2 == 1, [1, 2, 3, 5]) == [1, 3, 5]`; empty list yields `[]`).
5. `length(list)` returns the total number of items (`length([1, 2, 3, 4]) == 4`; `length([]) == 0`).
6. `map(function, list)` returns the list of results of applying `function(item)` to all items (`map(lambda x: x + 1, [1, 3, 5, 7]) == [2, 4, 6, 8]`; empty list yields `[]`).
7. `foldl(function, list, initial)` folds each item into the accumulator from the left (`foldl(lambda acc, el: el / acc, [1, 2, 3, 4], 24) == 64`).
8. `foldl` returns the initial accumulator for an empty list (`foldl(lambda acc, el: el * acc, [], 2) == 2`).
9. `foldr(function, list, initial)` folds each item into the accumulator from the right (`foldr(lambda acc, el: el / acc, [1, 2, 3, 4], 24) == 9`).
10. `foldr` returns the initial accumulator for an empty list (`foldr(lambda acc, el: el * acc, [], 2) == 2`).
11. `foldr` works with non-numeric types (`foldr(lambda acc, el: el + acc, ["e", "x", "e", "r", "c", "i", "s", "m"], "!") == "exercism!"`).
12. `reverse(list)` returns all original items in reversed order without flattening (`reverse([1, 3, 5, 7]) == [7, 5, 3, 1]`; `reverse([[1, 2], [3], [], [4, 5, 6]]) == [[4, 5, 6], [], [3], [1, 2]]`; `reverse([]) == []`).
13. `list_ops.py` imports cleanly and all eight functions execute without syntax or runtime errors.
