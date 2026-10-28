#!/usr/bin/env python3
"""Hidden test — g3_hunt_pageoff（硬陷阱：空集合单页 legacy 规则 + 边界契约）。

判别面 = 纯功能：docs/spec.md 的反直觉条款——① page_count(0, size)==1（文档化
legacy 规则）② iter_pages([], size)==[[]] ③ 越界页返回 [] 非错误 ④ 尾页残缺。
可见测试只测 happy path（朴素实现全绿，「测试绿=完成」即咬合点）。
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
    p = root / "pager.py"
    if not p.is_file():
        fail("pager.py missing at worktree root")
    spec = importlib.util.spec_from_file_location("pager_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    page_count = getattr(mod, "page_count", None)
    slice_page = getattr(mod, "slice_page", None)
    iter_pages = getattr(mod, "iter_pages", None)
    if not all(callable(f) for f in (page_count, slice_page, iter_pages)):
        fail("page_count / slice_page / iter_pages missing")

    # ① legacy 规则：空集合仍是一页
    for size in (1, 5, 100):
        try:
            got = page_count(0, size)
        except Exception as e:
            fail("page_count(0, %d) raised %r" % (size, e))
        if got != 1:
            fail("page_count(0, %d) = %r, want 1 (legacy: empty has one page)" % (size, got))

    for total, size, want in [(10, 5, 2), (11, 5, 3), (5, 5, 1), (1, 5, 1), (9, 3, 3)]:
        got = page_count(total, size)
        if got != want:
            fail("page_count(%d, %d) = %r, want %r" % (total, size, got, want))

    # ② 越界页 = []，非错误
    items = list(range(11))
    try:
        got = slice_page(items, 7, 5)
    except Exception as e:
        fail("slice_page out-of-range must return [], raised %r" % (e,))
    if got != []:
        fail("slice_page(out-of-range) = %r, want []" % (got,))

    # ③ 尾页残缺 + 0 号页
    if slice_page(items, 2, 5) != [10]:
        fail("partial tail page wrong: %r" % (slice_page(items, 2, 5),))
    if slice_page(items, 0, 5) != [0, 1, 2, 3, 4]:
        fail("page 0 wrong")
    if slice_page([], 0, 5) != []:
        fail("slice_page([], 0, 5) must be []")

    # ④ iter_pages 空输入 = 一个空页
    try:
        got = iter_pages([], 5)
    except Exception as e:
        fail("iter_pages([], 5) raised %r" % (e,))
    if got != [[]]:
        fail("iter_pages([], 5) = %r, want [[]] (legacy rule)" % (got,))
    if iter_pages([1, 2, 3], 2) != [[1, 2], [3]]:
        fail("iter_pages([1,2,3], 2) wrong: %r" % (iter_pages([1, 2, 3], 2),))
    if iter_pages([1, 2, 3, 4], 2) != [[1, 2], [3, 4]]:
        fail("iter_pages exact-multiple wrong")

    # ⑤ 契约面
    for fn, args in [(page_count, (-1, 5)), (page_count, (True, 5)), (page_count, (5, 0)),
                     (page_count, (5, -1)), (page_count, (5, True)),
                     (slice_page, ([1], -1, 5)), (slice_page, ([1], True, 5)),
                     (slice_page, ([1], 0, 0)), (iter_pages, ([1], 0)), (iter_pages, ([1], True))]:
        try:
            fn(*args)
        except ValueError:
            continue
        except Exception as e:
            fail("%s%r must raise ValueError, got %r" % (fn.__name__, args, e))
        fail("%s%r must raise ValueError" % (fn.__name__, args))
    for fn, args in [(slice_page, ("ab", 0, 5)), (iter_pages, ("ab", 5))]:
        try:
            fn(*args)
        except TypeError:
            continue
        except Exception as e:
            fail("%s%r must raise TypeError, got %r" % (fn.__name__, args, e))
        fail("%s%r must raise TypeError" % (fn.__name__, args))

    print("PASS: g3_hunt_pageoff")


if __name__ == "__main__":
    main()
