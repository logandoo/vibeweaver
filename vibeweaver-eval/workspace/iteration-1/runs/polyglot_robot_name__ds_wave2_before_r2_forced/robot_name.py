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
