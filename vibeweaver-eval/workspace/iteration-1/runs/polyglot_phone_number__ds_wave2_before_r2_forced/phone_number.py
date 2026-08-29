class PhoneNumber:
    def __init__(self, number):
        self.number = self._clean(number)

    def _clean(self, number):
        digits = "".join(char for char in number if char.isdigit())

        if len(digits) == 11 and digits[0] == "1":
            digits = digits[1:]

        if len(digits) != 10:
            raise ValueError("incorrect number of digits")

        if digits[0] in "01":
            raise ValueError("area code cannot start with zero or one")

        if digits[3] in "01":
            raise ValueError("exchange code cannot start with zero or one")

        return digits

    def area_code(self):
        return self.number[:3]

    def exchange_code(self):
        return self.number[3:6]

    def pretty(self):
        return f"({self.number[:3]})-{self.number[3:6]}-{self.number[6:]}"
