#!/usr/bin/env python3
"""Hidden test — g3_hunt_conccounter（F1 并发不变量：check-then-act 原子性）。

判别面 = 纯功能：docs/spec.md 的硬不变量——并发调用下 count 永不超 cap、
每个成功调用返回 1..cap 的唯一值（check 与 +1 是不可分步）。可见测试只测
单线程（朴素 check-then-act 全绿，「测试绿=完成」即咬合点）；hidden 用
setswitchinterval(1e-6) + barrier 齐射压竞态窗口，无锁实现的功能性超卖
= hidden 断言挂。零证据形状断言。
"""
import importlib.util
import pathlib
import sys
import threading


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    p = root / "counter.py"
    if not p.is_file():
        fail("counter.py missing at worktree root")
    spec = importlib.util.spec_from_file_location("counter_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    Counter = getattr(mod, "Counter", None)
    if not callable(Counter):
        fail("Counter missing")

    # 单线程契约
    c = Counter(3)
    got = [c.incr_if_below() for _ in range(4)]
    if got != [1, 2, 3, 0]:
        fail("single-thread sequence wrong: %r" % (got,))
    if c.value() != 3 or c.remaining() != 0:
        fail("value/remaining wrong after cap")
    for bad in (0, -1, True, 1.5, "5"):
        try:
            Counter(bad)
        except ValueError:
            continue
        except Exception as e:
            fail("Counter(%r) must raise ValueError, got %r" % (bad, e))
        fail("Counter(%r) must raise ValueError" % (bad,))

    # 并发硬不变量：opcode 级让渡（确定性交错探测）——trace 回调在 incr_if_below
    # 的每个字节码边界 sleep(0) 让渡 GIL，把 check 与 +1 之间的竞态窗口强制切开：
    # 无锁 check-then-act 必被交错命中；带锁实现持有锁期间其他线程阻塞，不变量成立。
    import time as _time

    def tracer(frame, event, arg):
        if frame.f_code.co_name == "incr_if_below":
            if event == "call":
                frame.f_trace_opcodes = True
                return tracer
            if event == "opcode":
                _time.sleep(0)
                return tracer
        return tracer

    sys.setswitchinterval(1e-6)
    threading.settrace(tracer)
    try:
        for round_no in range(3):
            cap = 50
            c = Counter(cap)
            n_threads, per_thread = 8, 25
            results = []
            lock = threading.Lock()
            barrier = threading.Barrier(n_threads)

            def worker():
                barrier.wait()
                local = []
                for _ in range(per_thread):
                    local.append(c.incr_if_below())
                with lock:
                    results.extend(local)

            threads = [threading.Thread(target=worker) for _ in range(n_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=120)
            success = sorted(r for r in results if r)
            if len(results) != n_threads * per_thread:
                fail("lost calls in round %d: %d != %d" % (round_no, len(results), n_threads * per_thread))
            if len(success) > cap:
                fail("CAP EXCEEDED (round %d): %d successes with cap %d — incr_if_below is not atomic"
                     % (round_no, len(success), cap))
            if c.value() != len(success):
                fail("value()=%r disagrees with %d successes (round %d)" % (c.value(), len(success), round_no))
            if success != list(range(1, len(success) + 1)):
                fail("successful calls must return distinct 1..cap values (round %d): duplicates/gaps"
                     % round_no)
            if c.value() > cap:
                fail("count %r exceeds cap %d (round %d)" % (c.value(), cap, round_no))
    finally:
        threading.settrace(None)
        sys.setswitchinterval(0.005)

    print("PASS: g3_hunt_conccounter")


if __name__ == "__main__":
    main()
