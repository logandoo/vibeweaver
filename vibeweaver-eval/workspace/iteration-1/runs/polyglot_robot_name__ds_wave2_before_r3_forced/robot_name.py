import random
import string


class Robot:
    _used_names = set()

    def __init__(self):
        self.name = self._new_name()

    def reset(self):
        self.name = self._new_name()

    def _new_name(self):
        while True:
            name = (
                random.choice(string.ascii_uppercase)
                + random.choice(string.ascii_uppercase)
                + random.choice(string.digits)
                + random.choice(string.digits)
                + random.choice(string.digits)
            )
            if name not in self._used_names:
                self._used_names.add(name)
                return name
