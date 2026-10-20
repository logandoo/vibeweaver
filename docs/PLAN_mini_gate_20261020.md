# PLAN — vibeweaver-mini-gate (2026-10-20)

## Consistency Hub

| entity | canonical spelling / value | source of truth |
|---|---|---|
| plugin id | `vibeweaver-mini-gate` | this plan |
| plugin file | `vibeweaver-mini/vibeweaver-mini-gate.js` | repo layout |
| disable env | `VIBEWEAVER_MINI_GATE=off` | mirrors `VIBEWEAVER_GATE` |
| timeout env | `VIBEWEAVER_MINI_TIMEOUT_MS` (default 900000) | checker bound |
| mini markers | `vw_check.py` · mini `script/check.sh` · `.vw_test_hashes.json` | mini kit |
| full-skill marker (excludes mini mode) | `tests/verification_log.md` at the session root | full gate activation |
| checker preference | `python3 vw_check.py` → mini `bash script/check.sh` (Unix only) | oracle first |
| pass flag | literal `ALL CHECKS PASS` | mini SKILL.md |
| corrective-prompt budget | 2 per session | mirrors stop-guard budget |
| test oracle | `tests/mini_gate_test.mjs` (executable acceptance) | this plan |

## Task 1 — plugin behavior

**Files** — Create `vibeweaver-mini/vibeweaver-mini-gate.js`; Test `tests/mini_gate_test.mjs`.

**Interfaces**
- *Consumes:* `server({client, directory})` (v1) and `setup(ctx)` (v2), matching `vibeweaver-gate.js`'s dual contract.
- *Produces:* default export `{ id, server, setup }` only (no extra exports — the v1 legacy iterator and v2 schema depend on it).
- Internal: `findMiniRoot(starts) -> string|null` · `runChecker(root) -> {ok, output, mode}` · `isCompletionClaim(text) -> boolean`.

**Test seam** — `tests/mini_gate_test.mjs`: import the real plugin, invoke the real hooks with a fake client / fake v2 context and a fake `vw_check.py` that toggles pass/fail via `.state`. One seam for both adapters.

**Steps**
1. RED: write the test harness; it must fail with `plugin module missing` before the plugin exists.
2. Implement `findMiniRoot` + `runChecker`; run the test — write-hook cases turn green.
3. Implement completion tracking + prompt budget; run the idle cases.
4. Implement v2 `setup`; run the v2 cases.
5. Run `node tests/mini_gate_test.mjs` — all pass.

## Task 2 — installers

**Files** — Create `vibeweaver-mini/install.sh`, `vibeweaver-mini/install.bat`.
**Interfaces** — installs `SKILL.md` + `scripts/` + `vibeweaver-mini-gate.js` into `~/.config/opencode/skills/vibeweaver-mini/` and the plugin into `~/.config/opencode/plugins/`.
**Test seam** — shell dry-run into a temp `XDG_CONFIG_HOME`; assert the four installed paths exist.
**Steps** — write both installers; run the temp-home install; assert `SKILL.md`, `vw_check.py`, `check.sh`, plugin.

## Task 3 — package checks + CI

**Files** — Modify `verify_skill.py`, `.github/workflows/verify.yml`.
**Interfaces** — `verify_skill.py` gains `MINI_FILES` existence checks and a `node --check` on the mini plugin; CI runs `node tests/mini_gate_test.mjs`.
**Test seam** — `python3 verify_skill.py`; CI YAML parses.
**Steps** — add checks; run `verify_skill.py`; run the new node test.

## Task 4 — docs + changelog

**Files** — Modify `README.md`, `README_zh.md`, `vibeweaver-mini/README_en.md`, `README_zh.md`, `vibeweaver-mini/SKILL.md`, `CHANGELOG.md`, `CHANGELOG_zh.md`.
**Interfaces** — none (prose).
**Test seam** — readme lint facts 10/10; every named path exists.
**Steps** — replace the “not shipped” paragraph with the shipped behavior; document install + disable; add the changelog entry.
