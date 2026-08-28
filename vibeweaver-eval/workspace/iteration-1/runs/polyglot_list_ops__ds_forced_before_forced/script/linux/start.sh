#!/usr/bin/env bash
# vibeweaver lifecycle: this is a pure Python library (no server, no build).
# "start" = compile + smoke check of the module.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m py_compile list_ops.py
python3 -c "
import list_ops as lo
assert lo.append([1, 2], [2, 3, 4, 5]) == [1, 2, 2, 3, 4, 5]
assert lo.concat([[1, 2], [3], [], [4, 5, 6]]) == [1, 2, 3, 4, 5, 6]
assert lo.filter(lambda x: x % 2 == 1, [1, 2, 3, 5]) == [1, 3, 5]
assert lo.length([1, 2, 3, 4]) == 4
assert lo.map(lambda x: x + 1, [1, 3, 5, 7]) == [2, 4, 6, 8]
assert lo.foldl(lambda acc, el: el / acc, [1, 2, 3, 4], 24) == 64
assert lo.foldr(lambda acc, el: el / acc, [1, 2, 3, 4], 24) == 9
assert lo.foldr(lambda acc, el: el + acc, ['e', 'x', 'e', 'r', 'c', 'i', 's', 'm'], '!') == 'exercism!'
assert lo.reverse([1, 3, 5, 7]) == [7, 5, 3, 1]
print('smoke check OK')
"
