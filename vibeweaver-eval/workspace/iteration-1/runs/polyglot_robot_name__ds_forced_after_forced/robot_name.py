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
