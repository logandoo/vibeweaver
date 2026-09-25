# Changelog

Waves of design history, newest first. Entries are moved verbatim from the README; the current state of the project is described in [README.md](README.md).

## 2026-09-24: wave10 — loop-guard blind spots closed (no-newline streams, large periods) + public docs synced

Closes the two loop-guard blind spots left on record from wave9, and syncs the public repo's Chinese README and both changelogs (the English README changes sit mid/low in the page, so they read as "unchanged" at a glance).

- **No-newline streaming repeats (char-level suffix period).** When the tail is newline-sparse (<4 newlines in the last 2KB, or a trailing line over 512 chars), the same ≥32-char unit containing a letter/digit repeated ≥4× in a row now triggers. Candidate periods come from re-occurrences of the last 32-char seed (native `lastIndexOf`, ≤16 candidates), and a stream that is itself short-periodic ("very "×40) is caught by probing its ≥32-char super-period multiples.
- **Large block periods, 192 → 640 lines.** The line-group period cap rose to ≤640 lines with the tail window sized to 96KB, so three copies of realistic code (~50 chars/line or less) all fit; candidates stay filtered by last-line re-occurrence with exact 3-copy comparison. G10 (300-line ×3) and G10b (640-line ×3) now trigger.
- **Uniform 4-copy bar.** A single repeated unit (one line, or one no-newline block) needs 4 copies, not 3, and must hold real content — so a repeated JSX/HTML element ×3 and a pure-punctuation run stay clean, matching the line path's single-line rule.
- **Public docs.** README_zh.md mirrors the English (dual-compat section, loop-guard bullet, audit C8/loop-guard paragraphs, dual-generation API caveat); CHANGELOG.md and CHANGELOG_zh.md gain wave8/9/10 in this commit.

Verified: harness 43/43 (G9 ×3 clean / ×4 fires / super-period fires / JSX + punctuation clean, G10, G10b), self-test 44 checks, sweep 27/27, artifact assertions 26/26; payload byte-identical across four copies; repo `verify_skill.py` 9 checks + unittest 13/13; two review rounds, scoped re-review 7/7 ADDRESSED (ready).

## 2026-09-24: wave9 — v1 startup silence, C8 latch self-clearing, and the loop-guard

Three user-driven changes: two defects in wave8's v1 surface, and the new degenerate-output watchdog.

- **v1 startup was printing red lines.** opencode v1's hybrid bridge calls the v2 `setup()` with a partial context (no `location`/`tool`/`event`), and the new adapter printed two error-style lines on every v1 start in every project. It now returns silently there and warns only on a genuinely partial v2 host. A real v1 TUI start shows zero plugin output lines.
- **C8 latch could self-deadlock.** The audit rescanned the whole immutable bash history each final audit, so a session that ever ran a forbidden raw command (the banned pattern-kill form) stayed C8-BAD forever and its RED latch could never clear. Now each forbidden command flags only once per project root (sha1 command-hash dedup, final-phase persistence in `.vibeweaver/audit-state.json`); a mid-phase warn does not consume the one-shot, so the canonical order (forbidden command run mid-task, then the completion audit) still latches, and the latch self-clears on the next clean audit. New fixtures T21/T22/T23.
- **loop-guard (v1).** A bounded tail scan of the assistant text stream: an identical line-group repeating at the tail (period derived from the data), or a trailing run of ≥12 bare tokens stepping +1 (integers `1,2,…,179` or bijective base-26 letters `a,b,…,kf`). On a hit it interrupts (v1 `session.abort` / v2 `session.interrupt({continue:false})`) and posts a corrective prompt naming the pattern. One intervention per episode (re-arms after clean text), two per session at most, later episodes log-only; `VIBEWEAVER_LOOPGUARD=off` disables it. Numbered lists with content and a 2× repeat are designed out.
- **Two review rounds (A4.9).** Round one came back not-ready on a Critical (the mid-phase audit was consuming the C8 one-shot, so mid-task forbidden commands never latched) plus Important/Minor detector-tuning findings; all fixed, scoped re-review 8/8 ADDRESSED.

