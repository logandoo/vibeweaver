#!/usr/bin/env python3
"""evidence_lock.py — bind the task contract before evidence can be forged.

Threat (PLAN W0 Task 2.5): a checker pin stops a fake checker, but the agent
can still rewrite the rules:
  - loosen tests/acceptance.md mid-task
  - delete a FAIL line from tests/verification_log.md
  - edit tests/project_profile.json to skip groups
  - edit tests/debt_baseline.json to wash debt
  - cite a 1-byte fake PNG as a screenshot

This tool writes tests/.evidence.lock (the only writer) and verifies:
  acceptance: sha256 of the CURRENT task section (last `##` heading -> EOF)
  profile/debt: file sha256 when present at lock time
  log: prefix hash + per-line chain (append-only; legacy logs get a baseline)
  media: magic bytes + non-trivial size for every cited tests/*.{png,webm,...}

Usage:
  python3 scripts/evidence_lock.py --init
  python3 scripts/evidence_lock.py --check [--final]
  python3 scripts/evidence_lock.py --seal-log
  python3 scripts/evidence_lock.py --update-acceptance --reason "..." --approved
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

LOCK_REL = "tests/.evidence.lock"
MEDIA_RE = re.compile(r"tests/([^\s`'\"()]+\.(?:png|jpe?g|webm|wav|mp4|mp3))", re.I)
MAGIC = {
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".webm": b"\x1aE\xdf\xa3",
    ".wav": b"RIFF",
    ".mp4": b"ftyp",
    ".mp3": b"ID3",
}


def norm_section(text):
    return (text.rstrip() + "\n") if text.strip() else ""


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    try:
        return sha_bytes(pathlib.Path(p).read_bytes())
    except OSError:
        return ""


def section(text):
    """Return (heading, section_text, start_line) for the last `## ` section."""
    lines = text.splitlines(keepends=True)
    idx = 0
    for i, line in enumerate(lines):
        if re.match(r"^#{1,2} ", line):
            idx = i
    head = lines[idx].rstrip("\r\n") if lines and re.match(r"^#{1,2} ", lines[idx]) else ""
    return head, "".join(lines[idx:]), idx


def section_slice(text, heading):
    """Slice from `heading` to the next heading (any level) or EOF."""
    lines = text.splitlines(keepends=True)
    out = []
    started = False
    for line in lines:
        if not started:
            if line.rstrip("\r\n") == heading.rstrip("\r\n"):
                started = True
                out.append(line)
            continue
        if re.match(r"^#{1,2} ", line):
            break
        out.append(line)
    return "".join(out)


def read_text(p):
    try:
        return pathlib.Path(p).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _lock_path(root):
    return pathlib.Path(root) / LOCK_REL


def _write_lock(root, data):
    p = _lock_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".lock.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(p)


def _line_hashes(text):
    return [sha_bytes(line.encode("utf-8")) for line in text.splitlines()]


def build_lock(root, previous=None):
    root = pathlib.Path(root)
    acc = read_text(root / "tests" / "acceptance.md")
    heading, sec, start = section(acc)
    log_text = read_text(root / "tests" / "verification_log.md")
    log_lines = _line_hashes(log_text)
    prev = previous or {}
    baseline_lines = int(prev.get("log", {}).get("baseline_lines", 0))
    baseline_sha = prev.get("log", {}).get("baseline_sha256", "")
    chain = list(prev.get("log", {}).get("chain", []))
    if not baseline_sha:
        # First lock: the existing log is the legacy baseline. Only entries
        # after it are chain-verified (Task 2.5 step 5).
        baseline_lines = len(log_lines)
        baseline_sha = sha_bytes("\n".join(log_text.splitlines()[:baseline_lines]).encode("utf-8"))
        chain = []
    lock = {
        "version": 1,
        "acceptance": {
            "heading": heading,
            "start_line": start,
            "sha256": sha_bytes(norm_section(sec).encode("utf-8")),
            "bytes": len(norm_section(sec).encode("utf-8")),
        },
        "profile": {"sha256": sha_file(root / "tests" / "project_profile.json") or None},
        "debt": {"sha256": sha_file(root / "tests" / "debt_baseline.json") or None},
        "log": {
            "baseline_lines": baseline_lines,
            "baseline_sha256": baseline_sha,
            "head_lines": len(log_lines),
            "head_sha256": log_lines[-1] if log_lines else "",
            "chain": chain,
            "mode": "legacy" if not chain else "chain",
        },
    }
    if previous and isinstance(previous.get("history"), list):
        lock["history"] = previous["history"]
    return lock


def init(root, force=False, approved=False):
    p = _lock_path(root)
    if p.exists() and not force:
        print("EVIDENCE-LOCK FAIL: %s already exists (use --update-acceptance/--seal-log)" % p, file=sys.stderr)
        return 1
    if force and not approved:
        print("EVIDENCE-LOCK FAIL: --force requires --approved (Class-E; re-baselining rewrites the anchor)", file=sys.stderr)
        return 1
    prev = None
    if p.exists():
        try:
            prev = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            prev = None
    _write_lock(root, build_lock(root, prev))
    print("EVIDENCE-LOCK OK: initialized %s" % p)
    return 0


def check_media(root, text):
    errors = []
    seen = set()
    for m in MEDIA_RE.finditer(text):
        rel = "tests/" + m.group(1)
        if rel in seen:
            continue
        seen.add(rel)
        p = pathlib.Path(root) / rel
        if not p.is_file():
            errors.append("cited media missing: %s" % rel)
            continue
        try:
            data = p.read_bytes()
        except OSError as e:
            errors.append("cited media unreadable: %s (%s)" % (rel, e))
            continue
        if len(data) < 8:
            errors.append("cited media too small (%d bytes): %s" % (len(data), rel))
            continue
        ext = p.suffix.lower()
        magic = MAGIC.get(ext)
        if ext == ".wav":
            ok = data[:4] == b"RIFF" and data[8:12] == b"WAVE"
        elif ext == ".mp4":
            ok = b"ftyp" in data[:64]
        elif magic:
            ok = data.startswith(magic)
        else:
            ok = True
        if not ok:
            errors.append("cited media magic mismatch: %s (%s)" % (rel, ext))
    return errors


def verify(root, final=False, rebase_new_task=False):
    root = pathlib.Path(root)
    p = _lock_path(root)
    if not p.exists():
        return ["evidence lock missing: %s (run --init)" % p]
    try:
        lock = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        return ["evidence lock unparseable: %s" % e]

    errors = []
    log_text = read_text(root / "tests" / "verification_log.md")
    # --- acceptance section -------------------------------------------------
    acc_text = read_text(root / "tests" / "acceptance.md")
    heading, sec, start = section(acc_text)
    locked = lock.get("acceptance", {})
    cur_sha = sha_bytes(norm_section(sec).encode("utf-8"))
    if heading == locked.get("heading") and cur_sha != locked.get("sha256"):
        errors.append(
            "acceptance section changed after lock (sha256 %s != %s) — "
            "changes require `--update-acceptance --reason <why> --approved`"
            % (cur_sha[:12], str(locked.get("sha256"))[:12])
        )
    elif heading != locked.get("heading"):
        locked_heading = str(locked.get("heading") or "")
        old = section_slice(acc_text, locked_heading) if locked_heading else ""
        old_sha = sha_bytes(norm_section(old).encode("utf-8")) if old else ""
        if locked_heading and locked_heading in acc_text and old_sha == locked.get("sha256"):
            _final_m = re.search(r"(?m)^- final-run:\s*--final\s*[—-]\s*pass=\d+/fail=0", log_text)
            _sealed_lines = int(lock.get("log", {}).get("baseline_lines", 0)) + len(lock.get("log", {}).get("chain", []) or [])
            _final_line = (log_text[:_final_m.start()].count("\n") + 1) if _final_m else 0
            log_has_final = bool(_final_m) and _final_line <= _sealed_lines
            if rebase_new_task and log_has_final:
                data = build_lock(root, lock)
                _write_lock(root, data)
                lock = data
            elif rebase_new_task:
                errors.append(
                    "new task section detected while the current task has no `- final-run: --final … pass=N/fail=0` — "
                    "refusing auto-rebase (it would be an escape hatch); finish the task or use --update-acceptance --approved")
            else:
                errors.append("new task section detected (%r) — finish the current task then re-run, or --update-acceptance --approved" % heading)
        else:
            errors.append("acceptance task section heading changed and the locked section was not preserved")

    # --- profile / debt -----------------------------------------------------
    for key, rel in (("profile", "tests/project_profile.json"), ("debt", "tests/debt_baseline.json")):
        want = (lock.get(key) or {}).get("sha256")
        if not want:
            continue
        got = sha_file(root / rel)
        if got != want:
            errors.append("%s changed after lock (sha256 %s != %s)" % (rel, got[:12] or "(missing)", want[:12]))

    # --- append-only log ----------------------------------------------------
    log_text = read_text(root / "tests" / "verification_log.md")
    lines = log_text.splitlines()
    hashes = _line_hashes(log_text)
    lg = lock.get("log", {})
    base_n = int(lg.get("baseline_lines", 0))
    base_sha = str(lg.get("baseline_sha256", ""))
    if base_sha:
        prefix = hashes[:base_n]
        if len(prefix) < base_n:
            errors.append("verification_log.md truncated below the locked baseline (%d < %d lines)" % (len(prefix), base_n))
        elif sha_bytes("\n".join(lines[:base_n]).encode("utf-8")) != base_sha:
            errors.append("verification_log.md baseline prefix changed (deleted/rewritten lines)")
    chain = lg.get("chain", []) or []
    prev = base_sha
    for e in chain:
        i = int(e.get("i", 0))
        if e.get("prev") != prev:
            errors.append("verification_log.md chain break at line %d (prev hash mismatch)" % i)
        if i < 1 or i > len(hashes):
            errors.append("verification_log.md chain line %d missing (log truncated)" % i)
        elif hashes[i - 1] != e.get("sha256"):
            errors.append("verification_log.md line %d changed after seal" % i)
        prev = e.get("sha256", "")
    if final and len(hashes) > base_n + len(chain):
        errors.append(
            "verification_log.md has %d unsealed line(s) after the last seal — run `--seal-log`"
            % (len(hashes) - base_n - len(chain))
        )

    # --- cited media --------------------------------------------------------
    errors.extend(check_media(root, acc_text + "\n" + log_text))
    return errors


def seal_log(root):
    p = _lock_path(root)
    if not p.exists():
        return ["evidence lock missing: %s (run --init)" % p]
    lock = json.loads(p.read_text(encoding="utf-8"))
    log_text = read_text(pathlib.Path(root) / "tests" / "verification_log.md")
    lines = log_text.splitlines()
    hashes = _line_hashes(log_text)
    lg = lock.setdefault("log", {})
    base_n = int(lg.get("baseline_lines", 0))
    base_sha = str(lg.get("baseline_sha256", ""))
    if not base_sha:
        base_n = len(lines)
        base_sha = sha_bytes("\n".join(lines[:base_n]).encode("utf-8"))
        lg["baseline_lines"] = base_n
        lg["baseline_sha256"] = base_sha
    if sha_bytes("\n".join(lines[:base_n]).encode("utf-8")) != base_sha:
        return ["verification_log.md baseline prefix changed — refusing to seal"]
    chain = lg.setdefault("chain", [])
    prev = chain[-1]["sha256"] if chain else base_sha
    added = 0
    for i in range(base_n + len(chain) + 1, len(hashes) + 1):
        e = {"i": i, "sha256": hashes[i - 1], "prev": prev}
        chain.append(e)
        prev = hashes[i - 1]
        added += 1
    if chain:
        lg["mode"] = "chain"
    lg["head_lines"] = len(lines)
    lg["head_sha256"] = hashes[-1] if hashes else ""
    _write_lock(root, lock)
    print("EVIDENCE-LOCK OK: sealed %d new line(s) (%d chained)" % (added, len(chain)))
    return []


def update_acceptance(root, reason, approved):
    if not reason or len(reason.strip()) < 10:
        return ["--update-acceptance requires --reason with >=10 non-space characters"]
    if not approved and os_environ_approved() != "1":
        return ["--update-acceptance requires explicit approval (--approved or VIBEWEAVER_ACCEPTANCE_APPROVED=1; Class-E)"]
    p = _lock_path(root)
    if not p.exists():
        return ["evidence lock missing: %s (run --init)" % p]
    lock = json.loads(p.read_text(encoding="utf-8"))
    acc = read_text(pathlib.Path(root) / "tests" / "acceptance.md")
    heading, sec, start = section(acc)
    lock["acceptance"] = {
        "heading": heading,
        "start_line": start,
        "sha256": sha_bytes(norm_section(sec).encode("utf-8")),
        "bytes": len(norm_section(sec).encode("utf-8")),
    }
    lock.setdefault("history", []).append({
        "at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "reason": reason.strip(),
        "approved": True,
        "sha256": lock["acceptance"]["sha256"],
    })
    _write_lock(root, lock)
    print("EVIDENCE-LOCK OK: acceptance update recorded (%s)" % reason.strip()[:60])
    return []


def os_environ_approved():
    import os
    return os.environ.get("VIBEWEAVER_ACCEPTANCE_APPROVED", "")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Task evidence lock")
    ap.add_argument("--root", default=".")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--init", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--seal-log", action="store_true")
    g.add_argument("--update-acceptance", action="store_true")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--rebase-new-task", action="store_true")
    ap.add_argument("--reason", default="")
    ap.add_argument("--approved", action="store_true", help="Class-E approval for re-baseline/acceptance changes")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = pathlib.Path(args.root).resolve()

    if args.init:
        return init(root, args.force, args.approved)
    if args.update_acceptance:
        errs = update_acceptance(root, args.reason, args.approved)
    elif args.seal_log:
        errs = seal_log(root)
    else:
        errs = verify(root, final=args.final, rebase_new_task=args.rebase_new_task)

    if args.json:
        print(json.dumps({"ok": not errs, "errors": errs}, indent=2))
    elif errs:
        print("EVIDENCE-LOCK FAIL (%d):" % len(errs), file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
    else:
        print("EVIDENCE-LOCK OK")
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
