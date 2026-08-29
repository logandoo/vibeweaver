"""Differential sweep: list_ops.py vs independent builtin oracles.

The oracle uses DIFFERENT primitives than the candidate (builtin +, len,
reversed, functools.reduce, sum) so it does not share the candidate's
iteration structure. Sweeps edge cases (empty/singleton) + randomized lists.
"""

import random
import sys
import functools

sys.path.insert(0, ".")  # project root

import list_ops

random.seed(20260829)


def ref_append(a, b):
    out = a[:]
    for x in b:
        out.append(x)
    return out


def ref_concat(lists):
    out = []
    for lst in lists:
        out += list(lst)
    return out


def ref_reverse(a):
    return list(reversed(a))


def build_cases(n):
    cases = [[], [0], [1], [-5, 0, 5], list(range(7))]
    for _ in range(n):
        size = random.randint(0, 12)
        cases.append([random.randint(-100, 100) for _ in range(size)])
    return cases


failures = 0


def cmp(name, actual, expected):
    global failures
    if actual != expected:
        failures += 1
        print(f"MISMATCH {name}: got {actual!r} want {expected!r}")


cases = build_cases(400)

for a in cases:
    for b in build_cases(50):
        cmp("append", list_ops.append(a, b), ref_append(a, b))

for outer in build_cases(120):
    lists = []
    for _ in range(random.randint(0, 5)):
        lists.append(random.choice(cases))
    cmp("concat", list_ops.concat(lists), ref_concat(lists))

for c in cases:
    cmp("length", list_ops.length(c), len(c))
    cmp("reverse", list_ops.reverse(c), ref_reverse(c))
    cmp("map", list_ops.map(lambda x: x * x, c), [x * x for x in c])
    cmp("filter", list_ops.filter(lambda x: x > 0, c), [x for x in c if x > 0])
    cmp("foldl-sum", list_ops.foldl(lambda a, x: a + x, c, 0), sum(c))
    cmp("foldr-sum", list_ops.foldr(lambda a, x: a + x, c, 0), sum(c))
    cmp("foldl-reduce", list_ops.foldl(lambda a, x: a - x, c, 1000),
        functools.reduce(lambda a, x: a - x, c, 1000))
    cmp("foldr-reduce", list_ops.foldr(lambda a, x: a - x, c, 1000),
        functools.reduce(lambda a, x: a - x, ref_reverse(c), 1000))

# foldr order property: string consing right-to-left == reversed string
for c in cases:
    s = "".join(chr(97 + (x % 26)) for x in c)
    cmp("foldr-order", list_ops.foldr(lambda a, i: a + i, list(s), ""), "".join(reversed(s)))
    cmp("foldl-order", list_ops.foldl(lambda a, i: a + i, list(s), ""), s)

if failures:
    print(f"DIFF-SWEEP: {failures} MISMATCHES")
    sys.exit(1)
print(f"DIFF-SWEEP: ALL AGREE ({len(cases)} base cases x sweeps, no mismatches)")
