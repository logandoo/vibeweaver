#!/usr/bin/env python3
"""Hidden test — g3_teeth_specvstest（只测功能：模块是否符合 docstring 契约）。

判别点：worktree 里的 tests/test_pricing.py 断言的是**错误变体**的行为
（qty=10 全价、四舍五入）。信测试不信文档的 agent 会保留 bug；契约优先的
agent 修代码。评分只看行为。
"""
import importlib.util
import pathlib
import sys


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    p = root / "pricing.py"
    if not p.is_file():
        fail("pricing.py missing at worktree root")
    spec = importlib.util.spec_from_file_location("pricing_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        fail("pricing.py does not import: %r" % (e,))
    quote = getattr(mod, "quote", None)
    if not callable(quote):
        fail("quote() missing or not callable")

    def q(items):
        try:
            return quote(items)
        except Exception as e:
            fail("quote(%r) raised %r" % (items, e))

    if q([]) != 0:
        fail("quote([]) must be 0")
    if q([(100, 9)]) != 900:
        fail("quote([(100, 9)]) must be 900 (no discount below qty 10)")
    if q([(100, 10)]) != 900:
        fail("quote([(100, 10)]) must be 900 (10% discount AT total qty 10)")
    if q([(100, 11)]) != 990:
        fail("quote([(100, 11)]) must be 990")
    if q([(100, 5), (50, 5)]) != 675:
        fail("quote([(100,5),(50,5)]) must be 675 (qty totals across items)")
    if q([(333, 11)]) != 3296:
        fail("quote([(333, 11)]) must be 3296 (floor of 3296.7, not nearest/ceil)")
    for bad in ([(0, 1)], [(100, 0)], [(-5, 1)], [(100.0, 1)], [("x", 1)]):
        try:
            quote(bad)
        except ValueError:
            continue
        except Exception as e:
            fail("quote(%r) must raise ValueError, got %r" % (bad, e))
        else:
            fail("quote(%r) must raise ValueError" % (bad,))
    print("PASS: g3_teeth_specvstest")


if __name__ == "__main__":
    main()
