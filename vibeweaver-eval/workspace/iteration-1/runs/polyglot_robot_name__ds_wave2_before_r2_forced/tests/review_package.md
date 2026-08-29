# A4.9 Review Package — polyglot robot_name

## Task requirements (from prompt.md)
- Robot has no name at creation.
- First name access generates a random name: two uppercase letters + three digits (e.g. RX837, BC811).
- reset() wipes the name; next access generates a new random name.
- Names must be random (not a predictable sequence) and every existing robot must have a unique name.

## Implementation under review (robot_name.py)
```python
import random
import string


class Robot:
    _used_names = set()

    def __init__(self):
        self._name = None

    @property
    def name(self):
        if self._name is None:
            self._name = self._generate_name()
        return self._name

    def reset(self):
        self._name = None

    @staticmethod
    def _generate_name():
        while True:
            candidate = (
                random.choice(string.ascii_uppercase)
                + random.choice(string.ascii_uppercase)
                + f"{random.randint(0, 999):03d}"
            )
            if candidate not in Robot._used_names:
                Robot._used_names.add(candidate)
                return candidate
```

## Verification evidence (executed, on disk)
- tests/verify_run.log: 10/10 PASS — format regex, name stability, distinct robots, reset changes name + format + distinctness, 1000-robot uniqueness (set size 1000).
- python3 -m py_compile robot_name.py OK; import + instantiate OK.
