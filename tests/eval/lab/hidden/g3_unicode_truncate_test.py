#!/usr/bin/env python3
"""Hidden test — g3_unicode_truncate (graded at scoring time; not in the worktree)."""
import importlib.util
import pathlib
import sys


def load(root):
    p = pathlib.Path(root) / "unicode_truncate.py"
    if not p.is_file():
        print("FAIL: unicode_truncate.py missing")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("unicode_truncate", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    m = load(sys.argv[1] if len(sys.argv) > 1 else ".")
    t = getattr(m, "truncate", None)
    if not callable(t):
        fail("truncate missing")

    for text, width, want in (
            ("你好世界", 5, "你好"),        # wide chars cost 2
            ("你好世界", 4, "你好"),
            ("你好世界", 8, "你好世界"),
            ("a你b", 3, "a你"),            # mixed widths
            ("a你b", 2, "a"),              # 你 does not fit
            ("ab", 5, "ab"),               # shorter than budget
            ("", 3, ""),                   # empty text
            ("a\u0301b", 1, "a\u0301"),   # combining mark stays attached
            ("abc", 0, "")):               # zero budget
        got = t(text, width)
        if got != want:
            fail("truncate(%r, %d) = %r, want %r" % (text, width, got, want))

    if t("a你", 2) != "a":
        fail("wide char must not fit into width 2 after a 1-wide char")
    for args in (("abc", -1), ("abc", 1.5), ("abc", True), (5, 1)):
        try:
            t(*args)
        except ValueError:
            continue
        fail("truncate%s must raise ValueError" % (args,))
    print("PASS: g3_unicode_truncate")


if __name__ == "__main__":
    main()
