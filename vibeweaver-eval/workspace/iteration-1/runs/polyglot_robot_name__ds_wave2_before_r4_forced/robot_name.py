import random
import string


class Robot:
    _used_names = set()
    _NAMESPACE_SIZE = len(string.ascii_uppercase) ** 2 * 10 ** 3

    def __init__(self):
        self.name = self._new_name()

    def reset(self):
        self.name = self._new_name()

    def _new_name(self):
        if len(self._used_names) >= self._NAMESPACE_SIZE:
            raise RuntimeError("robot name space exhausted")
        while True:
            name = "".join(
                random.choice(charset)
                for charset in (string.ascii_uppercase,) * 2
                + (string.digits,) * 3
            )
            if name not in self._used_names:
                self._used_names.add(name)
                return name
