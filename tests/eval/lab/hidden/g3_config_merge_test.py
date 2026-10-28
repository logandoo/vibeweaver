#!/usr/bin/env python3
"""Hidden test — g3_config_merge (graded at scoring time; not in the worktree)."""
import importlib.util
import pathlib
import sys


def load(root):
    p = pathlib.Path(root) / "config_merge.py"
    if not p.is_file():
        print("FAIL: config_merge.py missing")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("config_merge", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    m = load(sys.argv[1] if len(sys.argv) > 1 else ".")
    merge = getattr(m, "merge", None)
    if not callable(merge):
        fail("merge missing")

    if merge({"a": {"b": 1, "c": 2}}, {"a": {"c": 3}}) != {"a": {"b": 1, "c": 3}}:
        fail("nested dicts must merge deeply")
    if merge({"a": 1}, {"a": None}) != {}:
        fail("None override must delete the key")
    if merge({}, {"a": None}) != {}:
        fail("deleting an absent key must be a no-op")
    if merge({"l": [1, 2, 3]}, {"l": [9]}) != {"l": [9]}:
        fail("lists must be REPLACED, not concatenated")
    if merge({"n": {"x": 1}}, {"n": 5}) != {"n": 5}:
        fail("a scalar replaces a nested dict")
    if merge({"n": 5}, {"n": {"x": 1}}) != {"n": {"x": 1}}:
        fail("a nested dict replaces a scalar")

    base = {"a": {"b": 1}, "keep": [1, 2]}
    over = {"a": {"c": 2}, "new": {"deep": True}}
    base_copy = {"a": {"b": 1}, "keep": [1, 2]}
    over_copy = {"a": {"c": 2}, "new": {"deep": True}}
    out = merge(base, over)
    if out != {"a": {"b": 1, "c": 2}, "keep": [1, 2], "new": {"deep": True}}:
        fail("merge result wrong: %r" % (out,))
    if base != base_copy or over != over_copy:
        fail("inputs must not be modified: %r / %r" % (base, over))
    if out["a"] is base["a"] or out["keep"] is base["keep"] or out["new"] is over["new"]:
        fail("result must not share mutable objects with the inputs")
    out["a"]["b"] = 99
    if base["a"]["b"] != 1:
        fail("mutating the result leaked into the input")

    for bad in (([], {}), ({}, []), (None, {}), ({}, "x")):
        try:
            merge(*bad)
        except ValueError:
            continue
        fail("merge%s must raise ValueError" % (bad,))
    print("PASS: g3_config_merge")


if __name__ == "__main__":
    main()
