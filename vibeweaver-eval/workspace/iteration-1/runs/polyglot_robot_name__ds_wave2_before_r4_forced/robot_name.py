import random
import string


class Robot:
    _used_names = set()
    _NAMESPACE_SIZE = 26 * 26 * 10 * 10 * 10

    def __init__(self):
        self.name = self._new_name()

    def reset(self):
        self.name = self._new_name()

    def _new_name(self):
        if len(self._used_names) >= self._NAMESPACE_SIZE:
            raise RuntimeError("robot name space exhausted")
        while True:
            name = (
                random.choice(string.ascii_uppercase)
                + random.choice(string.ascii_uppercase)
                + "".join(random.choice(string.digits) for _ in range(3))
            )
            if name not in self._used_names:
                self._used_names.add(name)
                return name
