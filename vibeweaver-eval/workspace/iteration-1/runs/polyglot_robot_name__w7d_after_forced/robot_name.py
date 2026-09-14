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
