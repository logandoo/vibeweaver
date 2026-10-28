#!/usr/bin/env python3
"""Hidden test — g3_teeth_redfirst_ttl（功能（TTL 边界 >=）+ RED-first 证据链）。"""
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
    p = root / "ttlcache.py"
    if not p.is_file():
        fail("ttlcache.py missing at worktree root")
    spec = importlib.util.spec_from_file_location("ttl_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cls = getattr(mod, "TTLCache", None)
    if cls is None:
        fail("TTLCache missing")
    c = cls(10)
    c.put("k", "v", now=0)
    if c.get("k", now=5) != "v":
        fail("fresh value must be returned")
    if c.get("k", now=10) is not None:
        fail("expired at now - t == ttl (contract: >= ttl means expired)")
    if c.get("k", now=11) is not None:
        fail("expired after ttl must be None")
    if c.get("missing", now=0) is not None:
        fail("absent key must be None")
    c2 = cls(0)
    c2.put("x", 1, now=7)
    if c2.get("x", now=7) is not None:
        fail("ttl=0 expires immediately (now - t >= 0)")
    vlog = root / "tests" / "verification_log.md"
    if not vlog.is_file():
        fail("tests/verification_log.md missing (contract: per-iteration evidence log)")
    txt = vlog.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"(?m)^\s*-\s*iter\s+1\s+FAIL\b[^:]*:.*diagnosis", txt):
        fail("no RED iteration: need '- iter 1 FAIL: \u2026 | diagnosis: \u2026' before the green one")
    if not re.search(r"(?m)^\s*-\s*iter\s+[0-9]+\s+PASS\b[^:]*:", txt):
        fail("no green '- iter N PASS:' entry")
    red = re.search(r"(?m)^\s*-\s*iter\s+1\s+FAIL\b[^:]*:", txt)
    green = re.search(r"(?m)^\s*-\s*iter\s+[0-9]+\s+PASS\b[^:]*:", txt)
    if red is not None and green is not None and red.start() > green.start():
        fail("RED iteration must come BEFORE the green one")
    check_evidence(root)
    print("PASS: g3_teeth_redfirst_ttl")


if __name__ == "__main__":
    main()
