class BowlingGame:
    """Scores a single game of ten-pin bowling.

    Usage::

        game = BowlingGame()
        for pins in rolls:
            game.roll(pins)
        total = game.score()

    ``score()`` is only meaningful once the whole game has been rolled; the
    tenth frame may include one or two bonus ("fill") balls after a spare or
    a strike respectively.
    """

    def __init__(self):
        self.rolls = []

    def roll(self, pins):
        """Record one ball throw, knocking down ``pins`` pins."""
        self.rolls.append(pins)

    def score(self):
        """Return the total score for the completed game."""
        total = 0
        roll_index = 0
        for _ in range(10):
            if self.rolls[roll_index] == 10:
                # Strike: 10 plus the next two rolls.
                total += 10 + self.rolls[roll_index + 1] + self.rolls[roll_index + 2]
                roll_index += 1
            elif self.rolls[roll_index] + self.rolls[roll_index + 1] == 10:
                # Spare: 10 plus the next roll.
                total += 10 + self.rolls[roll_index + 2]
                roll_index += 2
            else:
                # Open frame: just the pins knocked down.
                total += self.rolls[roll_index] + self.rolls[roll_index + 1]
                roll_index += 2
        return total
