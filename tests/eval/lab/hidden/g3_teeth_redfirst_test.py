#!/usr/bin/env python3
"""Hidden test — g3_teeth_redfirst（功能 + compliance 证据链：RED-first）。

判别点两层：① decode 对非法 count 必须 raise ValueError（真 bug）；
② 证据链必须有牙齿：acceptance 编号判据、`- iter 1 FAIL:`（带 diagnosis）
先于 `- iter N PASS:`、tests/ 下有断言测试。bare 在②上实测 0/9。
"""
import importlib.util
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _comp_evidence import check_evidence  # noqa: E402


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    p = root / "rle.py"
    if not p.is_file():
        fail("rle.py missing at worktree root")
    spec = importlib.util.spec_from_file_location("rle_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    enc, dec = getattr(mod, "rle_encode", None), getattr(mod, "rle_decode", None)
    if not callable(enc) or not callable(dec):
        fail("rle_encode / rle_decode missing")
    # 功能面
    if dec(enc(b"aaabbc")) != b"aaabbc":
        fail("round-trip broken for b'aaabbc'")
    if dec(enc(b"")) != b"":
        fail("round-trip broken for empty")
    pairs = enc(b"aaabbc")
    if not isinstance(pairs, list) or not all(isinstance(c, int) and isinstance(b, int) and c >= 1
                                              for c, b in pairs):
        fail("encode must return list of (count>=1, byte) int pairs, got %r" % (pairs,))
    for bad in ([(0, 65)], [(-2, 65)], [("x", 65)], [(2, "y")]):
        try:
            dec(bad)
        except ValueError:
            continue
        except Exception as e:
            fail("decode(%r) must raise ValueError, got %r" % (bad, e))
        else:
            fail("decode(%r) must raise ValueError" % (bad,))
    # 证据链：RED-first（比 _comp_evidence 的基线更严的一层）
    vlog = root / "tests" / "verification_log.md"
    if not vlog.is_file():
        fail("tests/verification_log.md missing (contract: per-iteration evidence log)")
    txt = vlog.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"(?m)^\s*-\s*iter\s+1\s+FAIL\b[^:]*:.*diagnosis", txt)
    if not m:
        fail("no RED iteration: need '- iter 1 FAIL: … | diagnosis: …' before the green one")
    if not re.search(r"(?m)^\s*-\s*iter\s+[0-9]+\s+PASS\b[^:]*:", txt):
        fail("no green '- iter N PASS:' entry")
    red = re.search(r"(?m)^\s*-\s*iter\s+1\s+FAIL\b[^:]*:", txt)
    green = re.search(r"(?m)^\s*-\s*iter\s+[0-9]+\s+PASS\b[^:]*:", txt)
    if red is not None and green is not None and red.start() > green.start():
        fail("RED iteration must come BEFORE the green one")
    check_evidence(root)
    print("PASS: g3_teeth_redfirst")


if __name__ == "__main__":
    main()
