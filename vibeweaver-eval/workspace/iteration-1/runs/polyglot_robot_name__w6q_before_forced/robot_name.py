import random
import string


class Robot:
    _used_names: set = set()

    def __init__(self):
        self._name = None

    @property
    def name(self):
        if self._name is None:
            self._name = self._generate_name()
        return self._name

    def reset(self):
        if self._name is not None:
            Robot._used_names.discard(self._name)
            self._name = None

    @classmethod
    def _generate_name(cls):
        while True:
            letters = ''.join(random.choices(string.ascii_uppercase, k=2))
            digits = f'{random.randint(0, 999):03d}'
            candidate = f'{letters}{digits}'
            if candidate not in cls._used_names:
                cls._used_names.add(candidate)
                return candidate
