# vibeweaver-mini

A trimmed-down [vibeweaver](https://github.com/logandoo/vibeweaver), single-file, ~5KB, that buys a small gain on small LLMs whose instruction-following is mediocre but whose coding ability is decent. The kind of skill that people who don't need it don't need at all — and people who do need it can actually use.

## Why mini exists at all

The full vibeweaver is ~88KB of rules and ten covenants — to a small model that's not a rulebook, that's a threat. In the qwen3.6-27B eval, the full version was **loaded exactly zero times out of 16 tasks**; mini got loaded 62.5% of the time and beat even the force-injected full version (62.5% vs 56%).

The mechanism is brutally simple: **size decides trigger rate, trigger rate decides everything.** A short rulebook the model will actually read beats a masterpiece it will never open. mini compresses "the discipline that must be executed" to its shortest form, so weak-following models can actually read it and follow along.

## What it keeps

- **Mandatory-load declaration** — the frontmatter literally says "load this skill before writing any code"; the most aggressive trigger wording in the family
- **Decompose & research first** — break the request into sub-tasks, search for existing solutions before coding
- **Understand the project first** — read config, scripts, README, git status before changing anything
- **TDD, test-first** — RED→GREEN, watch it fail or it doesn't count; regression fixes must complete the revert-and-fail proof; code written before its test gets deleted and restarted
- **Frontend 3-layer testing standard** — logic tests (extract pure functions) + component tests (render & interaction) + E2E screenshots (acceptance criteria written to `tests/acceptance.md` BEFORE coding, Playwright screenshots, graded by [mm-sensor](https://github.com/logandoo/mm-sensor) when installed)
- **NO TEST, NO DONE** — no executed tests with on-disk evidence, no completion; multi-endpoint backend tasks additionally require one cross-endpoint workflow test with state-transition assertions
- **Script-only lifecycle** — build/start/stop go through `script/`; raw `npm run build` / `uvicorn` forbidden
- **Fix loop** — max 5 iterations per problem; same failure 3× in a row means change approach
- **Finish & report** — `acceptance.md` + `verification_log.md` must exist, descriptive commit, evidence in the report

## What was cut compared to vibeweaver

| Removed | Notes |
|---|---|
| **Project memory system** | `memory/`, `MEMORY.md` index, topic files, trust tiers (⛔/✅/⏳/❌), Final Memory Gate — the whole cross-session memory subsystem |
| **Design-doc system** | FLOW / PAGE / DATABASE / BACKEND_DESIGN.html plus the Design Gate A/B approval gates |
| **New-project scaffolding** | The full C1 workflow, `config.toml` templates, Part B default stack (FastAPI + React + Vite + PostgreSQL) |
| **Completion table & audit lines** | The 8-column completion table, `[Verification Gate]` line, `[Convergence]` line, Covenant Recall, the formalized COV-1~10 covenant set |
| **Executable assertions** | The 13-group `assert_artifacts.py` byte-checking script. The `vibeweaver-gate` plugin is NOT excluded — if installed, its inline evidence floor and stall observer cover mini projects too (mini's artifact formats are deliberately gate-compatible) |
| **Independent code review** | A4.9 subagent review dispatch (COV-8) |
| **API-doc-driven loop** | A4.7's "update API doc → audit doc↔code → write cases from the doc", reduced to "call the API and verify + one workflow test" |
| **Systematic debugging phases** | A4.6 root-cause investigation workflow, reduced to one line (read the full error → diagnose root cause → change one thing) |
| **Config / deps / communication / git chapters** | The standalone A3, A6, A7, A8, A9 rules |
| **Video & audio evidence** | Playwright `record_video` and Web Audio capture — screenshots only now |
| **mm-sensor modality probe** | `vision.py --probe` and the [video+audio]/[video]/[image] modes, simplified to "grade with mm-sensor if installed, otherwise read directly" |
| **Large-task plan** | C3's Files/Interfaces/Steps planning template |
| **Companion files** | `CODING_PRINCIPLES.md` / `ENGINEERING_STD.md` / `REFERENCE.md` / `APPENDIX.md` / `MEMORY_RULES.md` / `MEMORY_TEMPLATES.md` — mini is deliberately single-file |

In one line: **mini keeps only the must-do hard gates and cuts every nice-to-have.** It won't discuss design docs with a small model; it just watches it write tests and leave evidence.

## Benchmarks

16-task A/B eval (10 Aider polyglot + 6 SWE-bench Lite, hidden-test grading), head-to-head with the full version, all from the fixed `vibeweaver-eval` harness. Setup modes: **baseline** (no skill), **available** (skill listed in `available_skills`, the model decides whether to load it — that's the trigger rate), **force-injected** (skill text pasted into the prompt, no choice).

Before reading the numbers, the honesty clause: 16 tasks is a small sample with ±2–3 task variance, and each arm runs once per round — a full round on qwen3.8 takes 40-60 minutes (force-injected arms run several times longer), on the llama.cpp-hosted 35b-a3b it's 1-3 hours. **Read the direction, not the exact scores — and don't assume mini's edge transfers to your model.** On models that already behave, mini has measured exactly zero gain (qwen3.8: 13/16 = baseline; deepseek: within noise). The gains below are real but model-specific.

### Mid-size model (qwen3.6-27B) — where mini was born

| Arm | Pass rate (16 tasks) | Trigger rate |
|---|---|---|
| No skill | 7/16 (44%) | — |
| Full 71KB, force-injected | 9/16 (56%) | — |
| Full 71KB, available | 6/16 (38%) | 0/16 |
| **vibeweaver-mini, available** | **10/16 (62.5%)** | **10/16** |

- Best arm of the whole eval: +18.75pp over baseline, and 6.5pp above the force-injected full version
- SWE-bench 5/6 (83%) vs baseline 3/6 (50%); the only arm to solve pytest-6116
- Cost: 113s/task avg vs 69s baseline (+63%)

### Newer model (qwen3.8-27B) — neutral

| Arm | Pass rate (16 tasks) | Trigger rate |
|---|---|---|
| No skill | 13/16 (81%) | — |
| vibeweaver-mini, available | 13/16 (81%) | 10/10 (polyglot) |
| Full vibeweaver, available | 15/16 (94%) | 12/16 |
| **Full vibeweaver, force-injected** | **16/16 (100%)** | — |

mini lands at baseline — the discipline it supplies has become native behavior in the newer model. On models that already have the discipline, the full version's extra machinery (acceptance criteria, doc-driven tests, verification gates) is what earns the extra 3 tasks when force-injected.

### Weakest model (qwen3.6-35b-a3b) — force-injection's day

| Arm | Pass rate (16 tasks) | Trigger rate |
|---|---|---|
| No skill | 6/16 (37.5%) | — |
| vibeweaver-mini, available | 6/16 (37.5%) | **0/10** |
| **vibeweaver-mini, force-injected** | **7/16 (43.8%)** | — |
| Full vibeweaver, force-injected | 5/16 (31.3%) | — |

On an extremely weak model (34.6B MoE, ~3B active) the rules flip:

- **Loading collapses entirely**: 0/10 — the model is too weak to even read the available_skills list.
- **Force-injecting mini is the only thing that works**: 7/16 (best arm of the round), with a full-marks bowling (31/31) and robot_name (4/4).
- **Force-injecting the full version is a disaster**: 5/16, SWE-bench down to 1/6 with five "no diff produced" — 71KB of rules floods the context of a 3B-active model and it gives up.
- Cost on this model was brutal (llama.cpp, 700-943s/task avg, 2-9 timeouts per arm) — see vibeweaver-eval for raw numbers.

The force-injection advice is therefore no longer a blanket "don't": on mid-size models, force-feeding mini is pure overhead (qwen3.6-27B drops from 62.5% to 50%); on extremely weak models, it's the only path that works.

On strong models (deepseek-v4-flash-0731) mini is neutral (68.8% = baseline) — strong models already have this discipline natively; mini's value lives on weak models.

## Installation

```bash
git clone https://github.com/logandoo/vibeweaver && cp -r vibeweaver/vibeweaver-mini ~/.config/opencode/skills/vibeweaver-mini
```

or copy `SKILL.md` into your skills folder:

- Global (Linux/macOS): `~/.config/opencode/skills/vibeweaver-mini/`
- Project: `.opencode/skills/vibeweaver-mini/`

Restart opencode. Optional companions: Playwright (screenshot capture), [mm-sensor](https://github.com/logandoo/mm-sensor) (independent screenshot grading — more reliable when installed).

Optional — the mechanical floor: the `vibeweaver-gate` plugin blocks writes while evidence is missing and warns when the same file is edited 3× with no new PASS. It is not bundled with mini, but it covers mini projects out of the box (mini's artifact formats are aligned with its checks). For weak models this enforcement is worth more than any instruction:

```bash
curl -o ~/.config/opencode/plugins/vibeweaver-gate.js \
  https://raw.githubusercontent.com/logandoo/vibeweaver/main/vibeweaver/vibeweaver-gate.js
```

## Which one to pick

- **Extremely weak model (~3B active)** → mini, force-injected (available-mode loading collapses below a capability threshold; the full version's ~88KB floods the context)
- **Weak-following model (small/mid-size)** → mini, always-on
- **Strong model** → full [vibeweaver](https://github.com/logandoo/vibeweaver), plugin-injected (or mini always-on + full version expanded on demand)
- Project memory, design docs, the physical gate, all companion files — those live in the full version only

## Related

- [vibeweaver](https://github.com/logandoo/vibeweaver) — the full version: memory system, design docs, verification gate, all companion files
- [mm-sensor](https://github.com/logandoo/mm-sensor) — independent image/video/audio verifier

## License

MIT
