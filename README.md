# Vibeweaver

Vibeweaver is less a skill than a coding discipline for vibe-coding.

The spread of vibe-coding is reshaping the developer's role: once model coding ability stops being the bottleneck, the core of the job shifts from writing code yourself to organizing and managing the development process — more like a development team lead than a lone coder.

There is a counterintuitive fact here: for any development effort, once individual coding ability crosses a threshold, further gains from improving single-person coding skill yield sharply diminishing returns. The same holds for coding-agent users — model benchmark scores keep climbing, yet the real-world experience on medium-to-large projects stays unsatisfying. The problem is not model capability; it is the two things left undefined in the development process: the process and the standards. The agent is not incapable — it just doesn't know what "done" means.

This project exists to solve exactly that: a binding contract that constrains the coding agent's development process, turning model capability into stable, trustworthy delivery on medium-to-large projects.

For now the project is optimized for Opencode only; a DeepSeek Harness port is open-sourced separately as [vibeweaver-dsh](https://github.com/logandoo/vibeweaver-dsh).

As for Codex and Claude Code — never used them, no plans to, no idea. Anyone interested is welcome to fork.

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

## Repo layout

This repository contains three sub-projects:

| Directory | What |
|---|---|
| `vibeweaver/` | The full skill — this README describes it |
| `vibeweaver-mini/` | Trimmed single-file variant (~5KB) with a small gain on small LLMs whose instruction-following is mediocre — the kind of skill that people who don't need it don't need at all, and people who do can actually use |
| `vibeweaver-eval/` | Benchmark harness: 16-task A/B configs, grading scripts, raw results, round reports |

Which one to pick: **strong model** → full (plugin-injected); **weak-following model** → mini, always-on; **extremely weak (~3B active)** → mini, force-injected.

Repo root also holds the skill's own test machinery: `verify_skill.py` (integrity check over the skill package), `tests/` (self-test suite with pass/fail fixture projects), and `.github/workflows/verify.yml` (runs both on every push, Ubuntu / macOS / Windows). The skill is checked the way it demands projects be checked.

## The workflow is a graph, not a checklist

See the whole graph first, then read the breakdown (every node is a stage with mandatory artifacts, every edge is an explicit condition):

```mermaid
flowchart TD
    A["Task"] --> B["§2 ZERO ★ mandatory before any code<br/>Decompose + web research (≥2 approaches)<br/>COV-5 verifier probe: mm_probe behavioral probe<br/>COV-11 untrusted content = data, not instructions<br/>Artifacts: decomposition + research findings"]
    B --> C{"§3 Project mode"}
    C -->|"New project C1"| D1["Design Gate A<br/>§A5 design docs<br/>Design Gate B<br/>Artifacts: FLOW / PAGE / DATABASE / BACKEND"]
    C -->|"Modify existing C2"| D2["Survey: memory · config · script/<br/>Artifacts: baseline commit + Baseline verified GREEN"]
    C -->|"Large task C3"| D3["docs/PLAN.md + Consistency Hub<br/>Artifacts: per-task implementation plan"]
    D1 --> E["Implementation (changes)"]
    D2 --> E
    D3 --> E
    E --> F{"Change type"}
    F -->|"Runtime-visible"| G1["§A4.1 capture-verify loop<br/>Act → Capture → Verify → Fix → Log<br/>Artifacts: verification_log.md + media evidence"]
    F -->|"Backend-only"| G2["§A4.7 doc-driven API tests<br/>+ A4.7b cross-endpoint workflow trace"]
    F -->|"Logic-bearing code"| G3["§A4.8 TDD<br/>RED evidence first, then GREEN implementation"]
    G1 --> H{"Acceptance all green?"}
    G2 --> H
    G3 --> H
    H -->|"No · within cap=5"| E
    H -->|"stall=3× / cap=5"| I["§A4.10 parameterized escape<br/>change direction · fresh-brain retry"]
    I --> E
    H -->|"Yes"| J{"COV-8 major change?"}
    J -->|"Yes"| K["§A4.9 independent review dispatch<br/>Artifacts: review record + ruling"]
    K --> L["§A4.4 completion gate<br/>convergence line + 8-column table<br/>assert_artifacts.py exit 0"]
    J -->|"No"| L
    L --> M["Memory Gate<br/>A7.9 memory write + A7.10 passed"]
    M --> N{"Plugin audit Tier 0/1/2"}
    N -->|"BAD → GATE-BLOCKED / RED latch"| E
    N -->|"OK"| O["Delivered"]
```

- **Nodes = stages with mandatory artifacts.** ZERO (decompose + research) → project-mode detection → design gates → implementation → verification loop → independent review dispatch → completion table. A stage is not "done" because the model said so — it is done when its required outputs actually exist on disk.
- **Edges = explicit conditions, not model mood.** New project forks to one workflow, modify-existing to another; the verifier capability probe branches the capture and grading set into four modality modes; backend-only changes swap the browser loop for the doc-driven API test loop.
- **Cycles are bounded by construction.** Every loop shares one termination contract — `cap=5` iterations per sub-problem, `stall=3×` — and the stop condition is written down by the user *first*, so the graph is guaranteed to have an exit.
- **Traversal is soft, gating is hard.** The model walks the graph by interpreting prose — that part stays soft. But each guard condition is machine-checkable: literal tokens in the final answer, on-disk evidence byte-checked by `tests/assert_artifacts.py`, and (with the plugin) a tool-level hook that blocks the agent's own writes while any gate is red.

That is what makes it a state machine instead of a sobriety pact: the current stage is always verifiable from the files, and no transition may be declared without its evidence. The stop hook below is the same idea one layer down — the graph's final guard, executed by opencode itself instead of the model.

## What it actually does

Vibeweaver is a contract, not a methodology. It takes the single worst habit of coding agents — saying "done" without proof — and makes it structurally impossible to get away with:

- **NO TEST, NO DONE** — every code change must be followed by executed tests with on-disk evidence (log files, screenshots, operation video, page audio). "It builds" is not evidence.
- **Test-first, always** — logic-bearing code is written RED→GREEN: write the failing test first, *watch it fail* (the output gets pasted into `tests/verification_log.md`), then write the minimal code to make it pass. A test that passes on the first run proves nothing — it might be testing the wrong thing entirely. Regression tests must complete the full revert-and-fail cycle before they count.
- **API-doc-driven backend tests** — for backend-only changes, the loop is: update the API doc → audit doc↔code consistency exactly once → write test cases *from the doc, not from the implementation* → run the httpx test→fix→test loop until everything passes. Cross-endpoint changes additionally require real-HTTP workflow scenarios with on-disk traces (`tests/workflows/*.trace.log`); direct service-layer calls are not E2E and don't count.
- **Self-starting verification loop** — the moment a change touches runtime behavior, the agent enters `Act → Capture → Verify → Fix → Log` on its own. Screenshots are graded by the verifier selected at task start by the three-stage probe (see the mm-sensor hookup below): model-native self-reads must follow the §A4.1.1 protocol, and with [mm-sensor](https://github.com/logandoo/mm-sensor) installed the maker/checker split means the model doesn't grade its own homework; video/audio are included when the verifier model supports them, and the mode is decided by a capability probe.
- **Script-only lifecycle** — frontend builds and service start/stop/restart go through `script/` scripts. Raw `npm run build`, `vite`, `npm start`, `uvicorn` are forbidden. Stop scripts must use the `.pid`-file pattern — `pkill -f "uvicorn"` on a shared box kills your coworker's service.
- **Research before code** — the first action on any task is decomposing the problem (stop and ask when anything is unclear — one question at a time, no guessing) and searching the web (exa MCP + Context7) for existing solutions, evaluating at least two approaches before writing anything. This step is mandatory unless there's no internet or the fix is a trivial typo/config change. The philosophy behind it: **there is nothing new under the sun**. Your problem has almost certainly been solved before; if a genuine search turns up no precedent, the thing is too novel to be our job.
- **Project memory** — arguably the most important piece, because opencode has *no native memory system*: every session starts with a fresh brain. vibeweaver builds one from files and rules — an index + topic files, trust tiers (⛔ Forbidden / ❌ Failed / ✅ Verified / ⏳ Unverified), and a fix state machine. Full mechanism below.
- **Bounded loops** — every verification loop is capped: `cap=5` iterations per sub-problem, `stall=3×` (same criterion failing three times in a row means stop, change direction, and record the dead end).

The full package also covers new-project scaffolding (design docs first: FLOW / PAGE / DATABASE / BACKEND), config management, acceptance checklists, and an 8-column completion table.

## The stop hook: when words fail, plug in a gate

Prompts are just suggestions. A model that just got told "NO TEST, NO DONE" will still, occasionally, declare done without a single test. To solve this, I built a stop-hook plugin.

The companion plugin `vibeweaver-gate` enforces the evidence rules **mechanically**, at the tool level:

- It hooks opencode's `tool.execute.after` for every `write`/`edit`. If the project is vibeweaver-active (it has a `tests/verification_log.md`), the plugin runs the project's `tests/assert_artifacts.py` (trying all four flag combos).
- If verification evidence is missing or falsified — no iteration entries in the log, no `> cap=5  stall=3×` first line in `acceptance.md`, cited screenshots/media missing or zero bytes — the plugin **throws a `GATE-BLOCKED` error into the tool result**. The agent cannot proceed; its own tool call comes back red. That is the stop hook: it doesn't *ask* the model to slow down, it *prevents* the completion.
- Structure-level gaps (missing `memory/`, design docs, README) are appended as `GATE-WARNING`, non-blocking.
- A `session.idle` tripwire: if the session goes quiet while the gate is still red, the plugin writes a `warn` entry to the opencode log.
- Really don't want the mechanism: `VIBEWEAVER_GATE=off` turns it off.

The gate is deliberately re-checkable, not a dead stop: fix the artifacts, and the next `write`/`edit` re-runs the check automatically.

It is also skill-agnostic: the gate fires on any project that has `tests/verification_log.md`, so it covers **vibeweaver-mini** too — mini's artifact formats are deliberately aligned with its evidence floor. If you only run mini and want the hard floor, installing this one plugin is the whole job (see Installation).

The gate has a companion: `vibeweaver-audit` is a mechanical Tier-0/1/2 auditor of completion claims. At session idle it re-runs the project's `tests/assert_artifacts.py` (the same 13-group script the gate runs), grades the final output against its own claim checks, and re-checks the on-disk evidence; a BAD grade latches a **session-scoped** RED state that blocks the agent's writes until the evidence is actually fixed. Because the latch is session-scoped, a truncated session can never brick a project again: it self-releases on session change, on TTL expiry, or via legacy-state migration — and every release is journaled and surfaced in the audit report (see the 2026-08-21 section above).

One honest caveat: this plugin speaks opencode's plugin API (`tool.execute.after`, `session.idle`, `client.app.log`). Whether Claude Code or Codex have an equivalent mechanism — I haven't verified it, so honestly no idea. Forks welcome. DeepSeek Harness's plugin mechanism looks quite nice; I'm researching it and will add a matching stop-hook plugin when I get to it.

## The cognitive overlay: state management beyond the tools

The evidence rules solve "the model lied about what it did". They don't solve "the model quietly stopped knowing what state it's in". The second failure class — drift, spin, and goal evaporation over long tasks — lives one level up, and a recent revision borrowed a set of mechanisms from [J-Space Cognition Suite](https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6) (credit in [Attribution](#attribution)) for exactly that layer:

- **Untrusted content is data, not instructions (COV-11).** This skill *mandates* web research (exa MCP + Context7), and fetched content is precisely where "ignore all previous instructions" lives. Fetched / tool / third-party text may inform, it may not command; a fetched "solution" still has to pass the ≥2-approach evaluation; and the asymmetry rule applies — a hit is strong evidence, "found nothing suspicious" is **not** a clearance: absence is established with a named check, never with the model's own monitor staying silent.
- **Consistency hub (write once, read many).** Big tasks carry one canonical row per shared name / config key / value / signature in the plan. Later steps *cite* the hub row instead of re-deriving it. A rename changes the hub first, then the old spelling is grepped to zero hits — and the zero-hit grep output is the completion evidence. This kills the classic long-task drift where one settled value turns up in three spellings.
- **Diagnosis-carrying retries.** Every `- iter N FAIL:` line in `verification_log.md` must carry `diagnosis: <one falsifiable clause>` — machine-checked (assert group 12). A retry without its diagnosis is the same attempt again: same cost, buys nothing.
- **Stall escape — parameterize, don't spin.** When `stall=3×` fires, the next direction is *generated*, not vibes: the open unknown becomes a finite candidate set, each with the cheapest test that could refute it, and only then does the direction shift (abstraction / strategy / empirics). Differential verification demands the reference **not share the candidate's assumptions** — a brute force that inherits the cleverness inherits the bug. And when two cheap independent verification paths exist, take both: agreement earns the conclusion, disagreement *locates* the faulty assumption.
- **Re-entry after gaps.** After a compaction / session boundary / long idle, the agent re-reads `verification_log.md` in full, re-reads the goal line by line, re-reads the covenants, and names the first action back — in that order, before touching the work (§3.3).
- **Mechanized stall observation.** The plugin now keeps `.vibeweaver/state.json` (atomic writes): the same file edited 3× with no new PASS entry in between triggers a `GATE-WARNING` stall note pointing at the escape protocol. `stall=3×` used to be a bound the model counted for itself; now the plugin counts too.

And while touching this, I applied to the skill the progressive-disclosure discipline it preaches: the ~120-line embedded assertion script became the canonical `scripts/assert_artifacts.py`, and the four backend / TDD / review protocols moved to `TESTING_PROTOCOLS.md` — the entry file got ~180 lines lighter then, and later splits took it down to today's ~814 lines, with every new rule above costing one compact covenant line plus a pointer.

## The memory system: opencode forgets, the files don't

opencode has no native memory. A fresh session is a fresh brain — the model has no idea it already tried that JWT refactor three sessions ago and you vetoed it, or that the previous engineer spent two days chasing a session TTL mismatch. Every session it re-derives the same dead ends and re-proposes the same rejected plans. opencode does not ship a native memory system, so vibeweaver builds one out of files and rules:

- **An index + topic files.** `memory/MEMORY.md` is a table of contents, not the memory itself (load cap: 200 lines / 25KB). Each memory lives in its own `memory/*.md` file with YAML frontmatter: type (`user` / `feedback` / `project` / `reference` / `fix`), status, the commit hash it describes, and the file references it cites.
- **Selective recall, not full recall.** At session start the index loads first; then the agent greps the topic files for keywords from your request and loads only the top 3-5 most relevant entries. Memory is consulted before code is touched — but never trusted blindly: every file/line citation is verified against the current code, and entries older than 14 days get a "this may be stale" warning. Even a ✅ Verified entry self-ages: if it hasn't been re-validated in 14 days or its cited code changed, it's demoted back to ⏳ until re-verified.
- **Trust tiers, because not all memories are facts.** ⛔ Forbidden = methods proven to fail; never retry. ✅ Verified = confirmed by the user. ⏳ Unverified = the agent's own fix that passed tests but nobody confirmed. ❌ Failed = a ⏳ that later failed; it carries the same "don't retry" weight as ⛔.
- **A state machine for fixes.** Agent fixes something and tests pass → written as ⏳ (never ✅ — only the user can verify). You report the same symptom next session → the entry is auto-demoted to ❌ and the agent must try a genuinely different direction. You confirm it works → promoted to ✅. Three or more failures on the same problem → everything escalates into a ⛔ Forbidden file.
- **Written every session, gated at the end.** Memory writing is a non-negotiable session-end step, checked by a Final Memory Gate before the completion table. Fix entries must carry the commit hash of the change they describe, plus the failed approaches and rejected alternatives that were considered — so a future session can look at the memory, look at the exact code state, and skip the dead end entirely.
- **Two scopes, merged.** User-global memory (`~/.config/opencode/vibeweaver/memory/`) holds your cross-project preferences and conventions; project-local memory holds everything project-specific. Both load at session start; project-local wins on conflict.
- **Housekeeping.** The index has a consolidation trigger (150 lines / 20KB, or >15 topic files): ⛔ / ✅ / user / feedback entries survive consolidation, stale ⏳ entries get pruned, and a `.session-scratchpad.md` tracks mid-session backtracking before being deleted when the real memories are written.

In short: it's a poor man's persistent memory — filesystem plus rules doing the job of a memory layer, so the model doesn't have to relearn your project from zero every session.

## The mm-sensor hookup: partner, not rival

In general, [mm-sensor](https://github.com/logandoo/mm-sensor) and vibeweaver should be used together — the skill has built-in detection and invocation for it. Sure, if you really don't want it, no problem, though results take a small hit, since the two skills are designed as a pair. The division of labor:

- **A three-stage verifier tree (COV-5, behavioral probe, not self-declaration).** At task start vibeweaver first runs its self-multimodality probe `scripts/mm_probe.py`: it generates a probe image carrying a token and a color (`tests/probe_vision.png`), the model reads it via the Read tool and reports the token + color it actually sees, then `--check` verifies — **PASS** → announce `Verifier: model-native [image]`; the model grades its own screenshots under the §A4.1.1 Visual Verification Protocol (observation-first · per-criterion verdicts with quoted evidence · DOM/log cross-check · UNCERTAIN=FAIL). **FAIL** with mm-sensor installed → announce `Verifier: mm-sensor [video+audio|video|image]` for independent grading. Neither → `Verifier: direct read` (DOM/log inspection is the primary evidence).
- **vibeweaver makes the evidence exist.** Its rules force the agent to actually run the app, drive it with Playwright, and leave screenshots / operation video / page audio on disk.
- **mm-sensor grades it independently.** The maker/checker split: while mm-sensor is the verifier, the model that wrote the code is forbidden from grading its own screenshots. vibeweaver alone falls back to direct-read self-grading when the model fails its own probe — weaker, and it demands extra cross-checks against DOM and logs.
- **A capability probe decides how much evidence gets captured.** At task start, vibeweaver runs `vision.py --probe` to ask the model behind mm-sensor what it can actually perceive. Full-modal models get the [video+audio] mode: Playwright records the whole flow as video, captures in-page audio via Web Audio, plus a terminal-state screenshot. Image-only models degrade to [video] or [image] mode. The mode is fixed per task, and every captured file is graded with `vision.py --detail high`.
- **If the environment is lacking, it degrades gracefully.** No ffmpeg → grade the raw webm via frame-sampling. Model can't hear audio → mm-sensor reports the skip explicitly and the loop continues on video + screenshots. Audio is an added signal, never a criterion by itself.

In one line: vibeweaver decides *what must be captured*; the verifier (model-native or mm-sensor) decides *what the evidence actually says*.

## Does it actually work? We ran the numbers so you don't have to

Every table below uses the same three setup modes:

- **baseline** — no skill at all.
- **available** — the skill is installed and listed in `available_skills`; the model decides whether to load it. Whether it ever does is the **trigger rate**, listed per arm.
- **force-injected** — the skill's full text is pasted into the system prompt; the model has no choice.

### How the eval is designed

The numbers below come from one fixed, reproducible harness (`vibeweaver-eval`), designed to make rounds comparable and hard to game:

- **A fixed task set** — the same 16 tasks every round: 10 Aider polyglot + 6 SWE-bench Lite real-repo issues. Same prompts, same scoring, round after round.
- **Hidden-test grading** — solutions are graded by tests the agent never sees: Exercism-style for polyglot, FAIL_TO_PASS + P2P regression guards for SWE-bench.
- **Isolated arms** — every arm runs in its own XDG config directory; the only difference between arms is the skill (or its absence). The no-skill arm is the **control group**; the rest are treatment arms.
- **Gold-validated before admission** — every SWE-bench instance must fail on base and pass on gold before it's allowed into the set.
- **Headless and scripted** — `opencode run --auto`, everything published: harness, configs, gold checks, raw runs, grading scripts.

### Before / after: qwen3.6-35b-a3b (the weakest model yet)

34.6B MoE with ~3B active params, GGUF Q5 quantized, llama.cpp. This is where the size→trigger rule breaks at the bottom:

| Arm | Pass rate (16 tasks) | Trigger rate |
|---|---|---|
| No skill (baseline) | 6/16 (37.5%) | — |
| mini, available | 6/16 (37.5%) | 0/10 |
| Full skill, available | 7/16 (43.8%) | 0/10 |
| **mini, force-injected** | **7/16 (43.8%)** | — |
| Full skill, force-injected | 5/16 (31.3%) | — |

- **Below a capability threshold the model loads nothing** — 0/10 for both sizes.
- **Force-injected mini gains nothing either** — 7/16 ≈ baseline.
- **Force-injected full skill is actively worse**: 5/16, SWE-bench down to 1/6 with five "no diff produced" — 71KB of rules floods a 3B-active context and the model gives up.

### Before / after: qwen3.6-27B

| Arm | Pass rate (16 tasks) | Trigger rate |
|---|---|---|
| No skill (baseline) | 7/16 (44%) | — |
| Full skill (71KB), available | 6/16 (38%) | 0/16 |
| Full skill (improved description), available | 9/16 (56%) | 2/16 |
| Full skill, force-injected | 9/16 (56%) | — |
| **mini, available** | **10/16 (62.5%)** | **10/16** |

This is the round that made the mini variant exist:

- **mini beat even the force-injected full version** (62.5% vs 56%) purely because it got *loaded*: a short rulebook the model will read and remember beats a 71KB masterpiece it never opens.
- **Size drives triggering.** 71KB → 0/16, mini → 10/16.

### Before / after: deepseek-v4-flash-0731

| Arm | Pass rate (16 tasks) | Trigger rate |
|---|---|---|
| No skill (baseline) | 11/16 (68.8%) | — |
| Full skill, available | 11/16 (68.8%) | 0/16 |
| mini, available | 11/16 (68.8%) | 12/16 |
| **Full skill, force-injected** | **14/16 (87.5%)** | — |

A strong model already has the discipline natively, so mini becomes completely useless starting at this tier. The full version's gain starts to show, but the model will never load it on its own (0/16 available) — it needs **force-injection** into the context. The edge lives in polyglot: 8/10 vs 5/10.

### Before / after: qwen3.8-27B

| Arm | Pass rate (16 tasks) | Trigger rate |
|---|---|---|
| No skill (baseline) | 13/16 (81%) | — |
| mini, available | 13/16 (81%) | 10/10 (polyglot) |
| Full skill, available | 15/16 (94%) | 12/16 |
| **Full skill, force-injected** | **16/16 (100%)** | — |

Two findings: the bare model improved on its own (44% → 81% vs qwen3.6), and 3.8-27B's willingness to load skills grew a lot — qwen3.8 loaded the full skill on its own 12/16 times, producing the best score ever recorded on this benchmark. Force-injecting the full skill then completed the sweep: **16/16, the first perfect round in the eval's history** (polyglot 10/10 with every task at full marks, SWE-bench 6/6). But the perfection is pricey — 1820s/task avg vs 518s self-triggered (+251%), which is exactly what "the full verification loop, every single time" costs. mini is worthless here too, same as on deepseek-v4-flash-0731.

### The four models, one table

| | qwen3.6-35b-a3b | qwen3.6-27B | deepseek-v4-flash-0731 | qwen3.8-27B |
|---|---|---|---|---|
| Bare model | 6/16 (37.5%) | 7/16 (44%) | 11/16 (69%) | 13/16 (81%) |
| Full skill, available | 7/16 (43.8%) | 9/16 (56%)† | 11/16 (69%) | 15/16 (94%) |
| Full skill, force-injected | 5/16 (31.3%) | 9/16 (56%) | 14/16 (87.5%) | **16/16 (100%)** |
| mini, available | 6/16 (37.5%) | 8–10/16 (best 62.5%) | 13/16 (81%)* | 13/16 (81%) |
| mini, force-injected | 7/16 (43.8%) | 8/16 (50%) | — | — |
| Best config | mini, force-injected | mini, available | full, force-injected | **full, force-injected** |

\* deepseek's mini: first run 11/16, clean-environment rerun 13/16 — both within noise of its 11/16 baseline.
† qwen3.6's full skill: the plain version scored 6/16 (never loaded); 9/16 is the improved-description variant.

### Well, To be Honest

- Being TDD-driven, this skill **burns tokens like crazy**. If you have a real problem you want solved, it's still worth trying. If you're just playing with vibe-coding, it matters much less.
- **Model generations still matter more than the skill itself** — qwen3.6 → qwen3.8 lifted the bare model from 44% to 81% before any skill was involved; and the skill's role flips with the model — it *supplies* the missing discipline on qwen3.6 (mini wins), *enforces* execution discipline on qwen3.8 (force-injection hits a perfect 16/16), only works force-injected on deepseek, and only works as force-injected mini on the 35b-a3b class.
- **16 tasks is a small sample.** Each task is substantial, but I can't rule out a task "happening to be solvable" or "happening to be unsolvable" — landing right on a model's strength or weakness.
- **Each arm ran only once per round.** A qwen3.8 arm takes 40-60 minutes; the llama.cpp-hosted 35b-a3b takes 1-3 hours; force-injected arms take several times longer. More rounds would be proper — models are stochastic — but one round already takes too long, and I don't have the patience for more.
- **mini is a rather niche skill — but for exactly the people who need it, it happens to be exactly useful.** On qwen3.8 and 35b-a3b mini gains nothing — the most interesting finding: for models with very strong or very weak instruction-following, mini doesn't matter much; but for a model like qwen3.6-27B — decent at coding but poor at long-context instruction-following — it's a good choice.

## Installation

```bash
git clone https://github.com/logandoo/vibeweaver && cp -r vibeweaver/vibeweaver ~/.config/opencode/skills/vibeweaver
# or, from a local copy of this repo:
./install.sh    # Linux/macOS
install.bat     # Windows
```

Restart opencode. The skill auto-triggers when you ask to build, modify, debug, or deploy anything. To also get the enforcement plugins (stop hook + completion auditor — `install.sh`/`install.bat` already do both):

```bash
cp ~/.config/opencode/skills/vibeweaver/vibeweaver-gate.js ~/.config/opencode/plugins/
cp ~/.config/opencode/skills/vibeweaver/vibeweaver-audit.js ~/.config/opencode/plugins/
```

(Or just keep it simple and only use the skill without the gate — the gate is the enforcement layer, the skill is the instruction layer, and both work independently.)

Optional — but Playwright and [mm-sensor](https://github.com/logandoo/mm-sensor) are the two we'd actually insist on: they're a designed pair, and the verification loop gets meaningfully weaker without them (self-grading instead of independent grading). Also useful: ffmpeg (video transcode), exa MCP + Context7 (research). None are required for the skill to function; they upgrade how much of the evidence gets collected and how independently it gets checked.

## Stack compatibility

vibeweaver is stack-agnostic. It never assumes a language, framework, or database:

- **New projects**: tell it the stack, or it will ask once before scaffolding. Then it generates design docs, `config.toml` layout, `script/` lifecycle scripts, and dependency manifests around your stack.
- **Existing projects**: it reads what's already there — memory, config, scripts, structure — and adapts every rule to match. It will not "helpfully" introduce React into your Vue project.
- **Windows**: yes, it knows. `install.bat` and `script/windows/` exist.

### The default stack, and how to change it

New-project scaffolding has a built-in default (SKILL.md, Part B1): **FastAPI + React + Vite + PostgreSQL** — Python/FastAPI backend with OAuth2 auth on every endpoint, frontend mounted at `/static` with history-routing fallback, React + Vite responsive frontend (desktop / tablet / mobile). When you say "new project" and nothing else, this is what comes out.

Two ways to get a different stack:

1. **Per project — don't touch the skill at all.** Just declare your stack when asking ("new Go + Vue + MySQL project") and the skill scaffolds around that. The default only wins when you don't pick anything. The core rules (Part A) are universal; the skill reads your declared stack, fills in the real build commands, and adapts the `[database]` config block to your actual database.
2. **Permanently — edit the skill's Part B.** If you want a *different default* baked in, edit the stack description in `SKILL.md` §B1 (the "Default New Project Stack" section), and mirror the change in `APPENDIX.md`:
   - §A5 — the `config.toml` full template (adapt to your backend / database)
   - §A6 — the script templates (`script/linux/project_build.sh`, `start.sh`, `stop.sh`, `restart.sh` + the Windows `.bat` twins) so they produce your stack's real build/start/stop commands instead of the npm/uvicorn ones
   
   Rule of thumb when adapting (Part B2): apply all Part A principles (they're universal), swap the script templates for your build tooling, adjust the config template to your database, and keep the `script/` directory discipline — the mechanics matter more than the commands inside.

## vibeweaver vs superpowers

[Superpowers](https://github.com/obra/superpowers) is the closest well-known relative: a skills-based development methodology for coding agents. Both are MIT, both are skill ecosystems, but they bet on different things:

| Dimension | vibeweaver | superpowers |
|---|---|---|
| Workflow | Decompose → **web research (near-mandatory)** → design docs / plan (when scoped) → test-first → evidence gates | Brainstorm → spec → detailed plan → subagent execution |
| Core bet | **Research-first + evidence-gated completion** — near-mandatory web search before code (nothing new under the sun), tests must run and leave artifacts, enforced by a tool-level plugin gate | **Planning-first process** — brainstorm → spec → detailed plan → subagent execution |
| Verification | Self-starting capture loop graded by an independent multimodal verifier; evidence is byte-checked by `assert_artifacts.py` | Manual/self-review before declaring done |
| Project memory | Built-in memory subsystem with trust tiers | Not a core feature |
| Model requirements | Engineered for small models too (mini variant, benchmarked down to ~3B-active) | Assumes strong models — long specs, subagent delegation |
| Harness support | opencode (with a plugin gate; Claude Code / Codex unknown, forks welcome; DeepSeek harness under research) | Claude Code, Codex, Cursor, Gemini CLI, Copilot, opencode, etc. |
| Public benchmark | Published A/B vs no-skill baseline, multiple models | None |

Short version: both start the same way — decompose, then plan. The weight differs: superpowers invests in the plan; vibeweaver makes the research step near-mandatory (nothing new under the sun) and gates completion on evidence. They're not enemies — you could run both, if you have that kind of token budget. Honestly, I don't know whether running both makes the agent's context explode and it just gives up — untested, feedback welcome.

## Files

| File | Purpose |
|---|---|
| `SKILL.md` | The binding operational contract + router (815 lines, <49 KB — size-guarded) |
| `COMPLETION_GATE.md` | Completion output spec · artifact gates · §AUDIT audit protocol · pre-output checklist |
| `CODING_PRINCIPLES.md` | The four iron rules + Karpathy's six disciplines |
| `ENGINEERING_STD.md` | Detailed engineering standards |
| `REFERENCE.md` / `APPENDIX.md` | Workflow reference / executable templates (incl. §A9 postmortem) |
| `TESTING_PROTOCOLS.md` | §A4.1 loop + §A4.6 debugging + canonical §A4.7–§A4.10 protocols |
| `MEMORY_RULES.md` / `MEMORY_TEMPLATES.md` | Project memory subsystem |
| `scripts/assert_artifacts.py` | The canonical 16-group assertion script projects copy into `tests/` (incl. secret scan / test-change guard / risk-tier) |
| `scripts/mm_probe.py` | Behavioral self-multimodality probe (verifier selection, COV-5) |
| `vibeweaver-gate.js` | The stop-hook plugin (opencode) + mechanized stall observer |
| `vibeweaver-audit.js` | Three-tier mechanical auditor (Tier 0/1/2) — session-scoped RED latch, journaled auto-release, stale-latch healing |
| `scripts/vibeweaver-audit-core.js` | Pure triage core (headless-testable) |
| `scripts/audit_selftest.mjs` / `scripts/mutation_sweep.mjs` | 36 fixture checks / 27 mutation checks — including the latch-release regressions |
| `install.sh` / `install.bat` | Installers (skill files + both plugins) |

## Related

- [mm-sensor](https://github.com/logandoo/mm-sensor) — independent media verifier (image / video / audio)
- [J-Space Cognition Suite V3.6](https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6) — the inference-time cognitive-control suite whose mechanisms the cognitive overlay adapts (see Attribution)

## Attribution

`CODING_PRINCIPLES.md` is adapted (near-verbatim) from [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) ("Karpathy-Inspired Claude Code Guidelines", MIT License, by multica-ai / forrestchang), itself derived from [Andrej Karpathy's observations](https://x.com/karpathy) on how LLMs fail at coding.

The **cognitive overlay** mechanisms descend from [J-Space Cognition Suite V3.6](https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6) by [Tiger3807861189](https://github.com/Tiger3807861189): the claim-without-scope lint (assert group 13) is modeled on their `ship` check, and stall parameterization, differential testing against an independent reference, the two-route reconcile, the write-once consistency hub, the asymmetry rule for untrusted input, the post-gap re-entry protocol, and the mechanized stall observation in the plugin all trace back to that project's modules and controller. Its single-entry + on-demand-module architecture also informed this skill's progressive-disclosure layout. The credit is at the idea level — every implementation here is our own.

Benchmark methodology and raw data: `vibeweaver-eval`.

## License

MIT — go nuts, fork it, break it, tell us what broke.
