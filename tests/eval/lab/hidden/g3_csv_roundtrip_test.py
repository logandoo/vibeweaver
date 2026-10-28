#!/usr/bin/env python3
"""Hidden test — g3_csv_roundtrip (graded at scoring time; not in the worktree)."""
import importlib.util
import pathlib
import sys


def load(root):
    p = pathlib.Path(root) / "csv_roundtrip.py"
    if not p.is_file():
        print("FAIL: csv_roundtrip.py missing")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("csv_roundtrip", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    m = load(sys.argv[1] if len(sys.argv) > 1 else ".")
    dump, load_ = getattr(m, "dump", None), getattr(m, "load", None)
    if not callable(dump) or not callable(load_):
        fail("dump/load missing")

    if dump([["a,b"]]) != '"a,b"\r\n':
        fail("a field with a comma must be quoted: %r" % dump([["a,b"]]))
    if dump([["a", "b"]]) != "a,b\r\n":
        fail("plain fields must stay unquoted: %r" % dump([["a", "b"]]))
    if dump([['he said "hi"']]) != '"he said ""hi"""\r\n':
        fail("embedded quotes must be doubled and quoted: %r" % dump([['he said "hi"']]))
    if dump([["a"]]) != "a\r\n":
        fail("rows must end with CRLF: %r" % dump([["a"]]))

    table = [["a,b", "c"], ['quote " inside', "multi\nline"], [""], ["", ""], ["tail"]]
    try:
        text = dump(table)
    except Exception as exc:
        fail("dump raised %r" % exc)
    try:
        back = load_(text)
    except Exception as exc:
        fail("load raised %r" % exc)
    if back != table:
        fail("round-trip broken:\n in=%r\n out=%r\ntext=%r" % (table, back, text))

    for bad in ('"unterminated', 'a,"b\r\n'):
        try:
            load_(bad)
        except ValueError:
            continue
        fail("load(%r) must raise ValueError" % (bad,))

    for bad in ([[1, 2]], ["not a row"], [[None]]):
        try:
            dump(bad)
        except ValueError:
            continue
        fail("dump(%r) must raise ValueError" % (bad,))
    print("PASS: g3_csv_roundtrip")


if __name__ == "__main__":
    main()
