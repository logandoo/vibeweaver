> cap=5  stall=3×

# Acceptance Criteria — list_ops

Behavioral criteria derived from prompt.md (the eight operations) and the
official Exercism Python list-ops test suite. Each criterion is a single
checkable pass/fail assertion.

1. append([], []) == []
2. append([], [1,2,3,4]) == [1,2,3,4]
3. append([1,2,3,4], []) == [1,2,3,4]
4. append([1,2],[2,3,4,5]) == [1,2,2,3,4,5]
5. concat([]) == []
6. concat([[1,2],[3],[],[4,5,6]]) == [1,2,3,4,5,6]
7. concat flattens exactly one level: concat([[[1],[2]],[[3]],[[]],[[4,5,6]]]) == [[1],[2],[3],[],[4,5,6]]
8. filter(lambda x: x % 2 == 1, []) == []
9. filter(lambda x: x % 2 == 1, [1,2,3,5]) == [1,3,5]
10. length([]) == 0
11. length([1,2,3,4]) == 4
12. map(lambda x: x+1, []) == []
13. map(lambda x: x+1, [1,3,5,7]) == [2,4,6,8]
14. foldl(lambda acc, el: el*acc, [], 2) == 2
15. foldl(lambda acc, el: el+acc, [1,2,3,4], 5) == 15
16. foldl direction-dependent: foldl(lambda acc, el: el/acc, [1,2,3,4], 24) == 64
17. foldr(lambda acc, el: el*acc, [], 2) == 2
18. foldr(lambda acc, el: el+acc, [1,2,3,4], 5) == 15
19. foldr direction-dependent (right-to-left): foldr(lambda acc, el: el/acc, [1,2,3,4], 24) == 9
20. reverse([]) == []
21. reverse([1,3,5,7]) == [7,5,3,1]
22. reverse does not flatten: reverse([[1,2],[3],[],[4,5,6]]) == [[4,5,6],[],[3],[1,2]]
23. foldr over strings: foldr(lambda acc, el: el+acc, ["e","x","e","r","c","i","s","m"], "!") == "exercism!"
24. reverse mixed types: reverse(["xyz", 4.0, "cat", 1]) == [1, "cat", 4.0, "xyz"]
25. No syntax errors on module import; all eight stub signatures preserved
