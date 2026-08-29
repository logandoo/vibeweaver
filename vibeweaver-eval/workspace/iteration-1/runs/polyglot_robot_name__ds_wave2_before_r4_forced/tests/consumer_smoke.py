import re
import sys
import random

sys.path.insert(0, "/Users/logan/Documents/DEV/SKILLS/vibeweaver-repo/vibeweaver-eval/workspace/iteration-1/runs/polyglot_robot_name__ds_wave2_before_r4_forced")
from robot_name import Robot

NAME_RE = re.compile(r"^[A-Z]{2}\d{3}$")
failures = []


def check(label, cond):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)


r = Robot()
n1 = r.name
check("c1 name format regex", bool(NAME_RE.match(n1)))
check("c2 name sticks across accesses", n1 == r.name == r.name)

r2 = Robot()
check("c3 different robots differ", r2.name != n1)

old = r.name
r.reset()
new = r.name
check("c4 reset yields new different name", new != old and bool(NAME_RE.match(new)))

random.seed(0)
seen = {Robot().name for _ in range(2000)}
check("c5 global uniqueness over 2000 robots", len(seen) == 2000)
check("c5 all sweep names match format", all(NAME_RE.match(s) for s in seen))

prefixes = {s[:2] for s in seen}
suffixes = {s[2:] for s in seen}
check("c6 letter prefixes vary (not single)", len(prefixes) > 1)
check("c6 digit suffixes vary (not single)", len(suffixes) > 1)
sequential_block = {f"AA{i:03d}" for i in range(1000)}
check("c6 not a fixed sequential pattern", not (seen >= sequential_block))

print(f"\nsample names: {sorted(seen)[:5]} ... {sorted(seen)[-3:]}")
sys.exit(1 if failures else 0)
