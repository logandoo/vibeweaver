import random
import string


class Robot:
    _assigned_names = set()

    def __init__(self):
        self._name = None

    @property
    def name(self):
        if self._name is None:
            self._name = self._generate_name()
        return self._name

    def reset(self):
        old_name = self._name
        if old_name is None:
            return
        self._name = self._generate_name()
        Robot._assigned_names.discard(old_name)

    @classmethod
    def _generate_name(cls):
        while True:
            candidate = (
                random.choice(string.ascii_uppercase)
                + random.choice(string.ascii_uppercase)
                + "".join(random.choice(string.digits) for _ in range(3))
            )
            if candidate not in cls._assigned_names:
                cls._assigned_names.add(candidate)
                return candidate
