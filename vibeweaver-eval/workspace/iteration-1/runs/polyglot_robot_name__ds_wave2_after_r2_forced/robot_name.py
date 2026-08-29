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

    @classmethod
    def _generate_name(cls):
        while True:
            candidate = (
                random.choice(string.ascii_uppercase)
                + random.choice(string.ascii_uppercase)
                + f"{random.randrange(1000):03d}"
            )
            if candidate not in cls._used_names:
                cls._used_names.add(candidate)
                return candidate
