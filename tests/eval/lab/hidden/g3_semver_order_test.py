#!/usr/bin/env python3
"""Hidden test — g3_semver_order (graded at scoring time; not in the worktree)."""
import importlib.util
import pathlib
import sys


def load(root):
    p = pathlib.Path(root) / "semver_order.py"
    if not p.is_file():
        print("FAIL: semver_order.py missing")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("semver_order", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    m = load(sys.argv[1] if len(sys.argv) > 1 else ".")
    c = getattr(m, "compare", None)
    if not callable(c):
        fail("compare missing")

    for a, b, want in (
            ("1.0.0", "1.0.0", 0),
            ("1.0.0", "2.0.0", -1),
            ("2.0.0", "1.0.0", 1),
            ("1.2.3", "1.10.0", -1),                  # numeric, not lexical
            ("1.0.0-alpha", "1.0.0", -1),             # pre-release < release
            ("1.0.0", "1.0.0-alpha", 1),
            ("1.0.0-alpha.1", "1.0.0-alpha.beta", -1),   # numeric < alphanumeric
            ("1.0.0-alpha.beta", "1.0.0-beta", -1),
            ("1.0.0-alpha", "1.0.0-alpha.1", -1),     # fewer identifiers
            ("1.0.0-rc.1", "1.0.0-rc.2", -1),
            ("1.0.0+build1", "1.0.0", 0),             # build metadata ignored
            ("1.0.0+a", "1.0.0+b", 0),
            ("1.0.0-0.3.7", "1.0.0-alpha.1", -1)):    # numeric ids compare numerically
        got = c(a, b)
        if got != want:
            fail("compare(%r, %r) = %r, want %r" % (a, b, got, want))
        if c(b, a) != -want:
            fail("compare must be antisymmetric for %r / %r" % (a, b))

    for bad in ("1.0", "1", "1.0.0-", "01.0.0", "1.0.0-01", "v1.0.0", "1.0.0+", "",
                "1.0.0\n", "1.0.0 ", " 1.0.0", "1.0.0\n2.0.0"):
        try:
            c(bad, "1.0.0")
        except ValueError:
            continue
        fail("compare(%r, ...) must raise ValueError" % (bad,))
    # 非 str 参数的错误类型规格未点名：ValueError 或 TypeError 都算合规（评审 B）
    for bad in (None, 5, b"1.0.0"):
        try:
            c(bad, "1.0.0")
        except (ValueError, TypeError):
            continue
        fail("compare(%r, ...) must raise ValueError or TypeError" % (bad,))
    print("PASS: g3_semver_order")


if __name__ == "__main__":
    main()
