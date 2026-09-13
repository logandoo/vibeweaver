# Decisions (AUTO mode, append-only)

D-1 | trigger: §2 approach choice | options: (A) roll-list + frame-indexed scoring; (B) per-frame accumulator with bonus state | chosen: A | why: handles 10th-frame fill balls naturally, fewer mutable-state edge cases, canonical form confirmed by research | revisit-if: input validation / partial-game queries become required
D-2 | trigger: verification mode selection | options: mm-sensor / model-native image / direct read | chosen: direct read (non-web) | why: pure Python library, no browser-rendered output; companion mm_probe.py and mm-sensor not present in this bundle | revisit-if: a UI/HTTP surface is added
D-3 | trigger: "do not create test files" vs skill tests/ artifacts | options: create a .py test harness / run inline python and log output | chosen: inline python, log to tests/ | why: user constraint forbids test files; COV-1 still satisfied by executed tests with on-disk evidence | revisit-if: a test suite is later permitted
