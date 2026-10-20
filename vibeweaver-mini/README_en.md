# vibeweaver-mini

The small-model edition of [vibeweaver](https://github.com/logandoo/vibeweaver): a
**deterministic loop + checker**. Built for forced injection — a weak-instruction
model will not load a skill on its own, and will not follow long rules; it will
follow concrete mechanical actions with immediate feedback.

## What it is

A two-piece kit:

- `SKILL.md` (~2 KB) — one loop: run the checker → fix the first failure →
  repeat until it prints `ALL CHECKS PASS`. No engineering principles to remember.
- `scripts/vw_check.py` — the deterministic checker: runs pytest, prints the
  failing tests plus an observed-vs-expected repair packet, and **refuses to run
  if the test set changed** (hash guard; a discipline aid, not a security boundary).

## Why it works (G1 probe, Sep 2026, qwen3.6-35B-A3B, forced injection)

Four tasks that every prompt-only arm failed (grade_school / list_ops /
phone_number / transpose):

| configuration | passed |
|---|---|
| old mini (prose rules only) | 1/4 |
| mini-v2 + checker + **self-written tests** | 1/4 (phone_number regressed 13/21 → 5/21 — self-tests deceive) |
| mini-v2 + checker + **generated tests (unqualified)** | 1/4 (false green: frozen suite passes, real tests 10 failed) |
| mini-v2 + checker + **the project's real tests** | **4/4 full marks** |

Conclusion: **the loop is not the bottleneck — the oracle is.** The small model
happily runs the checker 12-36 times; what it lacks is trustworthy feedback. Give
it the project's own tests as the oracle and it fixes what it could not fix before.

## Install

```bash
bash install.sh                 # macOS / Linux
install.bat                     # Windows
```

Then, in the project you want the loop on:

```bash
bash ~/.config/opencode/skills/vibeweaver-mini/scripts/setup_project.sh
# or: sh setup_project.sh /path/to/project
```

That copies `vw_check.py` and `script/check.sh` into the project — the markers
the gate looks for. Then force-inject or instruct: "run `python3 vw_check.py`
until it prints ALL CHECKS PASS."

## The checker gate

`install.sh` also installs `vibeweaver-mini-gate.js` into
`~/.config/opencode/plugins/`. It activates when the project has `vw_check.py`
(or `.vw_test_hashes.json`), runs the checker after every write/edit, blocks
the tool result with the repair packet on failure, and surfaces
`ALL CHECKS PASS` on success. At session idle it challenges a completion claim
until the checker is green (budget: 2 prompts/session). Full-skill projects
(`tests/verification_log.md`) are excluded — the full gate owns those.

Disable with `VIBEWEAVER_MINI_GATE=off`; checker timeout is
`VIBEWEAVER_MINI_TIMEOUT_MS` (default 120000).

## Hard rules (already in the skill)

- **The project's own tests are the only oracle that certifies**; a suite you
  wrote yourself is weak evidence and must be labelled as such.
- Never edit tests to make them pass; the checker refuses to run if the test set changed.
- Do not invent interfaces: a function/method not visible in the spec is an open
  question, not a guess.
- Same check fails 3× → re-read the spec before changing anything again.

## Relationship to the full skill

The full vibeweaver is a complete engineering contract for capable models
(evidence gates, memory, design gates, audit). The mini is not a compressed copy —
it is a different route: move verification out of the prompt and into a
deterministic program. They coexist: the full skill governs process
trustworthiness, the mini governs the weak model's execution loop.

Mini does not use the full gate/auditor pair: those activate on
`tests/verification_log.md`, which this kit does not create. It ships a smaller
guard instead, `vibeweaver-mini-gate.js`, which enforces the checker's
`ALL CHECKS PASS` line directly.
