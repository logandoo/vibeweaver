#!/usr/bin/env bash
# vibeweaver lifecycle: this is a pure Python library (no server, no build).
# "start" = compile + smoke check of the module.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m py_compile grade_school.py
python3 -c "import grade_school; s = grade_school.School(); assert s.add_student('Aimee', 2) is True; assert s.roster() == ['Aimee']; assert s.grade(2) == ['Aimee']; assert s.added() == [True]; print('smoke check OK')"
