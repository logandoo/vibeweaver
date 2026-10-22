#!/usr/bin/env python3
"""Checks for check_doc_counts.py (W18 release-hygiene fix, 2026-10-22).

The W18 audit found README/CHANGELOG counts that no in-tree run could
reproduce (F1/F6). These checks prove the binder (a) reads both languages'
claim shapes, (b) ignores historical prose counts, (c) FAILS on a mismatch
(the falsifiable anchor: 70/71 vs 82/82), and (d) bans the CI quarantine flag.
"""
import importlib.util
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "check_doc_counts", ROOT / "check_doc_counts.py")
cdc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cdc)

RESULTS = []


def rec(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))


EN = """\
node vibeweaver/scripts/audit_selftest.mjs  # 571 fixture checks (T6 skips)
node vibeweaver/scripts/mutation_sweep.mjs  # 44 mutations, each must be caught
node tests/plugin_compat_test.mjs           # 82/82 dual loader compat
node tests/mini_gate_test.mjs               # 62/62 mini checker gate: idle + installers
| `scripts/audit_selftest.mjs` / `scripts/mutation_sweep.mjs` | 571 fixture checks / 44 mutation checks |
"""

ZH = """\
node vibeweaver/scripts/audit_selftest.mjs  # 571 项 fixture 检查（无校准数据时 T6 SKIP）
node vibeweaver/scripts/mutation_sweep.mjs  # 44 项变异，每项都必须被抓到
node tests/plugin_compat_test.mjs           # 82/82 双 loader 兼容
node tests/mini_gate_test.mjs               # 62/62 mini checker gate：v1/v2 write
| `scripts/audit_selftest.mjs` / `mutation_sweep.mjs` | 571 项 fixture 检查 / 44 项变异检查 |
"""

HISTORY = """\
- **第十三波：按比例验证。** 证据是 166 条 fixture 断言、41 项变异、两轮对抗评审。
qwen3.6 上 mini 赢；44% 抬到 81%。
"""

SELFTEST_RUN = "=== SUMMARY ===\nfixture checks: 571, failures: 0, skipped: 1\n"
MUTATION_RUN = "=== MUTATION SWEEP: 44 passed, 0 failed ===\n"
COMPAT_RUN = "=== COMPAT HARNESS: 82/82 passed, 0 failed ===\n"
MINI_RUN = "RESULT: 62/62 passed, 0 failed\n"


