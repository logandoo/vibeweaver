---
name: Pig Latin exercise contract
description: The exercise contract — Exercism canonical pig-latin spec, function signature translate(text), graded by hidden canonical tests, no test files may be created/modified
type: project
date: 2026-08-29
---

# Pig Latin Exercise Contract

**Contract:** Implement `translate(text)` in `pig_latin.py`. The four rules (vowel/xr/yt →
+ay; consonant cluster → move to end +ay; zero+ consonants then "qu" → move cluster+qu +ay;
consonants then "y" → move consonants +ay) exactly match the Exercism canonical-data.json.

**Constraints:** Only `pig_latin.py` may be modified. No test files may be created or
modified (grading is by the harness's hidden `pig_latin_test.py`). Verification is by
executing the module directly against the canonical cases and logging output.

**Why:** Keeps the graded artifact clean and unambiguous for the eval harness.

**How to apply:** Future sessions touching this run should not add tests; verify by running
the 23-case canonical sweep (dict in tests/verification_output.log). Memory of the 
vibeweaver skill applies: script/, tests/acceptance.md, tests/verification_log.md,
memory/ are workflow artifacts, not tests.
