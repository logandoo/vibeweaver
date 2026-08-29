# MEMORY — bowling.py (polyglot bowling exercise)

## Session 2026-08-29
- ✅ Verified: BowlingGame implemented via record-all-rolls + frame-walk; score() walks 10 frames (strike += 1 roll pointer, else += 2), adds bonuses from subsequent rolls. Handles 10th-frame fill balls naturally.
- ✅ Verified: perfect=300, gutter=0, all-spares=150, prompt example=48, 10th X1/=20, XXX=30, 5/7=17.
- ⏳ Unverified: behavior when score() called on incomplete game (spec says end-of-game only).
- ❌ Failed direction: none (only test-data error in iter 1, corrected).
- Reviewer minors deferred: no type annotations (cosmetic); no pins validation (not required); no incomplete-game guard (spec contract).
- Reference: tests/acceptance.md, tests/verification_log.md, tests/decisions.md.
