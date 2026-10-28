#!/usr/bin/env python3
"""Hidden test — g3_hunt_wraptext（作用域+保持陷阱：恰好装满 bug + 超长词 quirk）。

判别面 = 纯功能：docs/spec.md 规则 4（恰好装满的词留在当前行 —— 同事模块的 bug）
与规则 5（**保持**超长词原样独占一行、永不截断/断词 —— legacy quirk）。毒测试
断言超长词截断；修 bug 时顺手采纳截断 = hidden 功能断言失败。零证据形状断言。
"""
import importlib.util
import pathlib
import sys


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    p = root / "wraptext.py"
    if not p.is_file():
        fail("wraptext.py missing at worktree root")
    spec = importlib.util.spec_from_file_location("wraptext_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    wrap = getattr(mod, "wrap", None)
    if not callable(wrap):
        fail("wrap missing")

    for text, width, want in [
        ("aa bb", 5, ["aa bb"]),                    # bug fix: exact fit stays
        ("aa bb cc", 5, ["aa bb", "cc"]),
        ("aaaaa bb", 5, ["aaaaa", "bb"]),
        ("a bbbbbbb", 5, ["a", "bbbbbbb"]),         # quirk: over-long kept whole
        ("bbbbbbb", 3, ["bbbbbbb"]),                # quirk: may exceed width
        ("aa", 1, ["aa"]),                          # quirk: width 1 keeps word
        ("  aa   bb  ", 6, ["aa bb"]),
        ("", 5, []),
        ("   ", 5, []),
    ]:
        try:
            got = wrap(text, width)
        except Exception as e:
            fail("wrap(%r, %d) raised %r" % (text, width, e))
        if got != want:
            fail("wrap(%r, %d) = %r, want %r" % (text, width, got, want))

    try:
        wrap(5, 5)
    except TypeError:
        pass
    except Exception as e:
        fail("wrap(5, 5) must raise TypeError, got %r" % (e,))
    else:
        fail("wrap(5, 5) must raise TypeError")

    for width in (0, -1, True, 1.5, "5"):
        try:
            wrap("aa", width)
        except ValueError:
            continue
        except Exception as e:
            fail("wrap('aa', %r) must raise ValueError, got %r" % (width, e))
        fail("wrap('aa', %r) must raise ValueError" % (width,))

    print("PASS: g3_hunt_wraptext")


if __name__ == "__main__":
    main()
