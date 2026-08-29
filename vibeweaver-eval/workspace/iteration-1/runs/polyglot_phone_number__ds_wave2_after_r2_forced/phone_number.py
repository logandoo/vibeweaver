import re


class PhoneNumber:
    def __init__(self, raw_input):
        if re.search(r"[a-zA-Z]", raw_input):
            raise ValueError("letters not permitted")
        if re.search(r"[^0-9 .()+-]", raw_input):
            raise ValueError("punctuations not permitted")
        digits = re.sub(r"[^0-9]", "", raw_input)
        if len(digits) < 10:
            raise ValueError("must not be fewer than 10 digits")
        if len(digits) > 11:
            raise ValueError("must not be greater than 11 digits")
        if len(digits) == 11:
            if not digits.startswith("1"):
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
        self._number = digits

    @property
    def number(self):
        return self._number

    @property
    def area_code(self):
        return self._number[:3]

    def pretty(self):
        return f"({self._number[:3]})-{self._number[3:6]}-{self._number[6:]}"
