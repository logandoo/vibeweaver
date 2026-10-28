#!/usr/bin/env python3
"""Hidden test — g3_teeth_stateleak（只测功能：别名/变异契约）。

判别点：normalize 的 docstring 明文「NEW list of NEW dicts / input must NOT be
modified / rows without name skipped」。经典模型失败面：修了输出形状却仍在
原地变异输入、或复制了字典却漏了缺 name 行的跳过。评分只看行为与对象身份。
"""
import importlib.util
import pathlib
import sys


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    p = root / "normalize.py"
    if not p.is_file():
        fail("normalize.py missing at worktree root")
    spec = importlib.util.spec_from_file_location("normalize_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        fail("normalize.py does not import: %r" % (e,))
    normalize = getattr(mod, "normalize", None)
    if not callable(normalize):
        fail("normalize() missing or not callable")

    rows = [{"name": "  ALICE ", "score": "3"}, {"name": "bob", "score": "7"},
            {"score": 1}]
    snapshot = [dict(r) for r in rows]
    got = normalize(rows)

    if rows != snapshot:
        fail("input rows were modified (docstring: input must NOT be modified)")
    if not isinstance(got, list) or len(got) != 2:
        fail("result must be a list with the nameless row skipped, got %r" % (got,))
    if any(g is r for g in got for r in rows):
        fail("result dicts alias input dicts (docstring: NEW dicts)")
    if got[0] != {"name": "alice", "score": 3}:
        fail("got[0] must be {'name': 'alice', 'score': 3} (strip+lower+int), got %r" % (got[0],))
    if got[1] != {"name": "bob", "score": 7}:
        fail("got[1] must be {'name': 'bob', 'score': 7}, got %r" % (got[1],))
    if normalize([]) != []:
        fail("normalize([]) must be []")
    print("PASS: g3_teeth_stateleak")


if __name__ == "__main__":
    main()
