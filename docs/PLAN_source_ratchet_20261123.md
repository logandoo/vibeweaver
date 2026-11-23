# PLAN — Source ratchet + artifact budget (P0+P1)

Date: 2026-11-23 · Lane L · Class CODE · Mode AUTO
Scope: P0 (source no-growth ratchet, review-package artifact cap, total-blob/headroom) + P1 (low-touch grants, source/tests groups, seam/lean review).
Status: design frozen; implementation follows TDD.

## 1. Goal

Close the two severe gaps without turning the gate into a human-approval queue:

1. `source_budget.py` currently reports only (shadow); a file can grow forever.
2. Generated artifacts (review package, logs, eval trajectories) have no dedicated cap; the largest-blob ratchet is reactive and repo-wide.

The new model has a **zero-approval normal path**. A human is involved only for a rare, long-term budget increase or a Class-E history rewrite.

## 2. Non-goals

- No per-file or per-commit human waivers.
- No mechanical splitting by line count; size is a signal, not a command.
- No new runtime dependency; stdlib-only. `ratchet-size` / `module-size-discipline` are design references, not vendored code.
- No change to the existing largest-blob debt baseline or F19 machine-state semantics.
- No enforcement on untouched legacy files.

## 3. Low-touch model

| Scenario | Human? | Behavior |
|---|---|---|
| New file under hard cap | No | pass |
| New file over hard cap | No | fail; split by seam or archive |
| Existing over-cap file shrinks/holds | No | pass; `tighten` can lower its ceiling |
| Existing over-cap file grows | No | fail; shrink, split, or (rare) budget grant |
| Group total within headroom | No | pass |
| Group total over ceiling | No | fail; delete/offset or (rare) budget grant |
| Review package over cap | No | auto index + external archive + sha256 |
| Log/trajectory/media over cap | No | auto archive/truncate with manifest; no grant |
| Long-term group budget increase | Yes, once | `grant` is append-only, reason/expiry, one-line PR diff |
| History rewrite | Yes, Class-E | existing A10.1 runbook |

**Grant is budget-level, not file-level and not per-change.** The default is to fit the budget by design; an exception is a one-time standing adjustment.

## 4. Source ratchet semantics

`source_budget.py` remains the measurement/report tool (stable schema `source-file-budget/1`).
New `scripts/source_ratchet.py` consumes its JSON report (or calls the measurement functions) and enforces:

- **Groups**: `source` and `tests`; each has a total ceiling.
- **Initial baseline**: `init` records current group totals (with slack, default 5%) and every file already over `hard_lines` at its current size. This is a normal reviewed commit; no extra approval.
- **New files**: no per-file baseline; a file over `hard_lines` fails.
- **Existing over-cap files**: their recorded size is a ceiling; shrinking/holding passes; growth fails.
- **Files under `hard_lines`**: may grow up to `hard_lines`; the group ceiling still applies.
- **`budget`**: prints current/ceiling/headroom and near-cap files; JSON supported. Always exit 0 except hook mode.
- **`check --final`**: enforces the above; exit 0/1/2.
- **`check --base REF`**: rejects any base-policy/file/group-ceiling raise; grants are additive and raise the effective ceiling, never the committed base. The base must be a strict ancestor with a baseline (pin the adoption commit, not HEAD or a pre-adoption ref).
- **`tighten`**: lowers group/file ceilings to current size (+slack); never raises. Agent may run it after a cleanup; no human.
- **`grant`**: human-only; raises a group ceiling, appends `by/reason/expires/before/after`; agent is forbidden to run it. Grants expire; expired grants are ignored (the ceiling reverts to the last non-expired value/usage).
- **Baseline**: `tests/source_ratchet_baseline.json`, committed; shrink-only; history-min tamper anchor; no new keys after adoption.
- **Grants**: `tests/source_ratchet_grants.jsonl`, append-only; one-line diffs in PR; `--base` detects raises.

Thresholds (initial, calibratable):

- `warn_lines=1000`, `hard_lines=2000` (existing defaults).
- Existing over-hard files freeze at current size.
- Group slack 5% (configurable; `--slack`).
- Tests use the same hard cap but a separate group ceiling; a test file over hard is frozen, not forced to split.
- `budget`/`check` output names the source/tests split; docs/data/generated/vendor are excluded.

Seam hints: when a file crosses `hard_lines`, report top-level definitions near the middle (like `ratchet seams`). This is advisory; A4.9 decides whether extraction is justified.

## 5. Artifact budget