def main():
    en = cdc.extract_claims(EN)
    rec("CDC1 EN claim shapes extracted",
        en.get("selftest") == [571] and en.get("mutation") == [44]
        and en.get("compat") == [(82, 82)] and en.get("mini") == [(62, 62)],
        str(en))

    zh = cdc.extract_claims(ZH)
    rec("CDC2 ZH claim shapes extracted (same values)",
        zh == en, str(zh))

    hist = cdc.extract_claims(HISTORY)
    rec("CDC3 historical prose counts are not claims (no command anchor)",
        not hist, str(hist))

    runs = {
        "selftest": cdc.parse_run("selftest", SELFTEST_RUN),
        "mutation": cdc.parse_run("mutation", MUTATION_RUN),
        "compat": cdc.parse_run("compat", COMPAT_RUN),
        "mini": cdc.parse_run("mini", MINI_RUN),
    }
    rec("CDC4 run parsers read SUMMARY lines",
        runs["selftest"] == (571, 0) and runs["mutation"] == (44, 0)
        and runs["compat"] == (82, 82, 0) and runs["mini"] == (62, 62, 0),
        str(runs))

    rec("CDC5 matching claims pass silently", cdc.compare_counts(runs, en) == [],
        str(cdc.compare_counts(runs, en)))

    stale = dict(en)
    stale["compat"] = [(70, 71)]
    errs = cdc.compare_counts(runs, stale)
    rec("CDC6 mismatched claim FAILS (falsifiable anchor: 70/71 vs 82/82)",
        any("compat" in e and "70/71" in e for e in errs), str(errs)[:160])

    missing = {"selftest": [571], "mutation": [44], "compat": [(82, 82)]}
    errs = cdc.compare_counts(runs, missing)
    rec("CDC7 suite with no claim is a named error", any("mini" in e for e in errs),
        str(errs)[:160])

    red = dict(en)
    red["compat"] = [(82, 82, 1)]
    runs_red = dict(runs)
    runs_red["compat"] = (82, 82, 1)
    errs = cdc.compare_counts(runs_red, red)
    rec("CDC8 a red suite cannot bind claims (failures must be 0)",
        any("red" in e or "failed" in e for e in errs), str(errs)[:160])

    rec("CDC9 quarantine ban flags --allow-known in CI/harness",
        cdc.scan_quarantine_text("run: node tests/plugin_compat_test.mjs --allow-known\n")
        and not cdc.scan_quarantine_text("run: node tests/plugin_compat_test.mjs\n"),
        "")

    rec("CDC10 historical comment documenting removal is not quarantine",
        not cdc.scan_quarantine_text(
            "// W18 D-W18-2: the known-failure quarantine (--allow-known / E3/G9) is\n"
            "// REMOVED\n")
        and cdc.scan_quarantine_text(
            "const allowKnown = process.argv.includes(\"--allow-known\")\n"),
        "")

    # CDC11 (review A-I2): the falsified W18 claim lived in the CHANGELOG
    # ("plugin compat 82/82") — the newest entry binds by name now.
    CHANGELOG = ("# Changelog\n\n## 2026-10-22: fix\n\n**Verification.** "
                 "audit_selftest 571/0 (1 skipped) · mutation_sweep 44/0 · "
                 "plugin compat 70/71 (E3 known) · mini gate 62/62\n\n"
                 "## 2026-10-21: older wave\n\n**Verification.** "
                 "plugin compat 71/71 · audit_selftest 568/0\n")
    cl = cdc.extract_changelog_claims(CHANGELOG)
    errs = cdc.compare_counts(runs, cl, "changelog newest entry")
    rec("CDC11 newest changelog entry binds by name (70/71 fails) + old entry exempt",
        cl.get("compat") == [(70, 71)] and cl.get("selftest") == [(571, 0)]
        and any("compat" in e for e in errs) and not any("568" in e or "71/71" in e
                                                        for e in errs),
        str(errs)[:160])

    # CDC12 (review I2): the main() seam is pinned — docs wiring + compare
    # results must reach the exit code.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="cdc-main-") as td:
        tdp = pathlib.Path(td)
        doc_en = ("node vibeweaver/scripts/audit_selftest.mjs  # 571 fixture checks\n"
                  "node vibeweaver/scripts/mutation_sweep.mjs  # 44 mutations\n"
                  "node tests/plugin_compat_test.mjs  # 82/82 dual loader compat\n"
                  "node tests/mini_gate_test.mjs  # 62/62 mini checker gate\n")
        doc_zh = ("node vibeweaver/scripts/audit_selftest.mjs  # 571 项 fixture 检查\n"
                  "node vibeweaver/scripts/mutation_sweep.mjs  # 44 项变异\n"
                  "node tests/plugin_compat_test.mjs  # 82/82 双 loader 兼容\n"
                  "node tests/mini_gate_test.mjs  # 62/62 mini checker gate\n")
        (tdp / "README.md").write_text(doc_en)
        (tdp / "README_zh.md").write_text(doc_zh)
        fake = lambda key: (runs[key], None)  # noqa: E731
        rc_ok = cdc.main([], root=tdp, run=fake)
        (tdp / "README_zh.md").write_text(doc_zh.replace("82/82", "70/71"))
        rc_bad = cdc.main([], root=tdp, run=fake)
    rec("CDC12 main() seam: doc wiring reaches the exit code (ok→0, drift→1)",
        rc_ok == 0 and rc_bad == 1, f"ok={rc_ok} bad={rc_bad}")

    # CDC13 (review M2): a non-zero exit with a green-looking SUMMARY binds
    # nothing.
    value, err = cdc.evaluate_proc("compat", COMPAT_RUN, 1)
    rec("CDC13 non-zero exit cannot bind claims", value is None
        and "exited 1" in (err or ""), f"value={value} err={err}")

    fails = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n=== {len(RESULTS) - len(fails)}/{len(RESULTS)} pass" +
          (f" — FAILED: {', '.join(fails)}" if fails else " ==="))
    return 1 if fails else 0


def test_check_doc_counts_vectors():
    assert main() == 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
