#!/usr/bin/env python3
"""Hidden test — g3_transfer_invariant (graded at scoring time; not in the worktree)."""
import importlib.util
import pathlib
import sys


def load(root):
    p = pathlib.Path(root) / "transfer.py"
    if not p.is_file():
        print("FAIL: transfer.py missing")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("transfer", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    m = load(sys.argv[1] if len(sys.argv) > 1 else ".")
    t = getattr(m, "transfer", None)
    if not callable(t):
        fail("transfer missing")

    src = {"a": 10, "b": 5}
    got = t(src, "a", "b", 3)
    if got != {"a": 7, "b": 8}:
        fail("normal transfer wrong: %r" % (got,))
    if src != {"a": 10, "b": 5}:
        fail("input state was mutated: %r" % (src,))
    if got is src:
        fail("transfer must return a NEW dict")

    same = t({"a": 1}, "a", "a", 1)
    if not isinstance(same, dict) or same != {"a": 1}:
        fail("src==dst must copy the state unchanged: %r" % (same,))
    # 规格：insufficient-funds 只在 src != dst 时检查 —— src==dst 超额也应成功
    over = t({"a": 1}, "a", "a", 5)
    if not isinstance(over, dict) or over != {"a": 1}:
        fail("src==dst with amount > balance must still succeed: %r" % (over,))

    for args in (({"a": 1, "b": 0}, "a", "b", 5),      # insufficient funds
                 ({"a": 1}, "a", "zz", 1),            # unknown dst
                 ({"a": 1}, "zz", "a", 1),            # unknown src
                 ({"a": 1, "b": 1}, "a", "b", 0),     # zero amount
                 ({"a": 1, "b": 1}, "a", "b", -2),    # negative
                 ({"a": 1, "b": 1}, "a", "b", 1.5),   # non-int
                 ({"a": 1, "b": 1}, "a", "b", True)):   # bool is not int here
        state = args[0]
        before = dict(state)
        try:
            t(*args)
        except ValueError:
            if state != before:
                fail("state changed on error: %r -> %r" % (before, state))
            continue
        fail("transfer%s must raise ValueError" % (args,))
    print("PASS: g3_transfer_invariant")


if __name__ == "__main__":
    main()
