import re


class PhoneNumber:
    def __init__(self, number):
        digits = re.sub(r"\D", "", number)

        if len(digits) == 11:
            if digits[0] != "1":
                raise ValueError("11 digits must start with 1")
            digits = digits[1:]

        if len(digits) != 10:
            raise ValueError("number must be 10 or 11 digits")

        if digits[0] in "01":
            raise ValueError("area code cannot start with zero or one")

        if digits[3] in "01":
            raise ValueError("exchange code cannot start with zero or one")

        self.number = digits

    def area_code(self):
        return self.number[:3]

    def pretty_print(self):
        return f"({self.number[:3]}) {self.number[3:6]}-{self.number[6:]}"
