# using-vibeweaver (bootstrap v1)

You are working with the vibeweaver skill. This 1–2 KB pointer is injected at
session start. Read the profile it names; do not load the full 340 KB contract
unless the task class demands it.

## When
Any coding task: implement / modify / debug / deploy / audit. Pure Q&A and
explanation do not need this workflow.

## Load
- model class + task class decide the profile:
  - strong model + CODE → `full` (root `SKILL.md`; read companions on demand)
  - weak/local model, or unknown model class → `core` + a warning
  - small single-path change → `mini` (deterministic checker loop)
- `VIBEWEAVER_MODEL_CLASS=strong|weak|local` is the explicit input; unknown
  means `core` and must be surfaced, never guessed.

## Evidence
- acceptance criteria → `tests/acceptance.md` (first line `> cap=5  stall=3×`)
- per-iteration record → `tests/verification_log.md`
- run evidence → logs / screenshots / traces under `tests/`
- completion → `tests/assert_artifacts.py` (canonical, pinned) exits 0

## Gate
- The gate is a completion gate, not an execution stop: a blocked write still
  landed; fix the evidence, then the next write re-checks.
- Never claim done without executed tests and on-disk evidence.
- Host without any injection hook: install `bootstrap.md` and ask the host to
  prepend it at session start (`BOOTSTRAP_VERSION=1`).

Full contract: `SKILL.md` §1 (13 covenants) → `TESTING_PROTOCOLS.md` §A4.1/§A4.8
→ `COMPLETION_GATE.md` §A4.4.
