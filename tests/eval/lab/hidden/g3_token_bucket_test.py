#!/usr/bin/env python3
"""Hidden test — g3_token_bucket (graded at scoring time; not in the worktree)."""
import importlib.util
import pathlib
import sys


def load(root):
    p = pathlib.Path(root) / "token_bucket.py"
    if not p.is_file():
        print("FAIL: token_bucket.py missing")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("token_bucket", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    m = load(sys.argv[1] if len(sys.argv) > 1 else ".")
    f = getattr(m, "refilled", None)
    if not callable(f):
        fail("refilled missing")

    for args, want in (((10.0, 5.0, 2.0, 12.0), 12.0),      # clamp at capacity
                       ((0.0, 2.5, 2.0, 10.0), 5.0),        # fractional refill
                       ((1.5, 0.0, 3.0, 10.0), 1.5),        # no elapsed -> unchanged
                       ((0.0, 1.0, 0.0, 10.0), 0.0),        # zero rate
                       ((3.0, 1000.0, 1.0, 4.0), 4.0)):     # long gap clamps
        got = f(*args)
        if not isinstance(got, (int, float)) or isinstance(got, bool):
            fail("refilled%s must return a number, got %r" % (args, got))
        if abs(float(got) - want) > 1e-9:
            fail("refilled%s = %r, want %r" % (args, got, want))

    for args in ((1.0, -1.0, 1.0, 5.0),      # negative elapsed
                 (-1.0, 1.0, 1.0, 5.0),      # negative tokens
                 (1.0, 1.0, -1.0, 5.0),      # negative rate
                 (1.0, 1.0, 1.0, 0.0),       # zero capacity
                 (6.0, 1.0, 1.0, 5.0),       # tokens above capacity
                 (True, 1.0, 1.0, 5.0),      # bool is not a number here
                 (1.0, 1.0, 1.0, "5")):      # non numeric
        try:
            f(*args)
        except ValueError:
            continue
        fail("refilled%s must raise ValueError" % (args,))
    print("PASS: g3_token_bucket")


if __name__ == "__main__":
    main()
