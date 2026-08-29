#!/usr/bin/env bash
# COV-2 lifecycle: library-only workspace (no persistent server).
# "start" = verify the module is importable and passes its smoke check.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m py_compile simple_linked_list.py
python3 -c "
from simple_linked_list import LinkedList, EmptyListException
songs = LinkedList(range(1, 6))
assert list(songs) == [5, 4, 3, 2, 1]
songs.push(6)
assert songs.pop() == 6
assert list(songs.reversed()) == [1, 2, 3, 4, 5]
assert list(songs) == [5, 4, 3, 2, 1]
try:
    LinkedList().head()
    raise AssertionError('expected EmptyListException')
except EmptyListException as e:
    assert e.args[0] == 'The list is empty.'
print('smoke OK')
"
echo "start.sh: module import + smoke check passed"
