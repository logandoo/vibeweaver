import random
import string


class Robot:
    _used_names = set()

    def __init__(self):
        self.name = self._generate_name()

    def _generate_name(self):
        while True:
            candidate = (
                "".join(random.choices(string.ascii_uppercase, k=2))
                + "".join(random.choices(string.digits, k=3))
            )
            if candidate not in Robot._used_names:
                Robot._used_names.add(candidate)
                return candidate

    def reset(self):
        Robot._used_names.discard(self.name)
        self.name = self._generate_name()
