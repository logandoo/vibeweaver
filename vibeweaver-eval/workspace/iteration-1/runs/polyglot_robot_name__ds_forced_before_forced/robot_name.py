import random
import string


class Robot:
    used_names = set()

    def __init__(self):
        self._name = None

    @property
    def name(self):
        if self._name is None:
            self._name = self._generate_unique_name()
        return self._name

    def reset(self):
        self._name = None

    def _generate_unique_name(self):
        while True:
            name = (
                "".join(random.choices(string.ascii_uppercase, k=2))
                + "".join(random.choices(string.digits, k=3))
            )
            if name not in Robot.used_names:
                Robot.used_names.add(name)
                return name
