class BowlingGame:
    def __init__(self):
        self._rolls = []

    def roll(self, pins):
        if pins < 0:
            raise ValueError("Pins cannot be negative")
        if pins > 10:
            raise ValueError("Pins cannot exceed 10")
        # Validate: sum of two throws in a frame cannot exceed 10 (except 10th frame fill balls)
        if len(self._rolls) >= 2:
            # Check if we're in the middle of a frame (not strike, not 10th frame)
            frame_rolls = self._get_current_frame_rolls()
            if len(frame_rolls) == 1 and frame_rolls[0] != 10:
                # Not a strike, so second throw can't exceed 10 - first throw
                if frame_rolls[0] + pins > 10:
                    raise ValueError("Too many pins for the frame")
        self._rolls.append(pins)

    def score(self):
        if not self._is_game_complete():
            raise ValueError("Game is not complete")
        score = 0
        roll_index = 0
        for frame in range(10):
            if self._is_strike(roll_index):
                score += 10 + self._strike_bonus(roll_index)
                roll_index += 1
            elif self._is_spare(roll_index):
                score += 10 + self._spare_bonus(roll_index)
                roll_index += 2
            else:
                score += self._frame_score(roll_index)
                roll_index += 2
        return score

    def _get_current_frame_rolls(self):
        return self._rolls[-2:] if len(self._rolls) >= 2 else self._rolls[:]

    def _is_strike(self, roll_index):
        return self._rolls[roll_index] == 10

    def _is_spare(self, roll_index):
        return (self._rolls[roll_index] + self._rolls[roll_index + 1] == 10)

    def _frame_score(self, roll_index):
        return self._rolls[roll_index] + self._rolls[roll_index + 1]

    def _strike_bonus(self, roll_index):
        return self._rolls[roll_index + 1] + self._rolls[roll_index + 2]

    def _spare_bonus(self, roll_index):
        return self._rolls[roll_index + 2]

    def _is_game_complete(self):
        roll_index = 0
        for frame in range(10):
            if self._is_strike(roll_index):
                roll_index += 1
            elif self._is_spare(roll_index):
                roll_index += 2
            else:
                roll_index += 2
            if frame < 9:
                if roll_index > len(self._rolls):
                    return False
        # 10th frame validation
        tenth_rolls = len(self._rolls) - (roll_index - 2) if roll_index >= 2 else len(self._rolls)
        # After 10 frames, roll_index points past the 10th frame start
        # We need to check the 10th frame specifically
        roll_index = 0
        for frame in range(9):
            if self._is_strike(roll_index):
                roll_index += 1
            elif self._is_spare(roll_index):
                roll_index += 2
            else:
                roll_index += 2
        # Now roll_index is at the start of the 10th frame
        if self._is_strike(roll_index):
            # Strike in 10th: need 2 more rolls
            return len(self._rolls) >= roll_index + 3
        elif self._is_spare(roll_index):
            # Spare in 10th: need 1 more roll (the bonus)
            return len(self._rolls) >= roll_index + 3
        else:
            # Open frame in 10th: need exactly 2 rolls
            return len(self._rolls) >= roll_index + 2
