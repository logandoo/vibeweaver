"""G-DED artifact assertions — byte-level check of verification claims.
Canonical copy: vibeweaver skill `scripts/assert_artifacts.py`.
Mirrors SKILL.md §A4.4.1 minimum-check table (all 13 groups).

Portions (group 13 claim/coverage machinery) adapted from J-Space Cognition
Suite V3.6 (`j-space/scripts/jspace.py`, ship mode) — Copyright Tiger3807861189,
Apache License 2.0. Modifications by the vibeweaver authors: scoped to
tests/verification_log.md, structured-line exemptions, stdlib-only, reworded
messages. See repo root THIRD_PARTY_NOTICES.md."""
import argparse, os, pathlib, re, subprocess, sys

FAILS = []
PASSES = 0

CLAIM = re.compile(
    r"(?:\b(?:verified|confirmed|validated|tested|proven)\b|"
    r"(?:已经验证|已验证|经验证|验证通过|已经确认|已确认|经确认|确认无误|"
    r"已经测试|已测试|经测试|测试通过|已经证明|已证明|经证明))",
    re.I,
)
COVERAGE = re.compile(
    r"(?:\b(?:all|each|every|cases?|inputs?|samples?|bounds?|boundaries|edges?|"
    r"files?|modules?|sections?|lines?|scenarios?|environments?|platforms?|routes?|"
    r"commands?|branches?|ranges?|including|through|up\s+to|sweep(?:ed)?|coverage)\b|"
    r"\b(?:Windows|Linux|macOS|Chrome|Firefox|Safari)\b|"
    r"\b(?:Python|Node(?:\.js)?)\s*\d|\bn\s*[<≤=]\s*\d|coverage|covered|"
    r"截图|日志|覆盖|全部|所有|每个|每条|逐一|逐条|边界|用例|文件|目录|模块|"
    r"章节|区段|场景|平台|环境|浏览器|数据集|记录|路径|路由|命令|分支|范围|"
    r"包括|包含|至多|至少|最多|最少|随机|样本|样例)",
    re.I,
)
STRUCT_LINE = re.compile(r"^(?:#{1,6}\s|>|\|{1,2}\s*-+|\s*$)")
EXEMPT_LINE = re.compile(r"(?:^- iter \d+ (?:PASS|FAIL):|^- Baseline verified GREEN|^- COV-\d+ skipped)")
FENCE = re.compile(r"^\s{0,3}(?:```|~~~)")


def check(ok: bool, msg: str):
    global PASSES
    PASSES += 1
    if not ok:
        FAILS.append(msg)


