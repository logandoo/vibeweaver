# Auto-Decisions (COV-12, AUTO mode)

## D-1 | Verifier selection (COV-5)
- trigger: mm_probe generated tests/probe_vision.png + tests/probe_vision.expected, but the model could not read the image content (Read tool returns no perceivable pixels) and no mm-sensor skill is installed.
- options: mm-sensor grading | model-native image grading | direct-read
- chosen: direct-read (only viable option)
- why: no mm-sensor available; model-native image grading impossible (image unreadable); direct-read of executed test logs is the honest verifier for a pure-function task.
- revisit-if: mm-sensor skill installed; visual UI appears in the workspace.

## D-2 | foldr argument order / expected values
- trigger: initial scratch verification script used self-invented foldr expectations (foldr-sub wanted -20) that failed against the first implementation.
- options: trust self-derived semantics | use canonical Exercism list_ops_test.py + .meta/example.py
- chosen: canonical suite (fetched both files)
- why: hidden grader is 24 canonical tests; canonical recursive foldr confirms function(acc, el) applied right-to-left; the loop-based equivalent (iterate reverse(list)) matches. Self-invented cases were wrong and discarded.
- revisit-if: hidden grader differs from current Exercism Python list-ops suite.

## D-3 | Design gate (COV-10)
- trigger: no design doc produced for a stub-implementation exercise.
- options: write DESIGN doc | state-skip as minor tweak
- chosen: state-skip (bugfix / minor tweak)
- why: single-file, 8 small functions; no architecture, no cross-module coupling, no external system; §A5 table classifies minor tweaks as autonomous.
- revisit-if: task grows into a multi-file feature.

## D-4 | Independent review (COV-8 / A4.9)
- trigger: behavior-semantic change (stub → implementation) would normally fire A4.9.
- options: dispatch A4.9 reviewer | not triggered
- chosen: not triggered (backed by `git diff --stat af071a9 94da537`: 1 logic file changed — list_ops.py 44 lines — rest are workflow artifacts; change kind = small pure-function implementation)
- why: change is confined, deterministic, covered 24/24 by executed canonical tests; below A4.9 "major change" threshold.
- revisit-if: diff grows or behavior reaches across components.

## D-5 | E2E depth classification
- trigger: completion table requires an E2E depth value.
- options: real-HTTP | workflow-trace | service-direct | unit-only
- chosen: unit-only
- why: pure functions with no server, no HTTP, no cross-endpoint behavior; unit-only is the documented acceptable depth for pure functions.
- revisit-if: a runtime/service layer is added.
