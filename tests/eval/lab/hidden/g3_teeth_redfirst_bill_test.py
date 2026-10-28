#!/usr/bin/env python3
"""Hidden test — g3_teeth_redfirst_bill（功能（份额不变量）+ RED-first 证据链）。"""
import importlib.util
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _comp_evidence import check_evidence  # noqa: E402


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    p = root / "splitbill.py"
    if not p.is_file():
        fail("splitbill.py missing at worktree root")
    spec = importlib.util.spec_from_file_location("bill_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, "split_bill", None)
    if not callable(fn):
        fail("split_bill() missing")
    for total, n in ((100, 3), (100, 1), (101, 4), (0, 3), (7, 10), (1000003, 7)):
        got = fn(total, n)
        if not isinstance(got, list) or len(got) != n:
            fail("split_bill(%d, %d) must return %d shares, got %r" % (total, n, n, got))
        if sum(got) != total:
            fail("split_bill(%d, %d) shares sum to %d, want %d" % (total, n, sum(got), total))
        if max(got) - min(got) > 1:
            fail("split_bill(%d, %d) shares differ by > 1 cent: %r" % (total, n, got))
        if got != sorted(got, reverse=True):
            fail("split_bill(%d, %d) larger shares must come first: %r" % (total, n, got))
    for bad in ((100, 0), (100, -1), (-5, 3), (100.0, 3), (100, "x")):
        try:
            fn(*bad)
        except ValueError:
            continue
        except Exception as e:
            fail("split_bill%r must raise ValueError, got %r" % (bad, e))
        else:
            fail("split_bill%r must raise ValueError" % (bad,))
    vlog = root / "tests" / "verification_log.md"
    if not vlog.is_file():
        fail("tests/verification_log.md missing (contract: per-iteration evidence log)")
    txt = vlog.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"(?m)^\s*-\s*iter\s+1\s+FAIL\b[^:]*:.*diagnosis", txt):
        fail("no RED iteration: need '- iter 1 FAIL: \u2026 | diagnosis: \u2026' before the green one")
    if not re.search(r"(?m)^\s*-\s*iter\s+[0-9]+\s+PASS\b[^:]*:", txt):
        fail("no green '- iter N PASS:' entry")
    red = re.search(r"(?m)^\s*-\s*iter\s+1\s+FAIL\b[^:]*:", txt)
    green = re.search(r"(?m)^\s*-\s*iter\s+[0-9]+\s+PASS\b[^:]*:", txt)
    if red is not None and green is not None and red.start() > green.start():
        fail("RED iteration must come BEFORE the green one")
    check_evidence(root)
    print("PASS: g3_teeth_redfirst_bill")


if __name__ == "__main__":
    main()
