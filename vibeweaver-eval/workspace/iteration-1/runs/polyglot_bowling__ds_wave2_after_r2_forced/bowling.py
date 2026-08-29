class BowlingGame:
    def __init__(self):
        self.rolls = []

    def roll(self, pins):
        if pins < 0 or pins > 10:
            raise ValueError("Pins must have a value from 0 to 10")
        if self._is_complete():
            raise IndexError("Cannot roll after the game is over")
        first = self._next_roll_constraint()
        if first is not None and first + pins > 10:
            raise ValueError("Two rolls in a frame cannot score more than 10 points")
        self.rolls.append(pins)

    def score(self):
        if not self._is_complete():
            raise IndexError("Score cannot be taken until the end of the game")
        total = 0
        i = 0
        for _ in range(10):
            if self.rolls[i] == 10:
                total += 10 + self.rolls[i + 1] + self.rolls[i + 2]
                i += 1
            elif self.rolls[i] + self.rolls[i + 1] == 10:
                total += 10 + self.rolls[i + 2]
                i += 2
            else:
                total += self.rolls[i] + self.rolls[i + 1]
                i += 2
        return total

    def _is_complete(self):
        rolls = self.rolls
        i = 0
        for frame in range(10):
            if i >= len(rolls):
                return False
            if rolls[i] == 10:
                if frame == 9:
                    return len(rolls) >= i + 3
                i += 1
            else:
                if i + 1 >= len(rolls):
                    return False
                if frame == 9:
                    return (
                        len(rolls) >= i + 3
                        if rolls[i] + rolls[i + 1] == 10
                        else len(rolls) >= i + 2
                    )
                i += 2
        return True

    def _next_roll_constraint(self):
        rolls = self.rolls
        n = len(rolls)
        i = 0
        for frame in range(10):
            if i >= n:
                return None
            if rolls[i] == 10:
                if frame == 9:
                    if i + 1 >= n:
                        return None
                    if i + 2 >= n:
                        return rolls[i + 1] if rolls[i + 1] != 10 else None
                    return None
                i += 1
            else:
                if i + 1 >= n:
                    return rolls[i]
                if frame == 9:
                    if rolls[i] + rolls[i + 1] == 10:
                        if i + 2 >= n:
                            return None
                        return None
                    i += 2
                else:
                    i += 2
        return None
