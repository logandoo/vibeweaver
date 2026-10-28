import pathlib, sys
root = pathlib.Path(sys.argv[1])
p = root / "hello.txt"
if not p.is_file():
    print("FAIL: hello.txt missing"); sys.exit(1)
text = p.read_text(encoding="utf-8")
if text != "hello\n":
    print("FAIL: content=%r" % text); sys.exit(1)
print("PASS: hello.txt")
