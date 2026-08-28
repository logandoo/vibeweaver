# A4.9 Review Package — Robot Name exercise (`robot_name.py`)

Reviewer scope: READ-ONLY. Review the candidate implementation below against the spec.
Deliver a verdict: Strengths · Critical / Important / Minor (dimension-tagged
Bugs/Security/Compliance, Minors <= 5 itemized, with file:line + why) · Assessment.

## Task spec (prompt.md, verbatim requirements)
- When a robot comes off the factory floor, it has no name.
- The first time you turn on a robot, a random name is generated in the format of two
  uppercase letters followed by three digits, such as RX837 or BC811.
- Every once in a while we need to reset a robot to its factory settings, which means its
  name gets wiped; the next time you ask, that robot responds with a new random name.
- Names must be random: they should not follow a predictable sequence.
- Using random names means a risk of collisions. Your solution must ensure that every
  existing robot has a unique name.

## Expected interface (hidden grader = Exercism-style Python test)
- `Robot()` constructs; `robot.name` attribute immediately returns a valid name.
- `robot.reset()` wipes and assigns a new valid name.
- Uniqueness across instances and after resets.

## Candidate implementation (robot_name.py)
```python
import random
import string

LETTERS = string.ascii_uppercase
DIGITS = string.digits


class Robot:
    _used_names = set()

    def __init__(self):
        self.name = self._generate_name()

    def reset(self):
        self.name = self._generate_name()

    @classmethod
    def _generate_name(cls):
        while True:
            candidate = "".join(random.choices(LETTERS, k=2)) + "".join(
                random.choices(DIGITS, k=3)
            )
            if candidate not in cls._used_names:
                cls._used_names.add(candidate)
                return candidate
```

## Acceptance criteria exercised (tests/acceptance.md)
1. imports + constructs; 2. name matches ^[A-Z]{2}[0-9]{3}$; 3. name stable across reads;
4. distinct across instances; 5. reset() new valid name; 6. 500-robot uniqueness;
7. random/non-sequential (>=20 distinct prefixes).

## Evidence summary (tests/verification_run.log)
- 7/7 criteria PASS; extended sweep: 3000 robots unique, 200 sequential resets OK,
  669 distinct letter prefixes, 950 digit suffixes.