def read(p: pathlib.Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return ""


def claim_without_coverage(vl: str):
    """Return violating (line_number, line) pairs: a claim verb on a prose line
    whose own line states no coverage scope. Fenced blocks, headings, tables
    and structured entries are exempt — see EXEMPT_LINE."""
    hits = []
    in_fence = False
    for i, line in enumerate(vl.splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = line.strip()
        if not stripped or STRUCT_LINE.match(stripped) or EXEMPT_LINE.match(stripped):
            continue
        if CLAIM.search(stripped) and not COVERAGE.search(stripped):
            hits.append((i, stripped[:80]))
    return hits


def main():
    global PASSES
    ap = argparse.ArgumentParser()
    ap.add_argument("--existing", action="store_true", help="Modify-Existing task: skip new-project §A5 design-doc + git checks")
    ap.add_argument("--backend-only", action="store_true", help="no UI: skip PAGE_DESIGN.html and project_build.sh checks")
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parent.parent
    tests = root / "tests"
    vl = read(tests / "verification_log.md")
    acc = read(tests / "acceptance.md")

    # 1) verification_log — exists, has >=1 standard iteration entry (COV-1)
    check(vl and len(vl.strip()) > 0, "tests/verification_log.md missing or empty (COV-1)")
    check(bool(re.search(r"^- iter \d+ (PASS|FAIL):", vl, re.M)),
          "verification_log.md has no `- iter N PASS/FAIL:` entries (A4.1 Step 4)")

    # 2) acceptance.md — exists, first line cap/stall stop-condition (COV-7)
    check(bool(re.search(r"^>\s*cap=5\s+stall=3", acc, re.M)),
          "tests/acceptance.md missing first line `> cap=5  stall=3×` (COV-7)")

    # 3) screenshots cited in the log files must exist >0 bytes (A4.4)
    for png in re.findall(r"tests/(\S+\.png)", vl + "\n" + acc):
        p = tests / png
        check(p.exists() and p.stat().st_size > 0,
              f"screenshot claimed but missing/empty: tests/{png} (A4.4)")

    # 4) memory — MEMORY.md + >=1 topic file + index pointers (A7.9/A7.10)
    mem = root / "memory"
    idx_text = read(mem / "MEMORY.md")
    check(bool(idx_text), "memory/MEMORY.md missing (A7.10)")
    if idx_text:
        topics = sorted(mem.glob("*.md"))
        check(len(topics) >= 2, "memory/: MEMORY.md + >=1 topic file required (A7.9)")
        check(bool(re.search(r"\]\([^)]+\.md\)", idx_text)),
              "memory/MEMORY.md index has no topic-file pointers (A7.9)")
        check(any(p.name != "MEMORY.md" for p in topics),
              "memory/: at least one topic file besides MEMORY.md (A7.9)")

    # 5) scripts — start/stop/restart (+ project_build unless --backend-only) (A2/COV-2)
    #    exec-bit is only meaningful on POSIX; on Windows .sh files ride along
    #    and only their existence is enforceable.
    posix = os.name != "nt"
    for s in ["start.sh", "stop.sh", "restart.sh"]:
        sp = root / "script" / "linux" / s
        is_exec = (sp.stat().st_mode & 0o111) if posix else True
        check(sp.exists() and is_exec,
              f"script/linux/{s} missing or not executable (A2/COV-2)")
    if not args.backend_only:
        bp = root / "script" / "linux" / "project_build.sh"
        check(bp.exists(), "script/linux/project_build.sh missing (A2; use --backend-only if no UI)")

    # 6) git — new projects: repo exists with >=2 commits (C1 step 1/15, A9)
    if not args.existing:
        try:
            r = subprocess.run(["git", "-C", str(root), "log", "--oneline"],
                               capture_output=True, text=True, timeout=20)
            rc, out = r.returncode, r.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            rc, out = -1, ""
        n_commits = len([l for l in out.splitlines() if l.strip()]) if rc == 0 else 0
        check(rc == 0 and n_commits >= 2,
              f"new-project git repo needs >=2 commits (init + final); found {n_commits} (C1 step 1/15)")

    # 7) §A5 design docs — new projects (skipped with --existing) (A5 / C1 step 2)
    if not args.existing:
        for doc in ["FLOW_DESIGN.html", "DATABASE_DESIGN.html", "BACKEND_DESIGN.html"]:
            check((root / doc).exists(), f"new-project design doc missing: {doc} (A5 / C1 step 2)")
        if not args.backend_only:
            check((root / "PAGE_DESIGN.html").exists(),
                  "new-project design doc missing: PAGE_DESIGN.html (A5; use --backend-only if no UI)")

    # 8) README + requirements — new projects (skipped with --existing) (C1 step 15)
    if not args.existing:
        check(any((root / n).exists() for n in ["README.md", "README.html"]),
              "new-project README.md/README.html missing (C1 step 15)")
        check(any((root / n).exists() for n in ["requirements.txt", "package.json"]),
              "new-project requirements.txt/package.json missing (C1 step 15)")

    # 9) COV-9 — Modify-Existing tasks: baseline verdict recorded on disk (COV-9)
    if args.existing:
        check(bool(re.search(r"Baseline verified GREEN|COV-9 skipped", vl, re.M)),
              "tests/verification_log.md missing `- Baseline verified GREEN` or `- COV-9 skipped —` entry (COV-9)")

    # 10) A4.7b — workflow traces cited in the log must exist >0 bytes (A4.7b)
    for wf in re.findall(r"tests/workflows/(\S+?\.trace\.log)", vl):
        p = tests / "workflows" / wf
        check(p.exists() and p.stat().st_size > 0,
              f"workflow trace claimed but missing/empty: tests/workflows/{wf} (A4.7b)")

    # 11) A4.1 — video/audio evidence cited in the log must exist >0 bytes (A4.1 Step 2/3)
    for m in re.findall(r"tests/(\S+\.(?:webm|wav|mp4|mp3))", vl):
        p = tests / m
        check(p.exists() and p.stat().st_size > 0,
              f"media evidence claimed but missing/empty: tests/{m} (A4.1)")

    # 12) FAIL diagnosis clause — every failed iteration must carry its diagnosis
    #     (A4.1 Step 4 — a retry without its diagnosis is the same attempt again)
    for i, line in enumerate(vl.splitlines(), 1):
        if re.match(r"^- iter \d+ FAIL:", line.strip()):
            check("diagnosis:" in line,
                  f"verification_log.md line {i}: FAIL entry lacks `diagnosis:` clause (A4.1 Step 4)")

    # 13) claim-without-coverage — a verification claim must state what it covered
    #     (A4.4 Gate Function — "verified" without a stated scope is not a result)
    for i, snippet in claim_without_coverage(vl):
        check(False,
              f"verification_log.md line {i}: claim without stated coverage — {snippet!r} (A4.4 claim rule)")

    if FAILS:
        print("ASSERT FAILURES (%d):" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        sys.exit(1)
    print(f"assert_artifacts.py: all {PASSES} checks pass (exit 0)")


if __name__ == "__main__":
    main()
