class BowlingGame:
    def __init__(self):
        self.rolls = []

    def roll(self, pins):
        self.rolls.append(pins)

    def score(self):
        total = 0
        index = 0
        for _ in range(10):
            if self.rolls[index] == 10:
                total += 10 + self.rolls[index + 1] + self.rolls[index + 2]
                index += 1
            elif self.rolls[index] + self.rolls[index + 1] == 10:
                total += 10 + self.rolls[index + 2]
                index += 2
            else:
                total += self.rolls[index] + self.rolls[index + 1]
                index += 2
        return total
