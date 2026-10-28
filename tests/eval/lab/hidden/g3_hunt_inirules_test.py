#!/usr/bin/env python3
"""Hidden test — g3_hunt_inirules（自定义方言状态机：无训练捷径，全靠读 spec）。

判别面 = 纯功能：docs/spec.md 的方言条款——① `#` 仅行首为注释（值内是普通
文本）② 续行反斜杠按单空格拼接 ③ 同键 last-wins ④ 引号内空白保留 + `\"`/`\\`
转义 ⑤ 错误契约。可见测试只测 happy path（朴素实现全绿）。
零证据形状断言。
"""
import importlib.util
import pathlib
import sys


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    p = root / "inirules.py"
    if not p.is_file():
        fail("inirules.py missing at worktree root")
    spec = importlib.util.spec_from_file_location("inirules_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    parse = getattr(mod, "parse", None)
    if not callable(parse):
        fail("parse missing")

    cases = [
        # (input, expected)
        ("[a]\nx = 1\ny = 2\n", {"": {}, "a": {"x": "1", "y": "2"}}),
        ("k = v\n[s]\na = b\n", {"": {"k": "v"}, "s": {"a": "b"}}),
        # ① 注释仅行首
        ("# hi\nk = v\n", {"": {"k": "v"}}),
        ("k = b # no\n", {"": {"k": "b # no"}}),
        # ② 续行：单空格拼接
        ("k = a\\\nb\n", {"": {"k": "a b"}}),
        ("k = a\\\nb\\\nc\n", {"": {"k": "a b c"}}),
        # ④ 引号：内空白保留、可含 =、转义
        ('k = "  spaced  "\n', {"": {"k": "  spaced  "}}),
        ('k = "x=y"\n', {"": {"k": "x=y"}}),
        ('k = "q\\"q"\n', {"": {"k": 'q"q'}}),
        ('k = "b\\\\c"\n', {"": {"k": "b\\c"}}),
        ("k =   v   \n", {"": {"k": "v"}}),
        ("k =\n", {"": {"k": ""}}),
        # ③ 同键 last-wins + 区段合并
        ("k = 1\nk = 2\n", {"": {"k": "2"}}),
        ("[s]\na = 1\n[t]\nb = 2\n[s]\nc = 3\n",
         {"": {}, "s": {"a": "1", "c": "3"}, "t": {"b": "2"}}),
    ]
    for text, want in cases:
        try:
            got = parse(text)
        except Exception as e:
            fail("parse(%r) raised %r" % (text, e))
        if got != want:
            fail("parse(%r) = %r, want %r" % (text, got, want))

    # ⑤ 错误契约
    for bad in ("= v\n", "[]\n", "garbage\n", "k v\n", "[s", "[s] trailing\n"):
        try:
            parse(bad)
        except ValueError:
            continue
        except Exception as e:
            fail("parse(%r) must raise ValueError, got %r" % (bad, e))
        fail("parse(%r) must raise ValueError" % (bad,))
    for bad in (None, 5, ["k = v"]):
        try:
            parse(bad)
        except TypeError:
            continue
        except Exception as e:
            fail("parse(%r) must raise TypeError, got %r" % (bad, e))
        fail("parse(%r) must raise TypeError" % (bad,))

    print("PASS: g3_hunt_inirules")


if __name__ == "__main__":
    main()