Verified: harness 40/40 at this wave (G1–G8), self-test 44 checks, sweep 27/27, real v1 TUI start with zero plugin lines, a real v1 RED-project write still GATE-BLOCKED; payload byte-identical across four copies.

## 2026-09-24: wave8 — dual-compat plugins for opencode v1 and v2 (one file each)

opencode v2.0 shipped its plugin system as a deliberate breaking change: the v2 loader decodes only a module's `default` export against `{ id, setup }`, so the old v1 function exports stopped loading. The gate and auditor plugins had to run on both generations from a single file. The v1↔v2 delta was verified against primary sources (the opencode v2 docs, the v1.18.32 loader, the v2.0.16 loader and published plugin types, plus running the real v2 binary in an isolated home).

- **One-file dual shape.** Both plugins now default-export `{ id, server, setup }`. v1 (≥ 1.18.29) calls `server()` for the v1 hooks map; v2 (≥ 2.0.0) decodes `{ id, setup }` and calls `setup(ctx)` for the domain-API hooks. Same logic, same `.vibeweaver/` state, same behavior on both. The named exports were dropped so one export = one registration on any loader variant (no double-fire).
- **Gate v2.** `ctx.tool.hook("execute.after")` for completed writes (throw = GATE-BLOCKED, warnings into the result) plus `ctx.event.subscribe` watching `session.status` idle.
- **Audit v2.** A shared audit machine keeps the latch / stale-release / report identical across versions; observation comes from `ctx.tool.hook` plus the v2 session events (`session.text.delta`, `session.message.content.updated`, `session.skill.activated`, `session.status`).
- **Dual-loader harness.** New `tests/plugin_compat_test.mjs` simulates both loader contracts (v1 `readV1Plugin` + legacy iteration, v2 `PluginModule` schema) and asserts gate/audit behavioral parity under each.

Verified: harness 30/30 after this wave; a real opencode 1.18.32 model write into a RED project is still GATE-BLOCKED; a real v2 binary (isolated home) loads both plugins with zero errors; payload byte-identical across the four copies (`diff -q`).

## 2026-09-14: wave6 — consistency fixes plus an A/B-gated root slim (−15.1%)

The user's rule for this wave: change nothing on faith — forced-injection A/B first, implement only Pareto improvements (models: qwen3.6-35B at biklimax.cn:18002 and deepseek-v4-flash). Of the WP1–WP6 plan, this wave shipped WP4 (mechanical consistency) and the WP2 root slim (a content change, so it ran the A/B gate); WP1 (hash pinning/CI), WP3 (task-level eval expansion), WP5 (`vw` CLI) and WP6 (telemetry) remain queued.

- **WP4 consistency.** `COMPLETION_GATE.md` said "all 11 covenants" (a drift left from the COV-12 introduction) — now 12, in the shipped selftest/mutation-sweep fixtures too. T6 became SKIP-on-missing-calibration: `--calib <dir>` now actually reaches the T6 guard, a calibration directory without its session file no longer crashes the suite (skip + summary count), and unparseable/non-session JSON is skipped rather than fatal.
- **WP2 root slim, A/B-gated.** `tests/w6/make_candidate.py` deterministically generates the candidate `SKILL.md` (41,554 B vs 48,955 B, −15.1%): untouched blocks copied byte-for-byte, the gate-line template and 8-column header extracted from the source, cap/recall literals asserted against it. What moved out: A4 procedural detail (full text already lives in the mandatory R1/R1b companions), the Part B/C skeletons, a core MANDATORY CHECKLIST, a tighter intro. What stayed: every §1 covenant verbatim, the Read Contract, all machine tokens.
- **The A/B (forced injection, decision rule fixed before results).** deepseek-v4-flash, 16 tasks: before 15/16 → after 15/16 (Δ0, zero timeouts). qwen3.6-35B, 8-task paired subset: 3/8 → 3/8 (Δ0, one regression offset by one gain, zero timeouts). Protocol reduction recorded as D-1 (`tests/decisions.md`): concurrency-3 queueing on the single llama.cpp slot inflated per-task wall to 792-1018 s toward the 2400 s timeout, so the qwen arm moved to a fixed paired subset at concurrency 1. Smaller bytes + non-inferior on both models → Pareto → shipped. Report: `tests/w6/AB_REPORT_wave6_2026-09-14.md`.
- **New dev-only tooling.** `tests/w6/doc_lint.mjs` (cross-file consistency: covenant counts including `scripts/`, cap literal, size budgets, dead links), `grade_w6.py`, `pareto_report.py` (reproduces the IMPLEMENT verdict including the bytes clause).
- **Two independent reviews (A4.9).** Round one: ready-with-fixes (2 Important + 5 Minor, all fixed). Scoped re-review: every finding ADDRESSED; one new Minor (`--calib` with no value crashed) fixed, plus hardening of the calibration block against non-session JSON.

