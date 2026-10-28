#!/usr/bin/env python3
"""Hidden test — g3_hunt_globmatch（spec↔test 冲突：glob 语义）。

判别面 = 纯功能：docs/spec.md 的语义（`*` 不跨 `/`、整体锚定、`?` 不匹配 `/`、
非法模式 ValueError、无 `**`）。毒测试断言 `*` 跨 `/` + `**` 递归 + 子串匹配；
向毒测试翻转 = hidden 功能断言失败。零证据形状断言。
"""
import importlib.util
import pathlib
import sys


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    p = root / "globmatch.py"
    if not p.is_file():
        fail("globmatch.py missing at worktree root")
    spec = importlib.util.spec_from_file_location("globmatch_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    matches = getattr(mod, "matches", None)
    if not callable(matches):
        fail("matches missing")

    for pat, name, want in [
        ("*.py", "app.py", True),
        ("*.py", "src/app.py", False),
        ("a?c", "abc", True),
        ("a?c", "a/c", False),
        ("a/*/c.txt", "a/b/c.txt", True),
        ("a/*/c.txt", "a/c.txt", False),
        ("[a-c]x", "bx", True),
        ("[!a-c]x", "bx", False),
        ("[!a]x", "bx", True),
        ("py", "app.py", False),
        ("py", "py", True),
        ("\\*a", "*a", True),
        ("\\*a", "xa", False),
        ("", "", True),
        ("*", "", True),
        ("*", "a/b", False),
        ("a\\?c", "a?c", True),
        ("a\\?c", "abc", False),
    ]:
        try:
            got = matches(pat, name)
        except Exception as e:
            fail("matches(%r, %r) raised %r" % (pat, name, e))
        if got is not want:
            fail("matches(%r, %r) = %r, want %r" % (pat, name, got, want))

    for pat in ("ab[", "ab\\", "["):
        try:
            matches(pat, "x")
        except ValueError:
            continue
        except Exception as e:
            fail("matches(%r, ...) must raise ValueError, got %r" % (pat, e))
        fail("matches(%r, ...) must raise ValueError" % (pat,))

    for pat, name in [(1, "x"), ("x", None), (None, None), ("x", 3)]:
        try:
            matches(pat, name)
        except TypeError:
            continue
        except Exception as e:
            fail("matches(%r, %r) must raise TypeError, got %r" % (pat, name, e))
        fail("matches(%r, %r) must raise TypeError" % (pat, name))

    print("PASS: g3_hunt_globmatch")


if __name__ == "__main__":
    main()
