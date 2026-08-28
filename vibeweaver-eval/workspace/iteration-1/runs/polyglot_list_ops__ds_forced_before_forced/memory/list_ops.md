# list_ops

- type: fix
- status: ⏳ Unverified (implemented + executed tests pass; awaiting harness/user confirmation)
- updated: 2026-08-29

## Implemented behavior (verified by execution, `tests/verification_run.log`)
- `append(list1, list2)` — all items of `list2` appended after all items of `list1`.
- `concat(lists)` — one-level flatten of a series of lists.
- `filter(function, list)` — items for which `function(item)` is True.
- `length(list)` — count of items (no `len()`).
- `map(function, list)` — `function(item)` applied to every item.
- `foldl(function, list, initial)` — left fold, `acc = function(acc, item)`.
- `foldr(function, list, initial)` — right fold: fold left over `reverse(list)` (direction-sensitive: `foldr(lambda acc,el: el/acc, [1,2,3,4], 24) == 9`; strings: `foldr(el+acc, [e,x,e,r,c,i,s,m], "!") == "exercism!"`).
- `reverse(list)` — reversed order, no flattening.

## Argument-order contract (keep — fold ordering is significant)
- Fold signature is `foldl(function, list, initial)` / `foldr(function, list, initial)` — **initial accumulator is the THIRD arg, list is SECOND** (matches the Exercism Python track; a different order flips `foldl(lambda acc,el: el/acc, [1,2,3,4], 24)` from 64 to a different value).

## Failed/Rejected approaches (do not retry)
- Delegating to builtins (`len`, `sum`, `map`, `filter`, `functools.reduce`, `reversed`, `list.reverse`, `[::-1]`, `+`) — violates the prompt's "without using existing functions" constraint; the implementation uses primitive `for` loops + `.append`/`.insert` only.
- Recursive fold (canonical Exercism example) — recursion-depth risk on long lists; the iterative loop version is behaviorally identical.
