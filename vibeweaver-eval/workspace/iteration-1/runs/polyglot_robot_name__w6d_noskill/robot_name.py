import random
import string


class Robot:
    _used_names = set()

    def __init__(self):
        self._name = None

    @classmethod
    def _generate_name(cls):
        while True:
            letters = "".join(random.choice(string.ascii_uppercase) for _ in range(2))
            digits = "".join(random.choice(string.digits) for _ in range(3))
            name = letters + digits
            if name not in cls._used_names:
                cls._used_names.add(name)
                return name

    @property
    def name(self):
        if self._name is None:
            self._name = self._generate_name()
        return self._name

    def reset(self):
        if self._name is not None:
            self._used_names.discard(self._name)
        self._name = None
