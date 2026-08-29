class BowlingGame:
    def __init__(self):
        self.rolls = []

    def roll(self, pins):
        if pins < 0 or pins > 10:
            raise ValueError("Pins must be between 0 and 10")
        if self._is_game_over(self.rolls):
            raise ValueError("Cannot roll after the game is over")
        candidate = self.rolls + [pins]
        if self._build_frames(candidate) is None:
            raise ValueError("Invalid roll sequence")
        self.rolls.append(pins)

    def score(self):
        if not self._is_game_over(self.rolls):
            raise ValueError("Game is not complete")
        score = 0
        index = 0
        for _ in range(10):
            if self.rolls[index] == 10:
                score += 10 + self.rolls[index + 1] + self.rolls[index + 2]
                index += 1
            elif self.rolls[index] + self.rolls[index + 1] == 10:
                score += 10 + self.rolls[index + 2]
                index += 2
            else:
                score += self.rolls[index] + self.rolls[index + 1]
                index += 2
        return score

    def _build_frames(self, rolls):
        frames = []
        index = 0
        while index < len(rolls):
            if len(frames) == 10:
                return None
            if len(frames) == 9:
                tenth = rolls[index:]
                if len(tenth) > 3 or not self._valid_tenth(tenth):
                    return None
                frames.append(tenth)
                return frames
            if rolls[index] == 10:
                frames.append([10])
                index += 1
            elif index + 1 >= len(rolls):
                frames.append([rolls[index]])
                index = len(rolls)
            elif rolls[index] + rolls[index + 1] > 10:
                return None
            else:
                frames.append([rolls[index], rolls[index + 1]])
                index += 2
        return frames

    def _valid_tenth(self, tenth):
        first = tenth[0]
        if first == 10:
            if (
                len(tenth) == 3
                and tenth[1] < 10
                and tenth[1] + tenth[2] > 10
            ):
                return False
            return True
        if len(tenth) == 1:
            return True
        if first + tenth[1] > 10:
            return False
        if first + tenth[1] < 10:
            return len(tenth) == 2
        return len(tenth) in (2, 3)

    def _is_game_over(self, rolls):
        frames = self._build_frames(rolls)
        if frames is None or len(frames) < 10:
            return False
        tenth = frames[9]
        if tenth[0] == 10:
            return len(tenth) == 3
        if len(tenth) == 1:
            return False
        if tenth[0] + tenth[1] == 10:
            return len(tenth) == 3
        return True
