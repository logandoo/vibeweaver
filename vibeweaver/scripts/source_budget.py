#!/usr/bin/env python3
"""Source File Budget P0/P1 — deterministic, stdlib-only source size report.

Exit 0: pass, warning, or shadow-mode budget finding.
Exit 1: enforce + --final found a file above hard_lines.
Exit 2: configuration, discovery, symlink, or I/O failure (never hidden by shadow).

There is deliberately no baseline recorder, exemption approval, or waiver surface.
"""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

try:
    from git_trust import run_git as _trusted_git
except ImportError:
    import pathlib as _pathlib
    sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent))
    from git_trust import run_git as _trusted_git

try:
    import tomllib
except ImportError:  # Python 3.9/3.10
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

SCHEMA = "source-file-budget/1"
DEFAULTS = {"mode": "shadow", "warn_lines": 1000, "hard_lines": 2000}
POLICY_KEYS = frozenset(DEFAULTS)
MAX_CONFIG_BYTES = 64 * 1024
MAX_SOURCE_BYTES = 64 * 1024 * 1024
SOURCE_EXTENSIONS = frozenset({
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".go", ".rs", ".java", ".c", ".h", ".cc", ".cpp", ".cxx",
    ".hpp", ".cs", ".rb", ".php", ".swift", ".kt", ".kts", ".scala",
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".psm1", ".bat", ".cmd",
    ".sql", ".vue", ".svelte", ".html", ".css", ".scss", ".sass", ".less",
})
EXCLUDED_DIRS = frozenset({
    ".git", ".vibeweaver", ".venv", "venv", "env", ".tox", ".nox",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache", ".pnpm-store",
    ".next", ".nuxt", ".idea", ".vscode", "node_modules", "site-packages",
    "dist", "build", "target", "coverage", "vendor", "third_party", "third-party",
})


class BudgetError(Exception):
    """A fail-closed operational or policy error."""


def measure(raw):
    """Measure bytes without decoding; splitlines handles CRLF/CR/final lines."""
    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return {
        "physical_lines": len(raw.splitlines()),
        "raw_bytes": len(raw),
        "normalized_bytes": len(normalized),
    }


def _fallback_value(value, line_number):
    value = value.strip()
    if value.startswith('"'):
        try:
            parsed, end = json.JSONDecoder().raw_decode(value)
        except (ValueError, json.JSONDecodeError) as exc:
            raise BudgetError(f"config line {line_number}: invalid string") from exc
        if value[end:].strip() and not value[end:].lstrip().startswith("#"):
            raise BudgetError(f"config line {line_number}: trailing value")
        return parsed
    if value.startswith("'"):
        match = re.fullmatch(r"'([^']*)'\s*(?:#.*)?", value)
        if not match:
            raise BudgetError(f"config line {line_number}: invalid literal string")
        return match.group(1)
    match = re.fullmatch(r"([0-9]+)\s*(?:#.*)?", value)
    if not match:
        raise BudgetError(f"config line {line_number}: only strings/integers are supported")
    return int(match.group(1))


def parse_simple_policy(text):
    """Restricted Python 3.9 fallback: parse only flat [source_budget] scalars."""
    result = {}
    active = False
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("["):
            header = re.sub(r"\s+", "", stripped.split("#", 1)[0])
            if header == "[source_budget]":
                active = True
            elif (header.startswith("[source_budget.") or header.startswith("[[source_budget")
                  or header.startswith("[source_budget]")):
                raise BudgetError(f"config line {line_number}: nested/malformed source_budget table")
            else:
                active = False
            continue
        if not active:
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(.+)", stripped)
        if not match:
            raise BudgetError(f"config line {line_number}: unsupported source_budget syntax")
        key, value = match.groups()
        if key in result:
            raise BudgetError(f"config line {line_number}: duplicate {key}")
        result[key] = _fallback_value(value, line_number)
    return result


def _read_config(path, explicit):
    if not path.is_file():
        if explicit:
            raise BudgetError(f"config not found: {path}")
        return None
    size = path.stat().st_size
    if size > MAX_CONFIG_BYTES:
        raise BudgetError(f"config exceeds {MAX_CONFIG_BYTES} bytes")
    try:
        return path.read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise BudgetError(f"cannot read config: {path}") from exc


