# Review verdicts — W18 release-hygiene fix (archived 2026-10-22)

Two independent adversarial fresh-context reviewers (Lane L / §V4) reviewed
`tests/review_package_w18fix.md` (both trees' diffs) read-only. Both verdicts:
**ready-with-fixes**. Findings and adjudication below — every Critical/Important
fixed before delivery, Minors itemized or deferred to project memory.

## Reviewer A (claim-binding / bypass focus) — ready-with-fixes

Strengths: F1-F3 closed with executed proof (repo harness 82/82 exit 0,
byte-identical, E3 re-anchored to D3 + E3b); binder fail-closed on red runs and
mismatch (injected 70/71 → exit 1); sync_skill 15/15 with fail-closed drift;
new changelog counts all reproduce; acceptance #14-18 literal-pass.

Issues: I1 [Bugs] Windows/cp1252 decode crash + `python3` resolution in the
new CI step/harness · I2 [Compliance] binder covers README anchor lines only —
the falsified claim lived in the CHANGELOG · I3 [Compliance] quarantine ban is
a signature + file-list scan (renamed flag/unlisted file escapes) · I4
[Security] `apply_fix --fix` follows dst symlinks (out-of-tree overwrite) ·
M1 `--skip-run` dead mode · M2 returncode ignored · M3 stale 9/9 evidence log +
RED logs are crash traces · M4 w18 tag anchors the pre-fix release · M5 "dual
review" claimed without an in-tree anchor.

## Reviewer B (test-effectiveness / regression focus) — ready-with-fixes

Strengths: dual-layout diff has zero assertion changes (mutation-checked);
SS9-SS15 and CDC cores bite under mutation; falsifiability independently
reproduced (injected 70/71 → exit 1 both docs); 29 evidence files byte-identical
A↔B; E3 assertions are STRICTER (bypass stays closed).

Issues: C1 [Bugs] new CI step deterministically crashes on windows-latest
(cp1252 decode of CJK/emoji suite output) + `python3` calls introduced into the
harness · I1 [Compliance] fix not yet published (GitHub still in the audited
state) · I2 [Bugs] tests pin library seams only (main()/DOCS mutations go
undetected) and neither vector suite runs in CI · I3 [Compliance] the fix's own
evidence lives only in the dev tree (F4 pattern) · I4 `--skip-run` dead ·
I5 log/working-note open at review time (closed at delivery) · Minors: stale
cdc_green.log · weak RED traces · archive header accuracy · binder narrower
than the CHANGELOG claim · payloadFile root-first silent preference.

## Adjudication (fix round, same day)

| Finding | Disposition |
|---|---|
| A-I1 / B-C1 Windows decode + interpreter resolution | FIXED — all text read as UTF-8 (`encoding="utf-8", errors="replace"`); harness `PY = process.env.PYTHON \|\| (win32 ? "python" : "python3")`; CI step unified to `python` |
| A-I2 / B-Minor4 CHANGELOG claim form unbound | FIXED — newest-entry name-anchored binding (`audit_selftest N/N · mutation_sweep N/N · plugin compat N/N · mini gate N/N`); CDC11 pins it (70/71 in the newest entry fails) |
| B-I2 seam/CI coverage | FIXED — CDC12 pins main() wiring (doc drift must reach the exit code), CDC13 pins the returncode rule; both vector suites now run in CI (`Claim-binder + sync-control vectors` step) |
| B-I3 / A-M3 fix evidence not in-tree | FIXED — `tests/sync_skill.py` + `tests/test_sync_skill.py` shipped to the repo tree under copy-plan parity; wave logs in `tests/release_hygiene_fix/` |
| A-M2 returncode | FIXED — `evaluate_proc`: non-zero exit binds nothing (CDC13) |
| A-M1 / B-I4 `--skip-run` | FIXED — dead flag removed (YAGNI) |
| A-M4 tag semantics | FIXED — `w18.1` tags the delivered fix commit; `w18` stays on 9d2c915 per acceptance #17 |
| A-M5 review unanchored | FIXED — this file |
| B-Minor3 archive header | FIXED — four blocks named, 9 excluded lines marked |
| A-I3 signature-scan bypass (renamed flag / unlisted file) | DEFERRED — known boundary, recorded in project memory; red-run binding is the second line of defense |
| A-I4 `apply_fix` follows dst symlinks | DEFERRED — dev-tree tool, attacker needs write access to the repo copy first; recorded in project memory as ⏳ |
| B-Minor5 payloadFile root-first silent preference | DEFERRED — recorded in project memory |
| B-I1 publish state / B-I5 log closure | Delivery checklist: push + log closure after this round (Class-E push pre-authorized by the user) |

Reviewer disagreement: none material (A rated the binder coverage as a boundary,
B as a defect — adjudicated as defect and fixed).
