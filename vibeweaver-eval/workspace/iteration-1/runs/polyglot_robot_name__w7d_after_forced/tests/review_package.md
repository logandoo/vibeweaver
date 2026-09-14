# Independent Review Package — robot_name (A4.9 / COV-8)

Baseline: untracked new file (git shows `?? workspace/iteration-1/runs/polyglot_robot_name__w7d_after_forced/`),
so the reviewed artifact is the final `robot_name.py` content, not a git diff.

## Deliverable under review — `robot_name.py`

```python
import random
import string


class Robot:
    used_names = set()

    def __init__(self):
        self._name = None

    @property
    def name(self):
        if self._name is None:
            self._name = self._generate_name()
        return self._name

    def reset(self):
        self._name = None

    @classmethod
    def _generate_name(cls):
        while True:
            candidate = "".join(
                random.choice(string.ascii_uppercase) for _ in range(2)
            ) + "".join(random.choice(string.digits) for _ in range(3))
            if candidate not in cls.used_names:
                cls.used_names.add(candidate)
                return candidate
```

## Acceptance contract (`tests/acceptance.md`)

1. `Robot().name` matches `^[A-Z]{2}\d{3}$` on first access.
2. Repeated `robot.name` reads return the same value (name sticks until reset).
3. Two independently created robots have different names.
4. `robot.reset()` wipes the name; the next `name` access yields a valid name
   different from the previous one (canonical seeded-RNG reset test).
5. Across many live robots no two share a name, and a reset robot never receives
   a name already issued to any existing robot.

## Executed evidence (`tests/verification_run.log`)

- Canonical hidden suite `robot_name_test.py`: `4 passed in 0.01s`.
- Inline stress: 5000 live robots all unique, 1000 resets never reissue,
  seeded reset distinct `FV566 -> CP146`, `exit=0`.
