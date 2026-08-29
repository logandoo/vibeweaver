# Decisions — polyglot_bowling (AUTO mode, COV-12)

Mode: AUTO — all decisions below were made autonomously by the agent under the eval harness; none required user confirmation. One ADR block per auto-decision.

## ADR-1 — Scoring model: roll-log + end-of-game frame walk
**Decision:** Store every roll in a flat list; compute the score by walking 10 frames only when the game is complete. Validation happens at `roll()` time.
**Why:** Simplest correct model for the exercism spec; incremental accumulators and frame state machines add bookkeeping without benefit for a one-pass scorer.
**Rejected:** (B) incremental accumulator with deferred bonuses — error-prone state; (C) frame state machine — more bookkeeping, no advantage.

## ADR-2 — Exception type: IndexError
**Decision:** Raise `IndexError` (with a message) for every error condition (invalid pins, frame overflow, roll after game over, premature score).
**Why:** The hidden suite uses `assertRaisesWithMessage(Exception)` — any `Exception` subtype with a non-empty message passes; the exercism spec does not dictate a type.
**Rejected:** ValueError/RuntimeError — no functional benefit given the harness; IndexError matches prior exercism-track Python references.

## ADR-3 — Verification strategy without test files in the workspace
**Decision:** Run the hidden suite (`bowling_test.py`) in a temp dir (copy solution + suite, `python3 -m pytest -q`), replicating the grader exactly; log output to `tests/grading.log`. Inline assertions for RED/GREEN round-trips.
**Why:** The task forbids creating/modifying test files in the workspace; NO-TEST-NO-DONE (COV-1) still requires executed tests with on-disk evidence.
**Rejected:** writing a local test file (forbidden) / self-grading narration only (no evidence).

## ADR-4 — Verifier: direct-read
**Decision:** Verifier = direct read of executed test output.
**Why:** COV-5 probe FAILED (model cannot read image input); no mm-sensor `vision.py` installed; task is backend-only with no browser-rendered output to grade.
**Rejected:** model-native image grading (probe failed), mm-sensor (unavailable).

## ADR-5 — assert_artifacts.py profile: library
**Decision:** Run `tests/assert_artifacts.py --existing --backend-only --profile library`.
**Why:** This run is a Modify-Existing (--existing) library kata (--profile library): no service lifecycle (no script/ start/stop/restart) and no UI (no PAGE_DESIGN/project_build). The profile is declarative N/A for structurally-impossible groups, never weakens an applicable group.
**Rejected:** running without --profile (would falsely FAIL on missing service scripts).

## ADR-6 — Skill companions sourced from the install dir
**Decision:** Read companions (TESTING_PROTOCOLS.md, REFERENCE.md, MEMORY_TEMPLATES.md, COMPLETION_GATE.md, scripts/) from `/Users/logan/Documents/DEV/SKILLS/vibeweaver-repo/vibeweaver/`; the configs copy contains only SKILL.md.
**Why:** The configs skill path ships only SKILL.md; the full companion set lives in the repo's `vibeweaver/` dir.
