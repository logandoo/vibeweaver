> cap=5  stall=3×

# Acceptance Criteria — list_ops

Task: implement the 8 basic list operations in `list_ops.py` (Exercism "list-ops",
Python track). Verifier: direct read (non-web). Loop bound: cap=5, stall=3×.

1. `append([], [])` returns `[]`
2. `append([], [1, 2, 3, 4])` returns `[1, 2, 3, 4]`
3. `append([1, 2, 3, 4], [])` returns `[1, 2, 3, 4]`
4. `append([1, 2], [2, 3, 4, 5])` returns `[1, 2, 2, 3, 4, 5]`
5. `concat([])` returns `[]`
6. `concat([[1, 2], [3], [], [4, 5, 6]])` returns `[1, 2, 3, 4, 5, 6]`
7. `concat([[[1], [2]], [[3]], [[]], [[4, 5, 6]]])` returns `[[1], [2], [3], [], [4, 5, 6]]` (one level only, not recursive)
8. `filter(is_odd, [])` returns `[]`
9. `filter(is_odd, [1, 2, 3, 5])` returns `[1, 3, 5]`
10. `length([])` returns `0`
11. `length([1, 2, 3, 4])` returns `4`
12. `map(x + 1, [])` returns `[]`
13. `map(x + 1, [1, 3, 5, 7])` returns `[2, 4, 6, 8]`
14. `foldl(lambda acc, el: el * acc, [], 2)` returns `2`
15. `foldl(lambda acc, el: el + acc, [1, 2, 3, 4], 5)` returns `15`
16. `foldl(lambda acc, el: el / acc, [1, 2, 3, 4], 24)` returns `64`
17. `foldr(lambda acc, el: el * acc, [], 2)` returns `2`
18. `foldr(lambda acc, el: el + acc, [1, 2, 3, 4], 5)` returns `15`
19. `foldr(lambda acc, el: el / acc, [1, 2, 3, 4], 24)` returns `9`
20. `foldr(lambda acc, el: el + acc, ["e","x","e","r","c","i","s","m"], "!")` returns `"exercism!"`
21. `reverse([])` returns `[]`
22. `reverse([1, 3, 5, 7])` returns `[7, 5, 3, 1]`
23. `reverse([[1, 2], [3], [], [4, 5, 6]])` returns `[[4, 5, 6], [], [3], [1, 2]]`
24. Module imports with no syntax/runtime error and defines exactly `append, concat, filter, length, map, foldl, foldr, reverse`.
