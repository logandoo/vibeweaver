---
type: project
topic: list_ops
trust: verified
updated: 2026-09-14
---

# list_ops — basic list operations (Exercism polyglot)

## Task
Implement `append, concat, filter, length, map, foldl, foldr, reverse` in
`list_ops.py` without using the library functions being reimplemented.

## ✅ Verified behavior
- Both `foldl` and `foldr` call `function(accumulator, item)`.
  - `foldl` iterates left→right: `foldl(lambda acc, el: el/acc, [1,2,3,4], 24) == 64`.
  - `foldr` iterates right→left: `foldr(lambda acc, el: el/acc, [1,2,3,4], 24) == 9`.
- `concat` flattens exactly ONE level; nested lists stay nested.
- `reverse` does NOT flatten a list of lists.
- Empty inputs: folds return `initial`; `length([])==0`; others return `[]`.

## Source of truth
Public Exercism canonical data (`problem-specifications/exercises/list-ops/
canonical-data.json`) + Python-track `list_ops_test.py`. Hidden tests were
NOT read (eval integrity — see tests/decisions.md D-2).

## Notes / deferred
- Minor: parameter name `list` shadows the builtin (starter signature mandate).
  Not fixed (would diverge from the given API). No functional impact.
- Local verification: `tests/verification_transcript.log` (24/24 PASS).
