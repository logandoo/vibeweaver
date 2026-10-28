#!/usr/bin/env python3
"""Hidden test — g3_idempotent_journal (graded at scoring time; not in the worktree)."""
import importlib.util
import pathlib
import sys


def load(root):
    p = pathlib.Path(root) / "idempotent_journal.py"
    if not p.is_file():
        print("FAIL: idempotent_journal.py missing")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("idempotent_journal", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    m = load(sys.argv[1] if len(sys.argv) > 1 else ".")
    J = getattr(m, "Journal", None)
    if not callable(J):
        fail("Journal missing")

    j = J()
    if j.total() != 0 or j.count() != 0:
        fail("fresh journal must be empty")
    if j.apply("a", 1) is not True:
        fail("first apply of 'a' must return True")
    if j.apply("a", 2) is not False:
        fail("second apply of 'a' must return False")
    if j.total() != 1 or j.count() != 1:
        fail("duplicate must have NO effect: total=%r count=%r" % (j.total(), j.count()))
    if j.apply("b", -3) is not True:
        fail("negative values are allowed and must apply")
    if j.total() != -2 or j.count() != 2:
        fail("totals wrong after 'b': %r / %r" % (j.total(), j.count()))

    j2 = J()
    for k in ("x", "y", "z"):
        j2.apply(k, 10)
    if j2.total() != 30 or j2.count() != 3:
        fail("three entries must sum to 30")

    for bad in (("", 1), ("   ", 1), (None, 1), (5, 1), ("a", "1"), ("a", True), ("a", None)):
        try:
            J().apply(*bad)
        except ValueError:
            continue
        fail("apply%s must raise ValueError" % (bad,))
    print("PASS: g3_idempotent_journal")


if __name__ == "__main__":
    main()
