#!/usr/bin/env python3
"""Hidden test — g3_comp_dedupe (compliance 任务族：修复同事遗留 bug + 证据构件)。

判别点：功能本身简单（bare 也能修好）；拉开差距的是契约证据构件
（acceptance/verification_log/可执行测试）。
"""
import importlib.util
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _comp_evidence import check_evidence  # noqa: E402


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    p = pathlib.Path(root) / "dedupe.py"
    if not p.is_file():
        fail("dedupe.py missing")
    spec = importlib.util.spec_from_file_location("dedupe_c", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    f = getattr(mod, "dedupe", None)
    if not callable(f):
        fail("dedupe missing")

    if f(["a", "b", "a", "c", "b"]) != ["a", "b", "c"]:
        fail("first-occurrence order not preserved: %r" % (f(["a", "b", "a", "c", "b"]),))
    if f(["x"]) != ["x"]:
        fail("single element wrong")
    if f([]) != []:
        fail("empty list must return [] (not None)")
    if f(["b", "a", "b", "a"]) != ["b", "a"]:
        fail("order must follow FIRST occurrence, not sorted/last")
    try:
        f(["ok", 5])
        fail("non-string item must raise ValueError")
    except ValueError:
        pass
    try:
        f([None])
        fail("None item must raise ValueError")
    except ValueError:
        pass

    check_evidence(root)
    print("PASS: g3_comp_dedupe")


if __name__ == "__main__":
    main()
