#!/usr/bin/env python3
"""install.py — single implementation of the vibeweaver installer lifecycle.

W1 Task 5.5: install / dry-run / check / upgrade(backup) / rollback / uninstall.
The shell and batch installers are thin wrappers around this file. The
`.installed.json` manifest is the only record of ownership; uninstall removes
exactly those files and never touches `memory/` or user projects.
"""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

SOURCE = pathlib.Path(__file__).resolve().parent.parent
SKILL_NAME = "vibeweaver"
TOP_FILES = [
    "SKILL.md", "COMPLETION_GATE.md", "AUDIT_PLUGIN.md", "CODING_PRINCIPLES.md",
    "ENGINEERING_STD.md", "REFERENCE.md", "APPENDIX.md",
    "MEMORY_TEMPLATES.md", "MEMORY_RULES.md", "TESTING_PROTOCOLS.md",
    "WORKFLOWS_EXTENDED.md", "VERIFICATION_UPGRADES.md", "bootstrap.md",
    "install.sh", "install.bat",
]
CORE_COMPANIONS = [
    "TESTING_PROTOCOLS.md", "COMPLETION_GATE.md", "AUDIT_PLUGIN.md", "VERIFICATION_UPGRADES.md",
    "MEMORY_RULES.md", "WORKFLOWS_EXTENDED.md", "APPENDIX.md",
]
PLUGINS = ["vibeweaver-gate.js", "vibeweaver-audit.js"]
SCRIPT_EXCLUDE = {"install.py", "__pycache__"}
MANIFEST_NAME = ".installed.json"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def skill_dir():
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = pathlib.Path(xdg) if xdg else pathlib.Path(os.environ.get("HOME", "~")).expanduser() / ".config"
    return base / "opencode" / "skills" / SKILL_NAME


def plugins_dir():
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = pathlib.Path(xdg) if xdg else pathlib.Path(os.environ.get("HOME", "~")).expanduser() / ".config"
    return base / "opencode" / "plugins"