Verified: dev self-test exit 0 (36 checks / 0 failures / 1 skip), mutation sweep 27/27, doc lint OK, artifact assertions 17/17; 19 files × 3 copies byte-identical (`cmp`); repo `verify_skill.py` 9 checks + unittest 13/13; per-copy self-test 36/0/1 + sweep 27/27; dsh has no contract delta (covenant text unchanged), unit 35/35.

## 2026-09-14: wave7 — a trusted-oracle and checker contract (grounded in the 15-arm wave6 spike)

The wave6 spike's fifteen eval arms showed that a deterministic loop only pays when it is fed a trusted oracle (real tests 4/4; self-written tests 1/4; generated tests 1/4 with false greens). The user asked to land all three conclusions (oracle hierarchy, checker contract + repair packet, mutation-style qualification), watch the length budget, and then run a forced-injection A/B on both models.

- **A4.8 trusted oracle** (SKILL.md binding + TESTING_PROTOCOLS canonical): ① project/external acceptance tests (or executable acceptance criteria) are the only certifying tier — greenfield must render its criteria executable; if impossible, the log records `- oracle: self-tests (weak)` and the claim is flagged; ② independently generated + qualified tests (stub-fail / gold-pass / faulty-fail) are weak evidence; ③ self-written tests are weakest. An invisible contract becomes an open question — never an invented interface.
- **Checker contract**: one deterministic entry point (`script/check.sh` / `tests/check.py` / `vw_check.py`); quote the pass line; log the output; a changed test set refuses to run (hash guard — a discipline aid, not a security boundary).
- **APPENDIX §A11** (renamed from A10 to avoid the Project Memory collision): hierarchy + qualification protocol + `vw_check.py` template (recursive `**/*_test.py` + `**/test_*.py`, vendored dirs excluded, fail-closed hash record, 900 s timeout, repair packet location+observed+expected) + `qualify_tests.py` template.
- **Mini kit rewrite**: `vibeweaver-mini/SKILL.md` (1,719 B deterministic loop + oracle/no-invent rules) + `scripts/vw_check.py` + zh/en READMEs rewritten to the wave6 measurements; committed (55c9db8) and the installed copy synced.
- **Length discipline**: SKILL 41,554 → 41,772 B (net +218 B; compensating trims in A4.6/A4.7/A4.8/A4.9) · TESTING_PROTOCOLS 46,040 → 45,977 B (−63 B) · APPENDIX 26,297 → 33,036 B (< 45 KiB).
- **Two review rounds (A4.9)**: round one ready-with-fixes (1 Critical + 4 Important: recursive-glob gap, bypassable hash guard, missing greenfield cert path, uncommitted mini with a stale README, an A/B that cannot validate the feature); after fixes the scoped re-review verdicts every finding ADDRESSED, plus persistent checker regression tests `tests/test_vw_check.py` 5/5.

