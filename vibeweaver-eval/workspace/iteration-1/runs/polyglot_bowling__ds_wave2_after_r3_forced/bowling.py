class BowlingGame:
    def __init__(self):
        self.rolls = []

    def roll(self, pins):
        if pins < 0 or pins > 10:
            raise ValueError("Pins must have a value from 0 to 10")
        if self._is_complete():
            raise IndexError("Cannot roll after game is over")

        frames = self._split_frames()
        if frames:
            frame_rolls = frames[-1]
            frame_index = len(frames) - 1
            if (
                len(frame_rolls) == 1
                and frame_rolls[0] != 10
                and frame_rolls[0] + pins > 10
            ):
                raise ValueError(
                    "Two rolls in a frame cannot score more than 10 points"
                )
            if (
                len(frame_rolls) == 2
                and frame_index == 9
                and frame_rolls[0] == 10
                and frame_rolls[1] != 10
                and frame_rolls[1] + pins > 10
            ):
                raise ValueError("Invalid fill balls")

        self.rolls.append(pins)

    def score(self):
        if not self._is_complete():
            raise IndexError("Game is not complete")
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
                i += 1
                if frame == 9:
                    i += 2
            else:
                i += 2
                if frame == 9 and i <= len(rolls) and rolls[i - 1] + rolls[i - 2] == 10:
                    i += 1
        return i == len(rolls)

    def _split_frames(self):
        rolls = self.rolls
        frames = []
        i = 0
        for frame in range(10):
            if i >= len(rolls):
                break
            if rolls[i] == 10:
                frames.append(rolls[i:i + 3] if frame == 9 else rolls[i:i + 1])
                i += 3 if frame == 9 else 1
            else:
                take = min(3, len(rolls) - i) if frame == 9 else min(2, len(rolls) - i)
                frames.append(rolls[i:i + take])
                i += take
        return frames