def load_policy(root, config_path=None):
    explicit = config_path is not None
    path = Path(config_path) if explicit else root / "config.toml"
    if explicit and not path.is_absolute():
        path = root / path
    text = _read_config(path, explicit)
    if text is None:
        return dict(DEFAULTS)
    if tomllib is not None:
        try:
            document = tomllib.loads(text)
        except Exception as exc:
            raise BudgetError(f"invalid TOML config: {path}") from exc
        section = document.get("source_budget", {})
        if not isinstance(section, dict):
            raise BudgetError("[source_budget] must be a table")
    else:
        section = parse_simple_policy(text)
    unknown = sorted(set(section) - POLICY_KEYS)
    if unknown:
        raise BudgetError(
            "unsupported [source_budget] key(s): " + ", ".join(unknown)
            + "; trusted baseline/exemption/waiver is not available in v1"
        )
    policy = dict(DEFAULTS)
    policy.update(section)
    if policy["mode"] not in ("shadow", "enforce"):
        raise BudgetError("source_budget.mode must be 'shadow' or 'enforce'")
    for key in ("warn_lines", "hard_lines"):
        value = policy[key]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise BudgetError(f"source_budget.{key} must be a positive integer")
    if policy["warn_lines"] > policy["hard_lines"]:
        raise BudgetError("source_budget.warn_lines must be <= hard_lines")
    return policy


def _in_scope(rel):
    parts = rel.split("/")
    if any(part in EXCLUDED_DIRS for part in parts[:-1]):
        return False
    return Path(parts[-1]).suffix.lower() in SOURCE_EXTENSIONS


def _walk_error(exc):
    raise BudgetError(f"filesystem discovery failed: {exc}") from exc


def _reject_nested_git(root):
    for current, dirs, files in os.walk(
        str(root), topdown=True, onerror=_walk_error, followlinks=False
    ):
        current_path = Path(current)
        if current_path != root and ".git" in set(dirs) | set(files):
            rel = current_path.relative_to(root).as_posix()
            raise BudgetError(f"nested Git worktree/submodule is not scanned: {rel}")
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS and d != ".git")


def _reject_gitlinks(root):
    try:
        result = _trusted_git(root, "ls-files", "--stage", "-z", "--",
                              timeout=30, text=False)
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        raise BudgetError("git submodule discovery failed") from exc
    if result.returncode:
        raise BudgetError("git submodule discovery failed")
    for record in result.stdout.split(b"\0"):
        metadata, separator, raw_path = record.partition(b"\t")
        if separator and metadata.startswith(b"160000 "):
            raise BudgetError(f"nested Git submodule is not scanned: {os.fsdecode(raw_path)}")


def _git_discovery(root):
    _reject_nested_git(root)
    _reject_gitlinks(root)
    try:
        result = _trusted_git(root, "ls-files", "--cached", "--others",
                              "--exclude-standard", "--deduplicate", "-z", "--",
                              timeout=30, text=False)
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        raise BudgetError("git source discovery failed") from exc
    if result.returncode:
        raise BudgetError("git ls-files failed: " + result.stderr.decode("utf-8", "replace").strip())
    paths = set()
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        rel = os.fsdecode(raw).replace(os.sep, "/")
        if rel.startswith("/") or rel == ".." or rel.startswith("../"):
            raise BudgetError(f"unsafe git path outside root: {rel!r}")
        if _in_scope(rel):
            paths.add(rel)
    return sorted(paths)


def _filesystem_discovery(root):
    paths = []
    for current, dirs, files in os.walk(
        str(root), topdown=True, onerror=_walk_error, followlinks=False
    ):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)
        for name in sorted(files):
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            if _in_scope(rel):
                paths.append(rel)
    return sorted(paths)


def discover(root, policy):
    try:
        probe = _trusted_git(root, "rev-parse", "--is-inside-work-tree",
                             timeout=10, text=False)
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        raise BudgetError("Git availability probe failed; refusing implicit filesystem fallback") from exc
    if probe.returncode == 0 and probe.stdout.strip() == b"true":
        return _git_discovery(root), "git"
    not_a_repository = probe.returncode == 128 and b"not a git repository" in probe.stderr.lower()
    if not_a_repository:
        if policy["mode"] == "enforce":
            raise BudgetError("enforce mode requires a Git worktree; non-Git discovery is shadow-only")
        _reject_nested_git(root)
        return _filesystem_discovery(root), "filesystem"
    detail = probe.stderr.decode("utf-8", "replace").strip()
    raise BudgetError(f"Git availability probe failed ({probe.returncode}): {detail}")


def _inspect(root, rel):
    path = root
    info = None
    try:
        for part in Path(rel).parts:
            path = path / part
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise BudgetError(f"symlink source/path component is not followed: {rel}")
    except OSError as exc:
        raise BudgetError(f"cannot stat {rel}") from exc
    if info is None or not stat.S_ISREG(info.st_mode):
        raise BudgetError(f"non-regular source path: {rel}")
    if info.st_size > MAX_SOURCE_BYTES:
        raise BudgetError(f"source exceeds {MAX_SOURCE_BYTES} byte read cap: {rel}")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise BudgetError(f"cannot read source: {rel}") from exc
    if b"\0" in raw:
        return None, rel
    return {"path": rel, **measure(raw)}, None


