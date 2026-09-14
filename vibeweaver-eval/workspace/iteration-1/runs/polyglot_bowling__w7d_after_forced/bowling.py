class BowlingGame:
    def __init__(self):
        self.frames = []

    def roll(self, pins):
        if not isinstance(pins, int) or isinstance(pins, bool):
            raise ValueError("pins must be an integer")
        if pins < 0 or pins > 10:
            raise ValueError("pins must be between 0 and 10")

        if self._is_complete():
            raise ValueError("cannot roll: the game is complete")

        if not self.frames or self._frame_complete(len(self.frames) - 1):
            self.frames.append([])

        self._validate_roll(len(self.frames) - 1, pins)
        self.frames[-1].append(pins)

    def score(self):
        if not self._is_complete():
            raise ValueError("cannot score: the game is not complete")

        rolls = [pins for frame in self.frames for pins in frame]
        total = 0
        i = 0
        for _ in range(10):
            if rolls[i] == 10:
                total += 10 + rolls[i + 1] + rolls[i + 2]
                i += 1
            elif rolls[i] + rolls[i + 1] == 10:
                total += 10 + rolls[i + 2]
                i += 2
            else:
                total += rolls[i] + rolls[i + 1]
                i += 2
        return total

    def _is_complete(self):
        return len(self.frames) == 10 and self._frame_complete(9)

    def _frame_complete(self, index):
        rolls = self.frames[index]
        if index < 9:
            return (len(rolls) == 1 and rolls[0] == 10) or len(rolls) == 2
        if len(rolls) == 3:
            return True
        if len(rolls) == 2:
            if rolls[0] == 10:
                return False
            return rolls[0] + rolls[1] < 10
        return False

    def _validate_roll(self, index, pins):
        rolls = self.frames[index]
        if index < 9:
            if len(rolls) == 1 and rolls[0] + pins > 10:
                raise ValueError("two rolls in a frame cannot exceed 10")
            return
        if len(rolls) == 0:
            return
        if len(rolls) == 1:
            if rolls[0] != 10 and rolls[0] + pins > 10:
                raise ValueError("two rolls in a frame cannot exceed 10")
            return
        first, second = rolls
        if first == 10 and second != 10 and second + pins > 10:
            raise ValueError("bonus rolls cannot exceed 10")
