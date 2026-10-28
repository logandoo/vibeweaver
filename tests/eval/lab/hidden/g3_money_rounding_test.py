#!/usr/bin/env python3
"""Hidden test — g3_money_rounding (graded at scoring time; not in the worktree)."""
import importlib.util
import pathlib
import sys


def load(root):
    p = pathlib.Path(root) / "money_rounding.py"
    if not p.is_file():
        print("FAIL: money_rounding.py missing")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("money_rounding", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    m = load(sys.argv[1] if len(sys.argv) > 1 else ".")
    s = getattr(m, "sum_amounts", None)
    if not callable(s):
        fail("sum_amounts missing")

    if s([]) != "0.00":
        fail("empty list must return '0.00', got %r" % (s([]),))
    for values, want in (
            (["0.1", "0.2"], "0.30"),
            (["0.025"], "0.02"),          # ties to even (naive round -> 0.03)
            (["0.015"], "0.02"),          # ties to even
            (["2.675"], "2.68"),          # float trap: 2.675 is 2.6749... in binary
            (["2.665"], "2.66"),          # ties to even
            (["1.005", "2.005"], "3.01"),
            (["10.1234567890", "-3.1234567890"], "7.00")):
        got = s(values)
        if got != want:
            print("FAIL: sum_amounts(%r) = %r, want %r" % (values, got, want))
            sys.exit(1)

    # 负零的符号拼写**规格未规定** —— 两种写法都算合规（评审 B：过度规定会误杀）
    zeroish = s(["-0.005"])
    if zeroish not in ("-0.00", "0.00"):
        print("FAIL: sum_amounts(['-0.005']) = %r, want '-0.00' or '0.00'" % (zeroish,))
        sys.exit(1)

    for bad in (["abc"], ["1.0.0.0"], [""], [1.0], ["nan"], ["Infinity"], ["-inf"], ["0x10"]):
        try:
            s(bad)
        except ValueError:
            continue
        print("FAIL: sum_amounts(%r) must raise ValueError" % (bad,))
        sys.exit(1)
    print("PASS: g3_money_rounding")


if __name__ == "__main__":
    main()
