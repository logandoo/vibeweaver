class BowlingGame:
    def __init__(self):
        self.rolls = []

    def roll(self, pins):
        if pins < 0:
            raise IndexError("Negative roll is invalid")
        if pins > 10:
            raise IndexError("Pin count exceeds pins on the lane")
        context = self._next_roll_context()
        if context == "over":
            raise IndexError("Cannot roll after game is over")
        if context in ("second", "tenth_second"):
            if self.rolls[-1] + pins > 10:
                raise IndexError("Pin count exceeds pins on the lane")
        elif context == "strike_bonus_2":
            if self.rolls[-1] != 10 and self.rolls[-1] + pins > 10:
                raise IndexError("Pin count exceeds pins on the lane")
        self.rolls.append(pins)

    def score(self):
        if self._next_roll_context() != "over":
            raise IndexError("Score cannot be taken until the end of the game")
        rolls = self.rolls
        total = 0
        i = 0
        for _ in range(10):
            if rolls[i] == 10:
                total += 10 + rolls[i + 1] + rolls[i + 2]
                i += 1
            else:
                first, second = rolls[i], rolls[i + 1]
                if first + second == 10:
                    total += 10 + rolls[i + 2]
                else:
                    total += first + second
                i += 2
        return total

    def _next_roll_context(self):
        rolls = self.rolls
        i = 0
        for frame in range(10):
            if i >= len(rolls):
                return "first"
            first = rolls[i]
            if frame == 9:
                remaining = len(rolls) - i
                if first == 10:
                    if remaining >= 3:
                        return "over"
                    return "strike_bonus_1" if remaining == 1 else "strike_bonus_2"
                if remaining == 1:
                    return "tenth_second"
                if remaining == 2:
                    if first + rolls[i + 1] < 10:
                        return "over"
                    return "spare_bonus"
                return "over"
            if first == 10:
                i += 1
            else:
                if i + 1 >= len(rolls):
                    return "second"
                i += 2
        return "over"
