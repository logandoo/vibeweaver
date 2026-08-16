# Vibeweaver

A coding discipline for vibe-coding, built for [opencode](https://opencode.ai). The skill assumes the model is capable of doing the job — it just doesn't know how, and doesn't know what "done" means.

For now it's optimized for opencode only. Adapting it to DeepSeek Harness as a plugin is on the list, but not yet seriously studied.

As for Codex and Claude Code — never used them, no plans to, no idea. Anyone interested is welcome to fork.

## What it actually does

Vibeweaver is a contract, not a methodology. It takes the single worst habit of coding agents — saying "done" without proof — and makes it structurally impossible to get away with:

- **NO TEST, NO DONE** — every code change must be followed by executed tests with on-disk evidence (log files, screenshots, operation video, page audio). "It builds" is not evidence.
- **Test-first, always** — logic-bearing code is written RED→GREEN: write the failing test first, *watch it fail* (the output gets pasted into `tests/verification_log.md`), then write the minimal code to make it pass. A test that passes on the first run proves nothing — it might be testing the wrong thing entirely. Regression tests must complete the full revert-and-fail cycle before they count.
- **API-doc-driven backend tests** — for backend-only changes, the loop is: update the API doc → audit doc↔code consistency exactly once → write test cases *from the doc, not from the implementation* → run the httpx test→fix→test loop until everything passes. Cross-endpoint changes additionally require real-HTTP workflow scenarios with on-disk traces (`tests/workflows/*.trace.log`); direct service-layer calls are not E2E and don't count.
- **Self-starting verification loop** — the moment a change touches runtime behavior, the agent enters `Act → Capture → Verify → Fix → Log` on its own. The capture is graded by an independent verifier ([mm-sensor](https://github.com/logandoo) if installed — the maker/checker split means the model doesn't grade its own homework); video/audio are included when the verifier model supports them, and the mode is decided by a capability probe.
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

One honest caveat: this plugin speaks opencode's plugin API (`tool.execute.after`, `session.idle`, `client.app.log`). Whether Claude Code or Codex have an equivalent mechanism — I haven't verified it, so honestly no idea. Forks welcome. DeepSeek Harness's plugin mechanism looks quite nice; I'm researching it and will add a matching stop-hook plugin when I get to it.

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

In general, [mm-sensor](https://github.com/logandoo) and vibeweaver should be used together — the skill has built-in detection and invocation for it. Sure, if you really don't want it, no problem, though results take a small hit, since the two skills are designed as a pair. The division of labor:

- **vibeweaver makes the evidence exist.** Its rules force the agent to actually run the app, drive it with Playwright, and leave screenshots / operation video / page audio on disk.
- **mm-sensor grades it independently.** The maker/checker split: the model that wrote the code is forbidden from grading its own screenshots while mm-sensor is loaded. vibeweaver alone falls back to direct-read self-grading — weaker, and it demands extra cross-checks against DOM and logs.
- **A capability probe decides how much evidence gets captured.** At task start, vibeweaver runs `vision.py --probe` to ask the model behind mm-sensor what it can actually perceive. Full-modal models get the [video+audio] mode: Playwright records the whole flow as video, captures in-page audio via Web Audio, plus a terminal-state screenshot. Image-only models degrade to [video] or [image] mode. The mode is fixed per task, and every captured file is graded with `vision.py --detail high`.
- **If the environment is lacking, it degrades gracefully.** No ffmpeg → grade the raw webm via frame-sampling. Model can't hear audio → mm-sensor reports the skip explicitly and the loop continues on video + screenshots. Audio is an added signal, never a criterion by itself.

In one line: vibeweaver decides *what must be captured*; mm-sensor decides *what the evidence actually says*.

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

Restart opencode. The skill auto-triggers when you ask to build, modify, debug, or deploy anything. To also get the stop hook:

```bash
cp ~/.config/opencode/skills/vibeweaver/vibeweaver-gate.js ~/.config/opencode/plugins/
```

(Or just keep it simple and only use the skill without the gate — the gate is the enforcement layer, the skill is the instruction layer, and both work independently.)

Optional — but Playwright and [mm-sensor](https://github.com/logandoo) are the two we'd actually insist on: they're a designed pair, and the verification loop gets meaningfully weaker without them (self-grading instead of independent grading). Also useful: ffmpeg (video transcode), exa MCP + Context7 (research). None are required for the skill to function; they upgrade how much of the evidence gets collected and how independently it gets checked.

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
| `SKILL.md` | The binding operational contract (~1500 lines of "no, really, test it") |
| `CODING_PRINCIPLES.md` | The four iron rules + Karpathy's six disciplines |
| `ENGINEERING_STD.md` | Detailed engineering standards |
| `REFERENCE.md` / `APPENDIX.md` | Workflow reference / executable templates |
| `MEMORY_RULES.md` / `MEMORY_TEMPLATES.md` | Project memory subsystem |
| `vibeweaver-gate.js` | The stop-hook plugin (opencode) |
| `install.sh` / `install.bat` | Installers |

## Related

- [vibeweaver-mini](https://github.com/logandoo/vibeweaver/tree/main/vibeweaver-mini) — the always-on single-file entry point for quick tasks
- [mm-sensor](https://github.com/logandoo) — independent media verifier (image / video / audio)
- [vibeweaver-eval](https://github.com/logandoo/vibeweaver/tree/main/vibeweaver-eval) — the full benchmark harness, configs, and raw runs

## Attribution

`CODING_PRINCIPLES.md` is adapted (near-verbatim) from [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) ("Karpathy-Inspired Claude Code Guidelines", MIT License, by multica-ai / forrestchang), itself derived from [Andrej Karpathy's observations](https://x.com/karpathy) on how LLMs fail at coding.

Benchmark methodology and raw data: `vibeweaver-eval`.

## License

MIT — go nuts, fork it, break it, tell us what broke.
