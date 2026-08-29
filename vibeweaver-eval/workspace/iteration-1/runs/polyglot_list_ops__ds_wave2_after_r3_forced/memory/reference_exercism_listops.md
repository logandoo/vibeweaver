---
name: Exercism list-ops spec
description: Canonical list_ops API surface and fold arg-order convention for the Exercism list-ops exercise
type: reference
date: 2026-08-29
---

# Exercism list-ops spec

Confirmed from the sibling reference run (polyglot_list_ops__ds_wave2_after_forced, passed 24/24) and the prompt.

- `append(list1, list2)` — return new list with list1's items then list2's.
- `concat(lists)` — NOT `concatenate`; flattens a list of lists.
- `filter(function, list)` — keep items where `function(item)` is truthy.
- `length(list)` — count items.
- `map(function, list)` — `function(item)` per item.
- `foldl(function, list, initial)` and `foldr(function, list, initial)` — call the function as `function(accumulator, item)` (arg order significant); `foldr` is a right fold.
- `reverse(list)` — reversed copy.

**How to apply:** Match this exact surface (names, signatures, fold arg order) or the grader fails; arg order `(acc, item)` is the canonical convention here.