New `scripts/artifact_budget.py` + `tests/artifact_baseline.json`:

- Groups and caps (initial):
  - `review`: `tests/review_package*.md` — 512 KiB/file, 1 MiB total.
  - `logs`: `tests/**/*.log` — 5 MiB/file, 50 MiB total.
  - `trajectory`: `tests/eval/**/trajectory.json` — 2 MiB/file, 100 MiB total.
  - `media`: `tests/**/*.{png,webm,wav,mp4,mp3}` — 5 MiB/file, 50 MiB total.
- Existing over-cap files are frozen at current size; new/changed artifacts must fit; shrinking is always allowed.
- `check --final` fails over cap; `--json` for tooling.
- **Review package handling**: `scripts/make_review_package.sh` gets `--max-bytes` (default 512 KiB). If the full package exceeds it:
  1. write the full package to `.vibeweaver/artifacts/review_package_<base>_<head>.md` (ignored) or an external archive;
  2. write `tests/review_package.md` as an index: diff stat, commit list, per-file summary, full-package path + sha256 + size;
  3. group 16 sees the index (>0 bytes); A4.9 reads the full package via the index path.
- No human approval for any of this; the archive manifest is the evidence.

## 6. Repo total budget

Extend group 21 reporting (not the existing `largest-blob` key):

- `total reachable blob bytes` and top-N blob distribution (path/size) from `git rev-list --objects --all` + `git cat-file`.
- `tests/repo_budget_baseline.json` (new, one-time): live-tree total, ceiling, top-N, `reason`; shrink-only. Cumulative reachable-blob bytes are reported nowhere as a ratchet because every new commit would grow them; history is covered by max-blob/.git.
- Rollout: live-tree ceiling at adoption (+10% slack), top-N report, then FAIL on growth. Existing max-blob/.git/untracked/wave checks stay unchanged.
- No new key is added to `tests/debt_baseline.json`; F19 semantics remain untouched.

## 7. Ponytail / lean review

- Add a compact **Necessity Ladder** and **Lean Review** section to `CODING_PRINCIPLES.md` (not `SKILL.md`; only ~13 B headroom).
- A4.9 review prompt gets one lean pass:
  - delete dead/speculative code; reuse existing helpers; stdlib/native before dependencies; one line if clear; otherwise the minimum complete change.
  - split by responsibility seam, never by line count.
  - never cut trust-boundary validation, error handling, security, accessibility.
- Output `Lean: -N lines possible` when applicable; no new runtime dependency, no always-on plugin.
- P2 (not this task): `shortcut:` ledger and local A/B calibration. The rule text is included now because it is cheap and directly addresses growth.

## 8. Trust model

- The agent may run `init`, `budget`, `check`, `tighten`.
- The agent must not run `grant`; grants are human-only and review-visible.
- `--base` + append-only grants + history-min + committed baseline make raises tamper-evident.
- Without protected CI/CODEOWNERS, this is **not cryptographically tamper-proof**; do not claim otherwise.
- Normal path requires zero human interaction; a grant should be rare (target: <1 per wave).

## 9. Tests and mutations

- `tests/test_source_ratchet.py`: init/budget/check/tighten/grant; new file over cap; existing growth fail; shrink/hold pass; group ceiling; `--base` raise without grant; grant expiry; delete/re-record; rename/copy; no-baseline behavior.
- `tests/test_artifact_budget.py`: each group cap; over-cap review index + archive; frozen legacy; shrink pass; no human approval path.
- Extend `tests/test_assert_groups.py` or a new test for total-blob report/baseline; mutation cases for raise/delete-re-record/rename-copy.
- Keep existing suites green: 85/85 assert groups, 50/50 mutation, 602/0 build, 158 unittest.

## 10. Rollout / rollback

1. Implement measurement + baseline; run `init` in shadow, inspect distribution.
2. Enable `check --final` for new files and touched over-cap files; keep untouched legacy advisory.
3. Add group ceilings + grants; run one wave; if normal work needs >1 grant, raise slack or split the group policy.
4. Add artifact cap/index; verify F19-style review package would be archived, not committed.
5. Total blob WARN → ratchet after calibration.
6. Rollback: remove the ratchet call from build; keep `source_budget.py` measurement. Baselines/grants remain as evidence.

## 11. Acceptance mapping

Criteria 1–8 in `tests/acceptance.md` map to sections 4–9; the low-touch model is section 3/8; regression is section 9; evidence is the usual seal/lock/final gate.