def payload(profile):
    """[(source, relative destination)] under the skill dir."""
    out = []
    if profile in ("full", "all"):
        for rel in TOP_FILES:
            p = SOURCE / rel
            if p.is_file():
                out.append((p, rel))
    elif profile == "core":
        core = SOURCE / "profiles" / "core" / "SKILL.md"
        if not core.is_file():
            raise SystemExit(f"install.py: profile core not built yet ({core})")
        out.append((core, "SKILL.md"))
        for rel in CORE_COMPANIONS:
            p = SOURCE / rel
            if p.is_file():
                out.append((p, rel))
        out.append((SOURCE / "bootstrap.md", "bootstrap.md"))
    elif profile == "mini":
        raise SystemExit("install.py: --profile mini delegates to vibeweaver-mini/install.sh")
    else:
        raise SystemExit(f"install.py: unknown profile {profile!r}")

    scripts = SOURCE / "scripts"
    if scripts.is_dir():
        for p in sorted(scripts.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(scripts).as_posix()
            if any(part in SCRIPT_EXCLUDE for part in rel.split("/")):
                continue
            out.append((p, "scripts/" + rel))
    return out


def read_manifest(target):
    p = target / MANIFEST_NAME
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def atomic_copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    shutil.copyfile(src, tmp)
    tmp.replace(dst)


def backup(target, manifest):
    """Copy owned files (never memory/) to a timestamped sibling."""
    if not target.exists():
        return None
    bdir = target.parent / (target.name + ".bak." + time.strftime("%Y%m%d%H%M%S"))
    bdir.mkdir(parents=True, exist_ok=True)
    files = (manifest or {}).get("files", [])
    if files:
        for entry in files:
            rel = entry["path"]
            src = target / rel
            if src.is_file():
                atomic_copy(src, bdir / rel)
    else:
        # Unmanaged pre-existing tree: --force may overwrite it. Snapshot every
        # non-memory file so the printed "backup" promise is true.
        for src in sorted(target.rglob("*")):
            if not src.is_file():
                continue
            rel = src.relative_to(target).as_posix()
            if rel.startswith("memory/"):
                continue
            atomic_copy(src, bdir / rel)
    if (target / MANIFEST_NAME).is_file():
        atomic_copy(target / MANIFEST_NAME, bdir / MANIFEST_NAME)
    return bdir


def verify_bundle():
    manifest = SOURCE / "release" / "MANIFEST.json"
    if not manifest.is_file():
        manifest = SOURCE.parent / "release" / "MANIFEST.json"
    verifier = SOURCE / "scripts" / "verify_release.py"
    if not manifest.is_file() or not verifier.is_file():
        print("[WARN] release manifest not found — development install (unverified)", file=sys.stderr)
        return True
    root = SOURCE if (SOURCE / "release" / "MANIFEST.json") == manifest else SOURCE.parent
    r = subprocess.run([sys.executable, str(verifier), "--root", str(root),
                        "--manifest", str(manifest)], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        return False
    print("[OK] bundle verified")
    return True


def cmd_install(args):
    profile = args.profile
    target = skill_dir()
    plan = payload(profile)
    if not verify_bundle() and not args.no_verify:
        return 1
    old = read_manifest(target)
    managed = {e["path"] for e in (old or {}).get("files", [])}
    conflicts = []
    for _src, rel in plan:
        dst = target / rel
        if dst.is_file() and rel not in managed:
            conflicts.append(rel)
    if conflicts and not args.force:
        print("install.py: refusing to overwrite unmanaged file(s): " + ", ".join(conflicts), file=sys.stderr)
        print("  re-run with --force (a backup is taken first)", file=sys.stderr)
        return 1
    if old is not None or conflicts or args.backup:
        bdir = backup(target, old)
        if bdir:
            print(f"[OK] backup: {bdir}")
    for src, rel in plan:
        atomic_copy(src, target / rel)
    pdir = plugins_dir()
    installed_plugins = []
    for name in PLUGINS:
        src = SOURCE / name
        if src.is_file():
            atomic_copy(src, pdir / name)
            installed_plugins.append(name)
    manifest = {
        "schema_version": 1,
        "tag": os.environ.get("VIBEWEAVER_TAG", ""),
        "profile": profile,
        "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": str(SOURCE),
        "files": [{"path": rel, "sha256": sha256(target / rel)} for _src, rel in plan],
        "plugins": installed_plugins,
    }
    (target / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] installed profile={profile} files={len(plan)} -> {target}")
    return 0


def cmd_check(args):
    target = skill_dir()
    manifest = read_manifest(target)
    if manifest is None:
        print("install.py: no .installed.json — not installed by this installer", file=sys.stderr)
        return 1
    bad = []
    for entry in manifest.get("files", []):
        p = target / entry["path"]
        if not p.is_file() or sha256(p) != entry["sha256"]:
            bad.append(entry["path"])
    if bad:
        print("install.py: drift: " + ", ".join(bad), file=sys.stderr)
        return 1
    print(f"profile={manifest.get('profile')} files={len(manifest.get('files', []))} OK")
    return 0


def cmd_uninstall(args):
    target = skill_dir()
    manifest = read_manifest(target)
    if manifest is None:
        print("install.py: nothing to uninstall (no .installed.json)", file=sys.stderr)
        return 1
    removed = 0
    for entry in manifest.get("files", []):
        p = target / entry["path"]
        if p.is_file() and "memory/" not in entry["path"]:
            p.unlink()
            removed += 1
    pdir = plugins_dir()
    for name in manifest.get("plugins", []):
        p = pdir / name
        if p.is_file():
            p.unlink()
    (target / MANIFEST_NAME).unlink(missing_ok=True)
    for d in sorted(target.rglob("*"), reverse=True):
        if d.is_dir() and d != target / "memory":
            try:
                d.rmdir()
            except OSError:
                pass
    print(f"[OK] uninstalled {removed} file(s); memory/ preserved")
    return 0


def cmd_rollback(args):
    target = skill_dir()
    backups = sorted(target.parent.glob(target.name + ".bak.*"))
    if not backups:
        print("install.py: no backup to roll back to", file=sys.stderr)
        return 1
    bdir = backups[-1]
    manifest = read_manifest(bdir)
    if manifest is None:
        print("install.py: backup has no manifest", file=sys.stderr)
        return 1
    for entry in manifest.get("files", []):
        src = bdir / entry["path"]
        if src.is_file():
            atomic_copy(src, target / entry["path"])
    atomic_copy(bdir / MANIFEST_NAME, target / MANIFEST_NAME)
    print(f"[OK] rolled back from {bdir}")
    return 0


def cmd_dry_run(args):
    plan = payload(args.profile)
    print(f"dry-run target: {skill_dir()}")
    print(f"dry-run profile: {args.profile}")
    for _src, rel in plan:
        print(f"dry-run would install: {rel}")
    print(f"dry-run files: {len(plan)}")
    return 0


def cmd_from(args):
    target = skill_dir()
    manifest = read_manifest(target)
    if manifest is None:
        print("install.py: no current install", file=sys.stderr)
        return 1
    print(f"migration from {args.from_tag}: current profile={manifest.get('profile')} "
          f"files={len(manifest.get('files', []))}; no destructive migration steps required")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="vibeweaver installer")
    ap.add_argument("--profile", default="core", choices=["full", "core", "mini", "all"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--rollback", action="store_true")
    ap.add_argument("--backup", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--from", dest="from_tag", default="")
    args = ap.parse_args(argv)

    if args.dry_run:
        return cmd_dry_run(args)
    if args.check:
        return cmd_check(args)
    if args.uninstall:
        return cmd_uninstall(args)
    if args.rollback:
        return cmd_rollback(args)
    if args.from_tag:
        return cmd_from(args)
    return cmd_install(args)


if __name__ == "__main__":
    sys.exit(main())
