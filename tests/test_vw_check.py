#!/usr/bin/env python3
"""Regression tests for the shipped vw_check.py template (APPENDIX §A4.8).

Run: python3 tests/test_vw_check.py
"""
import pathlib
import subprocess
import sys
import tempfile

CHECKER = pathlib.Path(
    "/Users/logan/Documents/DEV/SKILLS/vibeweaver-repo/vibeweaver-mini/scripts/vw_check.py"
)


def run(cwd):
    return subprocess.run([sys.executable, str(CHECKER)], cwd=cwd,
                          capture_output=True, text=True)


def case(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" — " + detail if detail else ""))
    return ok


def main():
    import importlib.util
    if importlib.util.find_spec("pytest") is None:
        print(f"ENVIRONMENT: pytest is not importable by {sys.executable} — this is "
              f"an environment issue, not a code failure. Install it "
              f"(python3 -m pip install --user 'pytest<8') and re-run.")
        return 2
    results = []
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        r = run(td)
        results.append(case("no tests refuses", r.returncode == 1 and "NO TESTS FOUND" in r.stdout))
        (td / "tests").mkdir()
        (td / "tests" / "test_api.py").write_text("def test_ok():\n    assert 1 == 1\n")
        r = run(td)
        results.append(case("nested test_*.py discovered", r.returncode == 0 and "ALL CHECKS PASS" in r.stdout))
        (td / "tests" / "test_api.py").write_text("def test_ok():\n    assert 2 == 2\n")
        r = run(td)
        results.append(case("modified test refuses", r.returncode == 1 and "TEST SET CHANGED" in r.stdout))
        (td / "tests" / "test_api.py").write_text("def test_ok():\n    assert 1 == 1\n")
        (td / "tests" / "test_new.py").write_text("def test_new():\n    assert 1 == 1\n")
        r = run(td)
        results.append(case("added test refuses", r.returncode == 1 and "TEST SET CHANGED" in r.stdout))
        (td / ".vw_test_hashes.json").write_text("{bad json")
        r = run(td)
        results.append(case("corrupt hash record refuses (fail-closed)",
                            r.returncode == 1 and "UNREADABLE" in r.stdout))
    print(f"{sum(results)}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
