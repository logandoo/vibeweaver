# ADR Log — Bowling Game scoring (Mode: AUTO, COV-12)

## ADR-1 — Scoring/validation architecture
**Decision:** Store all rolls; `roll()` validates via prefix-validator; `score()` requires a complete 10-frame game then sums (Approach A).
**Why:** canonical kata shape; single source of truth (`self.rolls`); validation matches hidden canonical-data error cases exactly.
**Rejected:** B (incremental score at roll time — more corruptible state, same validation), C (lazy score-only — fails hidden error tests).

## ADR-2 — Verification strategy (no UI)
**Decision:** No Playwright loop — pure-library logic with no runtime-rendered output. Verify via executed tests with on-disk logs: run the authoritative hidden suite read-only (`PYTHONPATH=$WS python3 -m unittest bowling_test`) + fresh inline spot-checks. Verifier: direct read.
**Why:** COV-4/5 Playwright/multimodal capture only applies to runtime-visible output; none exists here. The hidden suite is the authoritative spec (exercism canonical-data).

## ADR-3 — COV-9 baseline in a shared dirty repo
**Decision:** Baseline commit `backup: before changes` staged ONLY this run's files (bowling.py, prompt.md); verified stub loads inertly → `Baseline verified GREEN`.
**Why:** workspace lives inside the shared vibeweaver-repo; bare `git add -A` at root would sweep sibling runs' unrelated dirty changes into the commit.
**Note:** `run.log` is harness-managed; excluded from commits.

## ADR-4 — A4.9 review trigger
**Decision:** Dispatch independent reviewer (COV-8) — the change-wave diff (`git diff --stat` bcfd72d..HEAD) spans ≥3 paths (bowling.py + tests/* + memory/*), exceeding the single-file threshold.
**Why:** "files changed" counts every path in `git diff --stat`; trigger includes behavior-semantic changes.
**Result:** APPROVE, 0 blocker/major/minor (3 nits), 50k random-sequence cross-check with 0 mismatches.
