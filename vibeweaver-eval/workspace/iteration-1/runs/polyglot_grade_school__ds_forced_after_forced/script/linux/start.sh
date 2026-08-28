#!/usr/bin/env bash
# vibeweaver lifecycle: this is a pure Python library (no server, no build).
# "start" = compile + smoke check of the module.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m py_compile grade_school.py
python3 -c "
from grade_school import School

s = School()
assert s.roster() == [], 'fresh School roster must be empty'
assert s.add_student('Jim', 2) is True, 'first add must succeed'
assert s.add_student('Jim', 2) is False, 'duplicate in same grade must be rejected'
assert s.add_student('Jim', 5) is False, 'same student in another grade must be rejected'
assert s.add_student('Anna', 1) is True
assert s.add_student('Barb', 1) is True
assert s.add_student('Charlie', 1) is True
assert s.add_student('Alex', 2) is True
assert s.add_student('Peter', 2) is True
assert s.add_student('Zoe', 2) is True
assert s.added() == [True, False, False, True, True, True, True, True, True], s.added()
assert s.grade(2) == ['Alex', 'Jim', 'Peter', 'Zoe'], s.grade(2)
assert s.grade(5) == [], 'grade with no students must be empty'
assert s.roster() == ['Anna', 'Barb', 'Charlie', 'Alex', 'Jim', 'Peter', 'Zoe'], s.roster()
print('smoke check OK: roster, grade, added(), duplicate rejection all correct')
"
