class BowlingGame:
    def __init__(self):
        self._rolls = []
        self._frame = 1
        self._ball = 1
        self._pins_this_frame = 0
        self._game_over = False

    def roll(self, pins):
        if self._game_over:
            raise ValueError("Cannot roll after the game is over")
        if pins < 0 or pins > 10:
            raise ValueError("Pins must have a value from 0 to 10")

        if self._frame < 10:
            if self._ball == 1:
                self._rolls.append(pins)
                if pins == 10:
                    self._frame += 1
                    self._ball = 1
                    self._pins_this_frame = 0
                else:
                    self._ball = 2
                    self._pins_this_frame = pins
            else:
                if self._pins_this_frame + pins > 10:
                    raise ValueError("A frame cannot total more than 10 pins")
                self._rolls.append(pins)
                self._frame += 1
                self._ball = 1
                self._pins_this_frame = 0
        else:
            if self._ball == 1:
                self._rolls.append(pins)
                self._pins_this_frame = pins
                self._ball = 2
            elif self._ball == 2:
                if self._pins_this_frame < 10 and self._pins_this_frame + pins > 10:
                    raise ValueError("A frame cannot total more than 10 pins")
                self._rolls.append(pins)
                if self._pins_this_frame == 10 or self._pins_this_frame + pins >= 10:
                    self._ball = 3
                else:
                    self._game_over = True
            else:
                last = self._rolls[-1]
                if self._pins_this_frame + last == 10 or last == 10:
                    remaining = 10
                else:
                    remaining = 10 - last
                if pins > remaining:
                    raise ValueError("A frame cannot total more than 10 pins")
                self._rolls.append(pins)
                self._game_over = True

    def score(self):
        if not self._game_over:
            raise ValueError("The game is not over yet")
        total = 0
        roll = 0
        for _ in range(10):
            if self._rolls[roll] == 10:
                total += 10 + self._rolls[roll + 1] + self._rolls[roll + 2]
                roll += 1
            elif self._rolls[roll] + self._rolls[roll + 1] == 10:
                total += 10 + self._rolls[roll + 2]
                roll += 2
            else:
                total += self._rolls[roll] + self._rolls[roll + 1]
                roll += 2
        return total
