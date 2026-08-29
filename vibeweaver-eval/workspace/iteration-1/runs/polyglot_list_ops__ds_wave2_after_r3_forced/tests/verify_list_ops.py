"""Verification driver for list_ops.py (vibeweaver C7 non-web library).

Deliberately NOT named test_*.py / *_test.py so it stays out of the
exercise test-suite's pytest collection (task constraint: do not create or
modify the exercise's test files). This driver exercises the public API and
prints a per-check verdict; exit code 0 = all checks pass.

Checks map 1:1 to tests/acceptance.md criteria 1-11.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import list_ops


def check(name, cond, detail=""):
    mark = "PASS" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
    return cond


def run():
    results = []
    ok = True

    # C1: append — result = list1 ++ list2, no mutation
    a, b = [1, 2], [3, 4]
    r = list_ops.append(a, b)
    ok &= check("C1 append basic", r == [1, 2, 3, 4], f"got {r}")
    ok &= check("C1 append empty-second", list_ops.append([1], []) == [1])
    ok &= check("C1 append empty-first", list_ops.append([], [1]) == [1])
    ok &= check("C1 append both-empty", list_ops.append([], []) == [])
    ok &= check("C1 append no-mutation",
                a == [1, 2] and b == [3, 4], f"a={a} b={b}")

    # C2: concat — flatten series of lists
    ok &= check("C2 concat basic",
                list_ops.concat([[1, 2], [3, 4]]) == [1, 2, 3, 4])
    ok &= check("C2 concat three",
                list_ops.concat([[1], [2, 3], [], [4]]) == [1, 2, 3, 4])
    ok &= check("C2 concat empty-series", list_ops.concat([]) == [])
    ok &= check("C2 concat empty-lists", list_ops.concat([[], []]) == [])

    # C3: filter
    ok &= check("C3 filter evens",
                list_ops.filter(lambda x: x % 2 == 0, [1, 2, 3, 4]) == [2, 4])
    ok &= check("C3 filter all-true",
                list_ops.filter(lambda x: x > 0, [1, 2]) == [1, 2])
    ok &= check("C3 filter none-true",
                list_ops.filter(lambda x: x > 10, [1, 2]) == [])
    ok &= check("C3 filter empty", list_ops.filter(lambda x: True, []) == [])

    # C4: length
    ok &= check("C4 length basic", list_ops.length([1, 2, 3]) == 3)
    ok &= check("C4 length empty", list_ops.length([]) == 0)
    ok &= check("C4 length singleton", list_ops.length([None]) == 1)
    ok &= check("C4 length strings",
                list_ops.length(["a", "b", "c", "d"]) == 4)

    # C5: map
    ok &= check("C5 map double", list_ops.map(lambda x: x * 2, [1, 2, 3]) == [2, 4, 6])
    ok &= check("C5 map str",
                list_ops.map(lambda x: x.upper(), ["a", "b"]) == ["A", "B"])
    ok &= check("C5 map empty", list_ops.map(lambda x: x, []) == [])

    # C6: foldl — function(accumulator, item), left to right
    ok &= check("C6 foldl sum", list_ops.foldl(lambda acc, i: acc + i, [1, 2, 3], 0) == 6)
    ok &= check("C6 foldl concat",
                list_ops.foldl(lambda acc, i: acc + i, ["a", "b", "c"], "") == "abc")
    ok &= check("C6 foldl empty", list_ops.foldl(lambda acc, i: acc, [], 42) == 42)
    ok &= check("C6 foldl sub-order",
                list_ops.foldl(lambda acc, i: acc - i, [10, 20, 30], 100) == 40)

    # C7: foldr — function(accumulator, item), right to left
    ok &= check("C7 foldr concat",
                list_ops.foldr(lambda acc, i: acc + i, ["a", "b", "c"], "") == "cba")
    ok &= check("C7 foldr sub-order",
                list_ops.foldr(lambda acc, i: acc - i, [10, 20, 30], 100) == 40)
    ok &= check("C7 foldr empty", list_ops.foldr(lambda acc, i: acc, [], "z") == "z")
    ok &= check("C7 foldr order-sens",
                list_ops.foldr(lambda acc, i: f"{acc}{i}", [1, 2, 3], "") == "321")
    ok &= check("C7 foldl order-sens",
                list_ops.foldl(lambda acc, i: f"{acc}{i}", [1, 2, 3], "") == "123")

    # C8: reverse — new list, no mutation
    s = [1, 2, 3]
    ok &= check("C8 reverse basic", list_ops.reverse(s) == [3, 2, 1])
    ok &= check("C8 reverse empty", list_ops.reverse([]) == [])
    ok &= check("C8 reverse singleton", list_ops.reverse([7]) == [7])
    ok &= check("C8 reverse no-mutation", s == [1, 2, 3], f"s={s}")

    # C10: import cleanliness is implied by `import list_ops` succeeding at top.

    # C9: implementation does not delegate to builtin higher-order list ops.
    with open("list_ops.py", encoding="utf-8") as fh:
        src = fh.read()
    forbidden = ["reversed(", "sorted(", ".reverse(", "[::-1]", "= sum(",
                 "return sum(", "itertools", "functools"]
    hits = [tok for tok in forbidden if tok in src]
    ok &= check("C9 no-builtin-delegation", not hits, f"hits={hits}" if hits else "clean")

    # C11: no grader test files created (static check of tree)
    import glob
    testfiles = glob.glob("test_*.py") + glob.glob("*_test.py")
    ok &= check("C11 no grader test files", not testfiles, f"found={testfiles}" if testfiles else "none")

    print(f"\nRESULT: {'ALL PASS' if ok else 'FAILURES PRESENT'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    run()
