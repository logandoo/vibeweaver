---
type: fix
status: verified
trust: verified
date: 2026-08-29
---

# fix_robot_name — Robot name generation

## Problem
Robot needed lazy random unique name `[A-Z]{2}\d{3}` with reset support and cross-robot uniqueness.

## Solution
- Class-level `_used_names` set guarantees uniqueness among existing robots.
- Lazy `name` property generates on first access; `reset()` sets `_name = None` (does NOT release old name — required so the canonical seeded-reset test yields a different name deterministically).
- Collision retry loop; uses stdlib `random` (so `random.seed` in tests works).

## Verified
- Inline transcript: 7/7 criteria PASS (format, sticks, distinct robots, reset, seeded-reset differs, 100 unique, clean import).
- Canonical exercism `robot_name_test.py`: 4/4 PASS (unittest OK).