def evaluate(root, policy, final=False):
    paths, discovery = discover(root, policy)
    files = []
    binaries = []
    errors = []
    for rel in paths:
        try:
            item, binary = _inspect(root, rel)
            if binary:
                binaries.append(binary)
            else:
                files.append(item)
        except BudgetError as exc:
            errors.append(str(exc))
    findings = []
    for item in files:
        lines = item["physical_lines"]
        if lines > policy["hard_lines"]:
            status, limit = "OVER_HARD", policy["hard_lines"]
        elif lines > policy["warn_lines"]:
            status, limit = "OVER_WARN", policy["warn_lines"]
        else:
            continue
        findings.append({**item, "status": status, "limit": limit})
    findings.sort(key=lambda item: item["path"])
    files.sort(key=lambda item: item["path"])
    over_hard = sum(item["status"] == "OVER_HARD" for item in findings)
    over_warn = sum(item["status"] == "OVER_WARN" for item in findings)
    if errors:
        result = "ERROR"
    elif policy["mode"] == "enforce" and final and over_hard:
        result = "FAIL"
    elif policy["mode"] == "shadow" and findings:
        result = "SHADOW"
    else:
        result = "PASS"
    summary = {
        "files": len(files),
        "physical_lines": sum(item["physical_lines"] for item in files),
        "raw_bytes": sum(item["raw_bytes"] for item in files),
        "normalized_bytes": sum(item["normalized_bytes"] for item in files),
        "over_warn": over_warn,
        "over_hard": over_hard,
        "errors": len(errors),
    }
    return {
        "schema": SCHEMA,
        "result": result,
        "policy": policy,
        "final": bool(final),
        "discovery": discovery,
        "summary": summary,
        "files": files,
        "findings": findings,
        "excluded": {"binary": sorted(binaries)},
        "errors": sorted(errors),
    }


def render_text(data, top=None):
    policy = data["policy"]
    summary = data["summary"]
    lines = [
        "SOURCE-BUDGET mode={mode} final={final} discovery={discovery} files={files} "
        "lines={lines} over_warn={warn} over_hard={hard} errors={errors}".format(
            mode=policy["mode"], final=str(data["final"]).lower(),
            discovery=data["discovery"], files=summary["files"],
            lines=summary["physical_lines"], warn=summary["over_warn"],
            hard=summary["over_hard"], errors=summary["errors"],
        )
    ]
    shown = data["findings"] if top is None else data["findings"][:top]
    for item in shown:
        lines.append(
            f"{item['status']} {item['path']} lines={item['physical_lines']} "
            f"limit={item['limit']} raw_bytes={item['raw_bytes']} "
            f"normalized_bytes={item['normalized_bytes']}"
        )
    if len(shown) < len(data["findings"]):
        lines.append(f"SHOWING {len(shown)} of {len(data['findings'])} findings; JSON remains complete")
    for path in data["excluded"]["binary"]:
        lines.append(f"BINARY {path} excluded")
    for error in data["errors"]:
        lines.append(f"ERROR {error}")
    lines.append(f"SOURCE-BUDGET RESULT {data['result']}")
    return "\n".join(lines) + "\n"


def _atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="project root (default: cwd)")
    parser.add_argument("--config", help="TOML path; relative paths resolve under --root")
    parser.add_argument("--final", action="store_true", help="enforce hard budget at completion")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", help="also atomically write the complete JSON report to this path")
    parser.add_argument("--top", type=int, default=20, help="text finding display limit; JSON remains complete")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.top <= 0:
            raise BudgetError("--top must be positive")
        root = Path(args.root).expanduser().resolve()
        if not root.is_dir():
            raise BudgetError(f"root is not a directory: {root}")
        policy = load_policy(root, args.config)
        data = evaluate(root, policy, args.final)
        json_rendered = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.format == "json":
            rendered = json_rendered
        else:
            rendered = render_text(data, args.top)
        if args.output:
            output = Path(args.output)
            if not output.is_absolute():
                output = root / output
            _atomic_write(output, json_rendered)
        sys.stdout.write(rendered)
        for error in data["errors"]:
            sys.stderr.write(f"source_budget: {error}\n")
        if data["result"] == "ERROR":
            return 2
        if data["result"] == "FAIL":
            return 1
        return 0
    except (BudgetError, OSError) as exc:
        sys.stderr.write(f"source_budget: ERROR: {exc}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
