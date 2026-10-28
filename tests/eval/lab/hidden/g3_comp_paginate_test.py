#!/usr/bin/env python3
"""Hidden test — g3_comp_paginate (compliance 任务族：功能 + 证据构件)。"""
import importlib.util
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _comp_evidence import check_evidence  # noqa: E402


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def load(root, name, modname):
    p = pathlib.Path(root) / name
    if not p.is_file():
        fail("%s missing" % name)
    spec = importlib.util.spec_from_file_location(modname, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    m = load(root, "paginate.py", "paginate_c")
    f = getattr(m, "paginate", None)
    if not callable(f):
        fail("paginate missing")

    data = list(range(10))
    got = f(data, 1, 3)
    if got != ([0, 1, 2], 4):
        fail("paginate(10, page 1, pp 3) = %r, want ([0,1,2], 4)" % (got,))
    if f(data, 4, 3) != ([9], 4):
        fail("last partial page wrong: %r" % (f(data, 4, 3),))
    if f(data, 1, 10) != (list(data), 1):
        fail("single-page case wrong")
    out = f(data, 2, 3)
    out[0].append("mutated")
    if len(data) != 10:
        fail("page_items must be a NEW list, not a view of the input")
    # tuple 输入（spec 允许 list or tuple），返回切片应为 list
    got_t = f((1, 2, 3, 4), 2, 2)
    if got_t != ([3, 4], 2) or not isinstance(got_t[0], list):
        fail("tuple input wrong: %r" % (got_t,))
    if f([1, 2, 3], 1, 3) != ([1, 2, 3], 1):
        fail("exact-multiple full page wrong")
    try:
        f([1, 2, 3], 2, 3)
        fail("page 2 of a 1-page input must raise ValueError")
    except ValueError:
        pass

    try:
        f([], 1, 5)
        fail("empty items + any page must raise (out of range; total_pages == 0)")
    except (ValueError, TypeError):
        pass
    for args, why in (((data, 0, 3), "page 0"), ((data, 5, 3), "page beyond total"),
                      ((data, "1", 3), "str page"), ((data, 1, "3"), "str per_page"),
                      ((data, 1.0, 3), "float page"), ((data, 3, 1.5), "float per_page")):
        try:
            f(*args)
        except (ValueError, TypeError):
            continue
        fail("%s must raise" % why)
    for bad, why in (((data, True, 1), "bool page"), ((data, 1, True), "bool per_page")):
        try:
            f(*bad)
        except ValueError:
            continue
        fail("%s must raise ValueError specifically (bool is an int subclass)" % why)

    check_evidence(root)
    print("PASS: g3_comp_paginate")


if __name__ == "__main__":
    main()
