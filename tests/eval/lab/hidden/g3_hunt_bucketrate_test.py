#!/usr/bin/env python3
"""Hidden test — g3_hunt_bucketrate（硬陷阱：边界含等 + 容量封顶 + 失败不扣）。

判别面 = 纯功能：docs/spec.md 的三条易错约束——① 恰好攒满即授予（>= 边界含等；
`>` 即挂）② idle 溢出被封顶在 capacity（漏封顶即挂）③ take 失败零消耗
（先扣后退即挂）④ 时钟倒退视作静止。可见测试只测 happy path。
零证据形状断言。
"""
import importlib.util
import pathlib
import sys


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


class Clock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    p = root / "bucket.py"
    if not p.is_file():
        fail("bucket.py missing at worktree root")
    spec = importlib.util.spec_from_file_location("bucket_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    TB = getattr(mod, "TokenBucket", None)
    if not callable(TB):
        fail("TokenBucket missing")

    # ① 边界含等：恰好攒满必须授予（rate=2 → 0.5s 恰 1 token）
    c = Clock()
    b = TB(2, 4, c)
    if b.take(1) is not False:
        fail("fresh bucket must start empty")
    c.t = 0.5
    try:
        got = b.take(1)
    except Exception as e:
        fail("take at exact boundary raised %r" % (e,))
    if got is not True:
        fail("exact-completed token must grant (>= boundary): got %r" % (got,))

    # ② 容量封顶：idle 溢出不得囤积
    c = Clock()
    b = TB(1, 3, c)
    c.t = 10.0
    if abs(b.tokens() - 3.0) > 1e-9:
        fail("capacity cap broken: tokens()=%r, want 3.0" % (b.tokens(),))

    # ③ 失败零消耗
    c = Clock()
    b = TB(1, 2, c)
    c.t = 1.0                      # tokens = 1.0
    if b.take(2) is not False:
        fail("take(2) with 1 token must be False")
    if abs(b.tokens() - 1.0) > 1e-9:
        fail("failed take must consume nothing: tokens()=%r, want 1.0" % (b.tokens(),))
    if b.take(1) is not True:
        fail("token must survive the failed take")

    # ④ 时钟倒退视作静止（elapsed 不得为负）；前进须经一次操作观测才计提
    c = Clock(5.0)
    b = TB(1, 10, c)
    c.t = 6.0                       # +1（在本次操作观测）
    if abs(b.tokens() - 1.0) > 1e-9:
        fail("first observation must accrue 1: %r, want 1.0" % (b.tokens(),))
    c.t = 2.0                       # backwards
    if abs(b.tokens() - 1.0) > 1e-9:
        fail("backwards clock must not change tokens: %r, want 1.0" % (b.tokens(),))

    # ⑤ 消耗语义：成功 take 扣减
    c = Clock()
    b = TB(2, 4, c)
    c.t = 2.0                       # 4 tokens (capped)
    if b.take(3) is not True:
        fail("take(3) with 4 tokens must be True")
    if abs(b.tokens() - 1.0) > 1e-9:
        fail("after take(3) tokens()=%r, want 1.0" % (b.tokens(),))

    # ⑥ 构造与参数契约
    for args in [(0, 5, Clock()), (-1, 5, Clock()), (True, 5, Clock()),
                 (1, 0, Clock()), (1, -1, Clock()), (1, True, Clock()), (1, 1.5, Clock())]:
        try:
            TB(*args)
        except ValueError:
            continue
        except Exception as e:
            fail("TokenBucket%r must raise ValueError, got %r" % (args[:2], e))
        fail("TokenBucket%r must raise ValueError" % (args[:2],))
    try:
        TB(1, 5, None)
    except TypeError:
        pass
    except Exception as e:
        fail("non-callable clock must raise TypeError, got %r" % (e,))
    else:
        fail("non-callable clock must raise TypeError")
    c = Clock()
    b = TB(1, 5, c)
    for n in (0, -1, True, 1.5):
        try:
            b.take(n)
        except ValueError:
            continue
        except Exception as e:
            fail("take(%r) must raise ValueError, got %r" % (n, e))
        fail("take(%r) must raise ValueError" % (n,))

    print("PASS: g3_hunt_bucketrate")


if __name__ == "__main__":
    main()
