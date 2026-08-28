#!/usr/bin/env bash
# vibeweaver lifecycle: this is a pure Python library (no server, no build).
# "start" = compile + smoke check of the module.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m py_compile simple_linked_list.py
python3 -c "import simple_linked_list; ll = simple_linked_list.LinkedList([1,2,3]); assert len(ll) == 3; assert list(ll) == [3,2,1]; assert list(ll.reversed()) == [1,2,3]; assert ll.pop() == 3; print('smoke check OK')"
