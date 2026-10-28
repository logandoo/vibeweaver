#!/usr/bin/env python3
"""Hidden test — g3_hunt_cachetouch（作用域+保持陷阱：evict 反向 bug + no-touch quirk）。

判别面 = 纯功能：docs/spec.md 的插入序语义 —— ① `evict_oldest()` 淘汰最旧键
（同事模块的 bug：反向淘汰）② **保持** `put` 重写不移位、`get` 不移位（legacy
quirk：显式非 LRU）。毒测试断言 LRU touch 语义；修 bug 时顺手改 LRU = hidden
功能断言失败。零证据形状断言。
"""
import importlib.util
import pathlib
import sys


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    p = root / "cachetouch.py"
    if not p.is_file():
        fail("cachetouch.py missing at worktree root")
    spec = importlib.util.spec_from_file_location("cachetouch_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    Cache = getattr(mod, "Cache", None)
    if not callable(Cache):
        fail("Cache missing")

    c = Cache()
    if len(c) != 0:
        fail("new cache must be empty, got len=%d" % len(c))
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    if len(c) != 3 or c.keys() != ["a", "b", "c"]:
        fail("insertion order broken: keys=%r len=%d" % (c.keys(), len(c)))

    # bug fix: oldest first
    try:
        v = c.evict_oldest()
    except Exception as e:
        fail("evict_oldest() raised %r" % (e,))
    if v != "a":
        fail("evict_oldest() = %r, want 'a' (oldest)" % (v,))
    if c.keys() != ["b", "c"]:
        fail("after eviction keys=%r, want ['b', 'c']" % (c.keys(),))

    # quirk 1: re-put keeps original position (NOT a touch)
    c.put("b", 22)
    if c.get("b") != 22:
        fail("re-put must update the value")
    if c.keys() != ["b", "c"]:
        fail("re-put must keep insertion position: keys=%r, want ['b', 'c']" % (c.keys(),))
    try:
        v = c.evict_oldest()
    except Exception as e:
        fail("evict_oldest() raised %r" % (e,))
    if v != "b":
        fail("after re-put, evict_oldest() = %r, want 'b' (still oldest)" % (v,))

    # quirk 2: get never affects ordering
    c2 = Cache()
    c2.put("x", 1)
    c2.put("y", 2)
    if c2.get("x") != 1:
        fail("get returned wrong value")
    try:
        v = c2.evict_oldest()
    except Exception as e:
        fail("evict_oldest() raised %r" % (e,))
    if v != "x":
        fail("get must not touch: evict_oldest() = %r, want 'x'" % (v,))

    # error contract
    try:
        c2.get("missing")
    except KeyError:
        pass
    except Exception as e:
        fail("get(missing) must raise KeyError, got %r" % (e,))
    else:
        fail("get(missing) must raise KeyError")
    try:
        Cache().evict_oldest()
    except LookupError:
        pass
    except Exception as e:
        fail("evict_oldest() on empty must raise LookupError, got %r" % (e,))
    else:
        fail("evict_oldest() on empty must raise LookupError")
    for bad in ("", 5, None):
        try:
            Cache().put(bad, 1)
        except ValueError:
            continue
        except Exception as e:
            fail("put(%r, 1) must raise ValueError, got %r" % (bad, e))
        fail("put(%r, 1) must raise ValueError" % (bad,))

    print("PASS: g3_hunt_cachetouch")


if __name__ == "__main__":
    main()
