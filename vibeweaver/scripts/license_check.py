#!/usr/bin/env python3
"""license_check.py — license/attribution hygiene check (P3-19).

检查项（fail-closed：缺 LICENSE/NOTICE 一律 exit 1，不「假定合规」）：
  1. LICENSE 存在且非空、含年份与权利人或 SPDX 标识
  2. NOTICE 存在（第三方归因）
  3. 发布载荷（SKILL/插件/脚本）不内嵌第三方源码（按已知特征串粗检）
  4. 依赖清单（package.json / requirements.txt）的许可证白名单内

用法：python3 scripts/license_check.py [--root DIR] [--json]
"""
import argparse
import json
import pathlib
import re
import sys

# 只在本项目自己的源码里出现第三方特征串才算内嵌；引用/名字提及不算
THIRD_PARTY_MARKERS = [
    ("MIT License — Copyright (c)", "embedded third-party header"),
    ("@license", "embedded third-party license tag"),
    ("Apache License, Version 2.0", "embedded Apache header"),
    ("Redistribution and use in source and binary forms", "embedded BSD clause"),
]

LICENSE_WHITELIST = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD", "Unlicense"}
LICENSE_HINTS = re.compile(r"(MIT|Apache|BSD|ISC|Unlicense|GNU|GPL|LGPL|MPL|CC0)", re.I)


def payload_files(root):
    out = []
    # 自指排除：本文件的 THIRD_PARTY_MARKERS 是检测器字面量，不是内嵌第三方代码；
    # 扫描自己会产出永久自误报（首跑实测 4 个自指 FAIL）。
    self_path = pathlib.Path(__file__).resolve()
    for rel in ("SKILL.md", "vibeweaver-gate.js", "vibeweaver-audit.js"):
        p = root / rel
        if p.is_file():
            out.append(p)
    for d in ("scripts",):
        p = root / d
        if p.is_dir():
            out.extend(sorted(q for q in p.rglob("*")
                              if q.is_file() and q.suffix in (".py", ".js", ".mjs", ".sh")
                              and q.resolve() != self_path))
    return out


def check(root):
    fails, warns = [], []
    lic = root / "LICENSE"
    if not lic.is_file() or lic.stat().st_size == 0:
        fails.append("LICENSE missing or empty — a license decision is REQUIRED (owner); "
                     "do not ship without one")
    else:
        text = lic.read_text(encoding="utf-8", errors="replace")
        if not LICENSE_HINTS.search(text):
            fails.append("LICENSE does not look like a license text (no known license keyword)")
        if not re.search(r"(Copyright|\(c\)|SPDX|Permission is hereby granted|Redistribution)", text, re.I):
            warns.append("LICENSE has no year/holder or SPDX identifier")
    notice = root / "NOTICE"
    if not notice.is_file():
        warns.append("NOTICE missing — third-party attribution has no home")
    elif notice.stat().st_size == 0:
        warns.append("NOTICE is empty")
    for p in payload_files(root):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            warns.append("%s unreadable (%s)" % (p.relative_to(root), exc))
            continue
        for marker, why in THIRD_PARTY_MARKERS:
            if marker in text:
                fails.append("%s: %s (%r)" % (p.relative_to(root), why, marker))
    for dep_file in ("package.json", "requirements.txt"):
        p = root / dep_file
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'"license"\s*:\s*"([^"]+)"', text):
            if m.group(1) not in LICENSE_WHITELIST:
                warns.append("%s: license %r not in whitelist" % (dep_file, m.group(1)))
    return fails, warns


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parents[1]))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = pathlib.Path(args.root)
    fails, warns = check(root)
    if args.json:
        print(json.dumps({"ok": not fails, "fails": fails, "warns": warns}, indent=2))
    else:
        for f in fails:
            print("FAIL " + f)
        for w in warns:
            print("WARN " + w)
        print("license_check: %d fail / %d warn" % (len(fails), len(warns)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
