import re


class PhoneNumber:
    def __init__(self, number):
        cleaned = self._clean(number)
        self.number = cleaned
        self.area_code = cleaned[:3]

    def pretty(self):
        return f"({self.number[:3]})-{self.number[3:6]}-{self.number[6:]}"

    @staticmethod
    def _clean(number):
        digits = re.sub(r"[().+\-\s]", "", number)
        if re.search(r"[A-Za-z]", digits):
            raise ValueError("letters not permitted")
        if re.search(r"\D", digits):
            raise ValueError("punctuations not permitted")
        if len(digits) < 10:
            raise ValueError("must not be fewer than 10 digits")
        if len(digits) > 11:
            raise ValueError("must not be greater than 11 digits")
        if len(digits) == 11:
            if digits[0] != "1":
                raise ValueError("11 digits must start with 1")
            digits = digits[1:]
        if digits[0] == "0":
            raise ValueError("area code cannot start with zero")
        if digits[0] == "1":
            raise ValueError("area code cannot start with one")
        if digits[3] == "0":
            raise ValueError("exchange code cannot start with zero")
        if digits[3] == "1":
            raise ValueError("exchange code cannot start with one")
        return digits