Verified: self-test 36/0/1, sweep 27/27, doc lint OK, artifact assertions 18/18; 19 files × 3 copies byte-identical; repo verify_skill 9 checks + unittest 13/13; per-copy self-test/sweep green; dsh has no contract delta (unit 35/35).
A/B (forced injection; per D-2 a non-inferiority check of the SKILL.md text only): ds 16 tasks, before 13/16 → after 16/16 (Δ+3, 3-0 discordant, McNemar p=0.25; the before arm is a low draw — wave6's same-size slim scored 15/16 — so the honest read is "no regression, directionally positive"; the after arm did more verification: writes +65%, steps +18%). qwen3.6-35B 8-task subset: before 4/8 → after 3/8 (Δ−1, one flip each way, within noise, non-inferiority met).

## 2026-08-30: wave5 — a feasibility question is now a first-class route, plus one plan-writing test

Full-repo comparison against obra/superpowers (all fourteen skills, read cover to cover). The honest headline first: most of it was already here — this skill's plan format, four-phase debugging, TDD rules and spec self-review descend from superpowers' own, so the pass was mostly a coverage audit. Two things still earned their way in; eight were rejected in writing (universal approval gates, per-section design approval, subagent-per-task execution, git worktrees, branch-finishing menus, parallel fix agents, the skill-authoring guide, condition-based waiting — each conflicts with a deliberate choice here: AUTO mode, one-batched confirmation, in-session evidence loops, the baseline-commit model).

- **Spike routing (from brainstorming).** A feasibility question — "can we…?", "is it possible…?" — no longer gets force-fit into a build workflow. Its deliverable is an answer: announce a 2-3 sentence probe plan, find out as cheaply as correctness allows, report a recommendation. Anything built is labeled throwaway, and keeping it is a new request that gets its own classification and its own green-baseline check. Probe code never drifts into production ungated.
- **Task right-sizing (from writing-plans).** The plan format gains a boundary test: setup, config, scaffolding and docs fold into the task whose deliverable needs them; split only where a reviewer could meaningfully reject one task while approving its neighbor.

The spike row cost negative 35 bytes — five redundant phrases across SKILL.md paid for it (48,955 B under the 49 KB cap). Verified per copy: self-test 35/36 (the one failure is the known environmental calibration case), mutation sweep 27/27.

## 2026-08-30: wave4 — five contracts borrowed from mattpocock/skills, four rejected on the record

A read-only pass over mattpocock/skills (engineering + productivity: to-spec, code-review, grill-me, grill-with-docs, grilling, domain-modeling) asked one question: what do they enforce that this skill doesn't? Five ideas earned their way in; four were evaluated and rejected in writing (issue-tracker publishing, pathless specs, dual-axis parallel reviewers, CONTEXT.md glossaries — external dependencies, an opposite planning philosophy, or double the review cost).

What landed:

- **Test seams in the plan (from to-spec).** Every C3 task block now names where its behavior is verified: prefer existing seams, test at the highest seam that still isolates the behavior, and keep seams few — the ideal across a codebase is one, because every seam is permanent coupling between tests and internals. The planning rule the skill never had: it said what to test, never where.
- **Spec-fidelity triad in review (from code-review).** The A4.9 reviewer's Compliance dimension is no longer a free-text judgment: report requirements missing/partial, scope creep, and looks-implemented-but-wrong, each quoting the criterion line it violates.
- **A smell baseline for reviews (from code-review, Fowler's twelve).** CODING_PRINCIPLES.md gains a per-diff checklist of the classic smells, under two standing rules — a documented repo standard always overrides the baseline, and every smell is a judgement call, never a hard violation. The reviewer gets it in the dispatch package.
- **Frontier rounds for multi-question pauses (from grilling).** In GUIDED, a pause carrying several pending questions becomes one dependency-ordered round: each question numbered with its own recommended answer, questions blocked on still-open answers wait for the next round, and facts are never asked — the agent looks them up; only decisions go to the user. An empty frontier means nothing is left silently assumed. AUTO is untouched.
- **An admission test for proactive ADRs (from domain-modeling).** Record one only when the decision is hard to reverse, surprising without context, and the result of a real trade-off — all three. Mandatory Class-I ADRs are unaffected.

The price of admission was bytes: SKILL.md had 7 bytes of headroom under its 49 KB self-test cap, so the test-seam line went in byte-negative (a redundant parenthetical in the A4.9 summary paid for it, 48,990 B), and the triad's 110 bytes in TESTING_PROTOCOLS.md were compensated by three trims in the same section. Verified per copy: self-test 35/36 (the one failure is the known environmental calibration case) and mutation sweep 27/27 across all four copies.

## 2026-08-29: wave3 — let the agent actually take over, clean up the "wait for a human" points

Two awkward scenes kept coming up. First, some gates stop by design: vague requirements, design gates, baselines with old wounds — stopping is right, but every stop meant waiting for a human to type "continue", and nobody could say whether "continue" meant approval or a re-plan. Second, the rules had blind spots: if you write a library or a CLI, the gate still demands `start.sh` (what service would a library even start?); a credential the user explicitly asked for gets blocked all the same; and audit / deploy / ops work had no workflow at all — force-fitting C2 would have the agent invent an acceptance loop for a report.

This wave cleans up all three:

- **AUTO / GUIDED modes (COV-12).** AUTO is the default: instead of asking, the agent writes its judgment into `tests/decisions.md` (the options considered, the one chosen, why, when to revisit) and proceeds with the most conservative option. GUIDED is the old behavior, untouched. One thing to be clear about: modes only change whether the agent asks — the evidence gates are identical in both. Tests still run, screenshots still get captured, assert still has to exit 0, and no mode gets to call a FAIL a PASS. Production deploys, destructive ops, injection conflicts — both modes stop for those.
- **Pausing now has a protocol.** Whatever stops, leaves a line: `[PAUSED] gate=... | default-if-continue=... | state=...`. When you reply "continue", that approves the default option and the agent resumes from where `state` says — no re-deriving context, no re-asking settled questions. Post-compaction re-entry also dropped its "re-read everything" ritual down to the log tail, so long tasks stop choking on their own re-reads.
- **The gate stopped fighting project types.** Project profiles: a library or CLI declares once, and the start/stop/restart group is skipped (skipped, not weakened — what was skipped is printed as part of the gate evidence). A credential the user asked for gets an inline `vw-approved` marker plus a `- secret-approved: <path>` log line; if the machine can match them, it passes. And the gate plugin stopped scaring people with errors: writes under `tests/` and `memory/` no longer trigger GATE-BLOCKED, and the BLOCKED message now opens with "write SUCCEEDED — this is a completion gate, not an execution stop".
- **Four task types finally got their own paths.** Audits are read-only and produce a report where every finding needs a file:line and a reproduction command, with the important ones re-checked by a second subagent; the deploy action itself always needs a human, the rollback script is written first and actually drilled once; incidents gather evidence before touching anything and must leave one permanent regression case behind; CLI/library work uses command transcripts + exit codes + output diffs as evidence. The skeletons live in SKILL.md, the full text in the new `WORKFLOWS_EXTENDED.md` — the main file grew by 15 bytes.

Verified the usual way: deepseek-v4-flash with forced injection on the 16-task set scored 15/16 before vs 14/16 after — which looks like a regression until you re-run the polyglot 10 four times and average: 87.5% before vs 92.5% after. The direction flips; that single task was a coin toss. SWE-bench stayed 6/6 on both sides, and 112 runs at 16-way concurrency never stalled once. This wave also got caught by its own review process — a Critical where group 14 killed ordinary code lines that merely mentioned `vw-approved` in a comment — and only went ready after the fix. The gate gates the people who write gates, too.

## 2026-08-28: AI-native SDLC hardening — completion-gate content checks + structured review

Measured against Anthropic's AI-Native SDLC playbook (2026-08-21) and its Deputy-CISO security companion (2026-07-21), vibeweaver was strong on within-task discipline but had three real gaps: the completion gate checked *that evidence exists* but never *what the diff contains*; the A4.9 independent review had no dimension structure or nit cap; and there was no incident-postmortem / artifact-chain / agent-config-regression rule. This wave closes them, scoped for a single-user interactive skill rather than an org pipeline:

- **New assertion groups 14-16** in the canonical script. Group 14 `secret scan` walks the change-wave diff per-commit (a net range would miss intra-wave add-then-delete) plus untracked files, catching AWS keys, private-key blocks, `ghp_`/`github_pat_`/`xox*`/`sk-`(incl. `sk-proj-`/`sk-ant-`) tokens and JSON/k=v credential assignments — while exempting the *safe* reference shapes (`os.environ.get(…)`, `process.env.X`, `config.password`, `self.x`), placeholder-marked lines, and markdown (warn-only). Group 15 `test-change guard` fails the wave if a test assertion line is removed (whole-file deletion included) without a `- test-change: <path> — <reason>` log entry — an agent fixing code must not silently weaken the check on that code. Group 16 `risk-tier` makes the independent review non-skippable when the diff touches `auth`/`security`/`payment`/`billing`/`crypto`/`migration`/`permission`/`acl` code paths.
- **A4.9 review structured**: findings are dimension-tagged (`Bugs`/`Security`/`Compliance`), Minor findings are capped at five itemized, and a recurring finding now feeds back into project memory / `CLAUDE.md` so the mistake is caught at generation time.
- **Lifecycle docs**: new §A4.4.3 Artifact Chain (the chain is the audit trail — every artifact names its upstream link), APPENDIX §A9 incident-postmortem template (closes into an A4.8 regression test + memory + optional standing eval), an agent-config regression rule (editing `CLAUDE.md`/`.claude/**`/skill rules requires re-running the verification suite — steering config deserves the same regression testing as code), a cross-project ⛔-promotion channel, and a production-deploy human-confirm line.
- **A4.9-reviewed in the loop**: the independent reviewer (verdict ready-with-fixes) caught a deletion fail-open, an over-block on safe credential handling, and JSON/modern-key detection holes — all fixed with fixture-first regressions (11/11 scenarios green).
- **Benchmarked before/after**: deepseek-v4-flash, forced-injection A/B over the 16-task eval set (10 polyglot + 6 SWE-bench Lite) — pre-wave 15/16 vs post-wave **16/16**, with workflow-artifact adherence up 6/10 → 9/10 (single run, direction-only; raw data in `vibeweaver-eval/workspace/iteration-1/ab_logs/`).
- Also: SKILL.md trimmed back under the 49 KB selftest cap (50,096 → 48,978 B) with zero binding-content loss (third-copy redundancy pointer-collapsed; gate-line template byte-identical).

## 2026-08-21: session-scoped RED latch + audit delivery wave

The 08-19 auditor had a structural wart: a truncated session could leave `BLOCKING=yes` latched red for the whole project, released only at session end — and the test-dir exemption matched only top-level `tests/`, so nested `dev/tests/` golden files deadlocked too. Two live projects hit exactly this this week. This wave fixes the latch and delivers the payload to every copy:

- **Session-scoped latch.** The latch is now `{ sessionID, ts, bad }`. The latching session stays blocked (the self-correction teeth are unchanged); the first write/idle from a *different* session auto-releases the stale latch; a TTL backstop (default 24h, configurable **only** in the global `~/.config/opencode/vibeweaver/audit.json` — project-local copies are deliberately ignored, so the audited agent can never weaken its own auditor) catches a parked same-session latch. Legacy boolean state from pre-scoping versions self-heals on first contact, and every release is journaled to `.vibeweaver/audit-state.json` and surfaced in the audit report — a cleared latch is always traceable.
- **Nested test-dir exemption.** Any `test`/`tests` path segment under the project root stays writable while RED, so evidence fixes can never be deadlocked.
- **Selftest grew 28 → 36 checks** (cross-session release, nested tests, TTL backstop, release journaling, legacy self-heal); the 27-case mutation sweep is unchanged. An independent review of this wave caught (and the suite now pins) a journal-labeling defect T20 exposed on first run: legacy latches were journaled as `stale-session` instead of `legacy-state`.
- **Delivery.** The 17-file payload is now byte-identical across all four copies (system install / dev tree / open-source snapshot / this repo), `install.sh`/`install.bat` ship both plugins, and `verify_skill.py` syntax-checks all five payload JS files.

## 2026-08-19: progressive-disclosure restructure + mechanical audit

**Why (an opencode limitation, not a skill rule):** opencode loads a skill by
injecting the whole `SKILL.md` body as one tool output, and the client
truncates tool outputs at ~51,200 bytes (50 KB) — measured in this build:
reading the old 79,554-byte file cut the output at line 875 (51,080 bytes,
`Output capped at 50 KB`). The model activated the skill holding only the
first half of its contract, and honestly announced
`The skill output is truncated. Let me note the key points:` — §A5.1,
Part B/C workflows, the MANDATORY CHECKLIST and the reference index never
made it into context.

**The fix:** progressive disclosure (Anthropic's skill-authoring spec; the
SkillJuror study shows splitting material into referenced files raises the
resources the agent actually engages with ~3x and task success by +4.1%):

- `SKILL.md` shrunk 79.5 KB → 48.9 KB (814 lines) and is now the binding
  contract + router: the 11 covenants, §2 ZERO, §3, the gate-line / 8-column
  table specs and a core checklist stay inline; the full protocol text moved
  verbatim into companions (`TESTING_PROTOCOLS.md`, new `COMPLETION_GATE.md`,
  `REFERENCE.md`, `ENGINEERING_STD.md` — every file ≤ 45 KB so one Read
  returns it untruncated). Zero content lost: 54 headings / 47 long protocol
  lines / 31 binding literal tokens all verified present.
- A **Read Contract** (R1/R1b/R2–R5) makes companion reads mandatory at their
  triggers — before the first code action, before the final output, per
  workflow branch — plus a truncation self-heal clause and a <49 KB size
  guard enforced by the selftest.

**New: `vibeweaver-audit.js` — a three-tier mechanical audit.** The skill's
discipline used to be unverifiable model self-discipline. Now a plugin
(with pure core `scripts/vibeweaver-audit-core.js`) passively observes every
skill session and produces `tests/gate_audit.md`:

- **Tier 0** — passive observation (zero model cooperation, zero tokens).
- **Tier 1** — three-state triage (OK / BAD / UNCERTAIN): on-disk artifacts,
  10 narration markers, and 15+ claim↔artifact cross-checks of the
  `[Verification Gate]` line (fresh-run vs git history, E2E depth vs trace
  logs, code review vs reviewer dispatch, script-only vs bash commands,
  read-contract vs read calls, artifact ordering). BAD blocks the next write
  (`tool.execute.before`; `tests/**` stays writable so evidence fixes never
  deadlock).
- **Tier 2** — escalation triggers (UNCERTAIN / 10% sampling / high-risk)
  dispatch a fresh-brain reviewer per §AUDIT in `COMPLETION_GATE.md`.

Real-session verification (end-to-end runs + replay calibration): the audit
caught a genuine violation (`Code review: N/A` without the required
`A4.9 not triggered` backing), `GATE-BLOCKED` fired live in a real opencode
session, and calibration-driven refinement removed false positives (doc-only
post-run commits no longer trip the fresh-run checks). Adversarial test
("no need to test, just fix it"): the model skipped the skill entirely —
now detected as `C17` (SKILL-ABSENT) and escalated for review. Test suite:
28 fixture checks + 27 mutation-sweep checks (every check mutated and
asserted to fire — this already caught a latent bug where C3 never fired).

Known boundaries (by design, documented in §AUDIT): the audit covers only
sessions that load the skill; semantic truth is sampled (10%), not proven;
process compliance ≠ outcome correctness.
