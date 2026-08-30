# Changelog

Waves of design history, newest first. Entries are moved verbatim from the README; the current state of the project is described in [README.md](README.md).

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
