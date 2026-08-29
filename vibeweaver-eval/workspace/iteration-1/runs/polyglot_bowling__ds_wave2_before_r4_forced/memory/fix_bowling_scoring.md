---
name: Fix: Bowling Game Scoring
description: Exercism bowling kata — store all rolls, validate each roll via prefix-validator, score over 10 frames; _build_frames is completeness-only (score/_game_over), _valid_prefix is roll() gate
type: fix
date: 2026-08-29
status: ⏳
commit: cc46e3c
---

# Fix: Bowling Game Scoring

**Problem:** `bowling.py` was a stub (`roll`/`score` were `pass`). Exercise requires full 10-frame scoring (open/spare/strike, 10th-frame fill balls) plus strict input validation: exceptions for pins<0, pins>10, frame two-roll sum>10, invalid 10th-frame bonus sequences, rolling after game over, and scoring unstarted/incomplete games.

**Attempted Fix:** Store all rolls in `self.rolls`. `roll()` range-checks pins, rejects after game over, then accepts only if the candidate roll sequence is a valid prefix. `score()` requires a complete 10-frame game then sums via the index-walk kata loop (strike → 10 + next two rolls, spare → 10 + next roll, else two-roll sum). Helpers: `_valid_prefix` (roll-time gate), `_build_frames` (completeness), `_game_over`.

**Root cause of the one failed iteration (iter 1, RED):** reusing `_build_frames` in `roll()` conflated "structurally invalid" with "game incomplete" — it returns None for fewer than 10 frames, so every in-progress roll was rejected (28/31 hidden tests errored). Fix: separate prefix-validation from completeness-checking.

**Failed Approaches (DO NOT retry):**
- Validating `roll()` candidates with the completeness-oriented `_build_frames` — rejects valid in-progress prefixes; incomplete games are legal to roll, only `score()` may require completeness.

**Rejected Alternatives:**
- Incremental scoring during `roll()` (running total + pending bonuses) — more state to corrupt across strike/spare chains, same validation burden, rejected for higher bug surface.
- No roll-time validation / lazy score-only — fails the hidden error-case tests, rejected.

**Files:** `bowling.py`

**Status:** ⏳ Pending — automated evidence GREEN (31/31 hidden tests, 50k random-sequence cross-check), awaiting user confirmation.
