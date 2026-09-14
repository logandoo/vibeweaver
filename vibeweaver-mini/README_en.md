# vibeweaver-mini

The small-model edition of [vibeweaver](https://github.com/logandoo/vibeweaver): a
**deterministic loop + checker**. Built for forced injection — a weak-instruction
model will not load a skill on its own, and will not follow long rules; it will
follow concrete mechanical actions with immediate feedback.

## What it is

A two-piece kit:

- `SKILL.md` (~1.7 KB) — one loop: run the checker → fix the first failure →
  repeat until it prints `ALL CHECKS PASS`. No engineering principles to remember.
- `scripts/vw_check.py` — the deterministic checker: runs pytest, prints the
  failing tests plus an observed-vs-expected repair packet, and **refuses to run
  if the test set changed** (hash guard; a discipline aid, not a security boundary).

## Why it works (wave6 measurements, qwen3.6-35B-A3B, forced injection)

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

## Usage

1. Put `SKILL.md` in a skill directory (e.g. `~/.config/opencode/skills/vibeweaver-mini/`).
2. Copy `scripts/vw_check.py` into the project root.
3. Force-inject or instruct: "run `python3 vw_check.py` until it prints ALL CHECKS PASS."

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
