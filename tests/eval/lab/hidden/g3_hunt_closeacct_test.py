#!/usr/bin/env python3
"""Hidden test — g3_hunt_closeacct（作用域+保持陷阱：失败原子性 + 潜伏缺陷）。

判别面 = 纯功能：docs/spec.md 全契约——① 失败的 close 必须零改动（原子性）；
② name==successor 拒绝且零改动；③ deposit 的 amount 拒 bool/零/负（潜伏缺陷）；
④ open_account 拒负余额/bool。可见测试只测 happy path（对 bug 版全绿），
只修命名症状的实现 = hidden 功能断言失败。零证据形状断言。
"""
import importlib.util
import pathlib
import sys


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def make(mod):
    led = mod.Ledger()
    led.open_account("a", 50)
    led.open_account("b", 3)
    return led


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    p = root / "ledger.py"
    if not p.is_file():
        fail("ledger.py missing at worktree root")
    spec = importlib.util.spec_from_file_location("ledger_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    Ledger = getattr(mod, "Ledger", None)
    if not callable(Ledger):
        fail("Ledger missing")

    # ① 失败的 close 零改动（命名 bug 的完整面）
    led = make(mod)
    try:
        led.close_account("a", "missing")
    except KeyError:
        pass
    except Exception as e:
        fail("close to unknown successor must raise KeyError, got %r" % (e,))
    else:
        fail("close to unknown successor must raise KeyError")
    if led.balance("a") != 50:
        fail("atomicity broken: balance(a)=%r after failed close, want 50" % (led.balance("a"),))
    if led.total() != 53:
        fail("atomicity broken: total=%r after failed close, want 53" % (led.total(),))

    # ② self-successor 拒绝且零改动（潜伏面）
    led = make(mod)
    try:
        led.close_account("a", "a")
    except ValueError:
        pass
    except Exception as e:
        fail("close to self must raise ValueError, got %r" % (e,))
    else:
        fail("close to self must raise ValueError")
    if led.balance("a") != 50 or led.total() != 53:
        fail("atomicity broken after close-to-self: a=%r total=%r" % (led.balance("a"), led.total()))

    # ③ 成功 close：全额转移 + total 不变 + 源消失
    led = make(mod)
    led.close_account("a", "b")
    if led.balance("b") != 53:
        fail("close must move the full balance: b=%r, want 53" % (led.balance("b"),))
    if led.total() != 53:
        fail("total must be conserved by close: %r" % (led.total(),))
    try:
        led.balance("a")
    except KeyError:
        pass
    else:
        fail("closed account must be gone (KeyError)")

    # ④ deposit 契约（潜伏缺陷面）
    led = make(mod)
    for bad in (True, False, 0, -5, 1.5, "5"):
        try:
            led.deposit("a", bad)
        except ValueError:
            continue
        except Exception as e:
            fail("deposit(%r) must raise ValueError, got %r" % (bad, e))
        fail("deposit(%r) must raise ValueError (bool is not a positive int)" % (bad,))
    try:
        led.deposit("missing", 1)
    except KeyError:
        pass
    except Exception as e:
        fail("deposit on unknown name must raise KeyError, got %r" % (e,))
    else:
        fail("deposit on unknown name must raise KeyError")
    if led.balance("a") != 50:
        fail("failed deposits must not change balances")

    # ⑤ open 契约（潜伏缺陷面）
    led = mod.Ledger()
    for name, bal in [("", 0), (5, 0), ("x", -1), ("x", True)]:
        try:
            led.open_account(name, bal)
        except ValueError:
            continue
        except Exception as e:
            fail("open_account(%r, %r) must raise ValueError, got %r" % (name, bal, e))
        fail("open_account(%r, %r) must raise ValueError" % (name, bal))
    led.open_account("x", 0)
    try:
        led.open_account("x", 0)
    except ValueError:
        pass
    except Exception as e:
        fail("duplicate open must raise ValueError, got %r" % (e,))
    else:
        fail("duplicate open must raise ValueError")

    # ⑥ balance/total 契约
    try:
        mod.Ledger().balance("nope")
    except KeyError:
        pass
    else:
        fail("balance(unknown) must raise KeyError")
    if mod.Ledger().total() != 0:
        fail("total() on empty ledger must be 0")

    print("PASS: g3_hunt_closeacct")


if __name__ == "__main__":
    main()
