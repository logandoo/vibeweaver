class BowlingGame:
    def __init__(self):
        self.rolls = []

    def roll(self, pins):
        if pins < 0 or pins > 10:
            raise ValueError("Pins must be between 0 and 10")
        if _game_over(self.rolls):
            raise ValueError("Cannot roll after the game is over")
        candidate = self.rolls + [pins]
        if not _valid_prefix(candidate):
            raise ValueError("Invalid roll for the current frame")
        self.rolls.append(pins)

    def score(self):
        frames = _build_frames(self.rolls)
        if frames is None or len(frames) != 10:
            raise ValueError("Game is not complete")
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


def _game_over(rolls):
    frames = _build_frames(rolls)
    return frames is not None and len(frames) == 10


def _valid_prefix(rolls):
    i = 0
    frame_count = 0
    while frame_count < 10:
        if i >= len(rolls):
            return True
        if rolls[i] == 10:
            if frame_count == 9:
                rest = len(rolls) - i - 1
                if rest > 2:
                    return False
                if rest == 2 and rolls[i + 1] != 10 and rolls[i + 1] + rolls[i + 2] > 10:
                    return False
                i += 1 + rest
            else:
                i += 1
        else:
            if i + 1 >= len(rolls):
                return True
            if rolls[i] + rolls[i + 1] > 10:
                return False
            if frame_count == 9 and rolls[i] + rolls[i + 1] == 10:
                if i + 2 >= len(rolls):
                    return True
                i += 3
            else:
                i += 2
        frame_count += 1
    return i == len(rolls)


def _build_frames(rolls):
    frames = []
    i = 0
    while len(frames) < 10:
        if i >= len(rolls):
            return None
        if rolls[i] == 10:
            if len(frames) == 9:
                if i + 2 >= len(rolls):
                    return None
                tenth = rolls[i:i + 3]
                if tenth[1] != 10 and tenth[1] + tenth[2] > 10:
                    return None
                frames.append(list(tenth))
                i += 3
            else:
                frames.append([rolls[i]])
                i += 1
        else:
            if i + 1 >= len(rolls):
                return None
            frame = [rolls[i], rolls[i + 1]]
            if rolls[i] + rolls[i + 1] > 10:
                return None
            if len(frames) == 9 and rolls[i] + rolls[i + 1] == 10:
                if i + 2 >= len(rolls):
                    return None
                frames.append(frame + [rolls[i + 2]])
                i += 3
            else:
                frames.append(frame)
                i += 2
    if i != len(rolls):
        return None
    return frames
