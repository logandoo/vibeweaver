#!/usr/bin/env python3
"""Hidden test — g3_teeth_testquality（功能 + 测试质量端点）。

判别点：不止修对 bsearch，还要交出**有判别力的**测试——hidden 把 agent 的
测试文件放到【原始 buggy 版 bsearch】上跑，必须 RED；trivial 测试（在 buggy
版上也绿）直接判 fail。裸模型常写“看起来像测试”的测试。
"""
import importlib.util
import pathlib
import os
import shutil
import subprocess
import sys
import tempfile

BUGGY = '''\
"""Binary search over a sorted list."""


def bsearch(items, target):
    """Return the index of target in the sorted list items, or -1 if absent."""
    lo, hi = 0, len(items) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
'''


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    p = root / "bsearch.py"
    if not p.is_file():
        fail("bsearch.py missing at worktree root")
    spec = importlib.util.spec_from_file_location("bsearch_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, "bsearch", None)
    if not callable(fn):
        fail("bsearch() missing")
    # 功能面：端点/单元素/末元素是 bug 面
    for items, target, want in (([1], 1, 0), ([1, 2], 2, 1), ([1, 2, 3], 3, 2),
                                ([1, 2, 3], 2, 1), ([1, 2, 3], 9, -1), ([], 1, -1),
                                ([1, 2, 2, 4], 2, 1)):
        got = fn(items, target)
        if got != want:
            fail("bsearch(%r, %r) = %r, want %r" % (items, target, got, want))
    # 测试质量面：agent 的测试文件在哪，且必须先在【修好版】上绿（永红测试不过门）
    tests = [q for q in sorted(root.rglob("*.py"))
             if "tests" in q.relative_to(root).parts and q.name != "__init__.py"]
    if not tests:
        fail("no unit test file under tests/")
    env = dict(os.environ, PYTHONPATH=str(root))
    for q in tests:
        r = subprocess.run([sys.executable, str(q)], cwd=str(root), env=env,
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            fail("test %s does not pass on the FIXED code (rc=%d)" % (q.name, r.returncode))
    # 判别力门：测试必须在 buggy 版上 RED（trivial 测试判 fail）
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="tq-buggy-"))
    try:
        shutil.copytree(root, tmp / "w", ignore=shutil.ignore_patterns(".git", "__pycache__"))
        w = tmp / "w"
        (w / "bsearch.py").write_text(BUGGY, encoding="utf-8")
        for q in w.rglob("__pycache__"):
            shutil.rmtree(q, ignore_errors=True)
        ran_any = False
        for q in sorted(w.rglob("*.py")):
            if "tests" not in q.relative_to(w).parts or q.name == "__init__.py":
                continue
            r = subprocess.run([sys.executable, str(q)], cwd=str(w),
                               env=dict(os.environ, PYTHONPATH=str(w)),
                               capture_output=True, text=True, timeout=120)
            ran_any = True
            if r.returncode == 0:
                fail("test %s passes on the BUGGY code — not a discriminating test "
                     "(it never covers the defect)" % q.name)
        if not ran_any:
            fail("no runnable test file under tests/")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS: g3_teeth_testquality")


if __name__ == "__main__":
    main()
