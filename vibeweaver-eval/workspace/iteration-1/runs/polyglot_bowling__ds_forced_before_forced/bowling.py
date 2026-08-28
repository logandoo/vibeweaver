class BowlingGame:
    def __init__(self):
        self._frames = []
        self._current = []

    def roll(self, pins):
        if pins < 0 or pins > 10:
            raise ValueError("Pins must have a value from 0 to 10")
        if len(self._frames) == 10:
            raise ValueError("Cannot roll after the game is over")

        if len(self._frames) < 9:
            self._current.append(pins)
            if len(self._current) == 1 and pins == 10:
                self._frames.append(self._current)
                self._current = []
            elif len(self._current) == 2:
                if self._current[0] + pins > 10:
                    raise ValueError("Two rolls in a frame cannot score more than 10 points")
                self._frames.append(self._current)
                self._current = []
        else:
            self._current.append(pins)
            n = len(self._current)
            first = self._current[0]
            if n == 2:
                if first != 10 and first + pins > 10:
                    raise ValueError("Two rolls in the last frame cannot score more than 10 points")
            elif n == 3:
                second = self._current[1]
                if not (first == 10 or first + second == 10):
                    raise ValueError("Third roll is not allowed in an open last frame")
                if first == 10 and second != 10 and second + pins > 10:
                    raise ValueError("Bonus rolls after a strike in the last frame cannot score more than 10 points")
            if n == 3 or (n == 2 and first != 10 and first + pins < 10):
                self._frames.append(self._current)
                self._current = []

    def score(self):
        if len(self._frames) != 10 or self._current:
            raise ValueError("Game is not over")

        rolls = [r for frame in self._frames for r in frame]
        total = 0
        start = 0
        for i in range(9):
            frame = self._frames[i]
            if frame[0] == 10:
                total += 10 + rolls[start + 1] + rolls[start + 2]
            elif sum(frame) == 10:
                total += 10 + rolls[start + 2]
            else:
                total += sum(frame)
            start += len(frame)
        total += sum(self._frames[9])
        return total
