import re


class PhoneNumber:
    def __init__(self, number):
        allowed_chars = set("0123456789.()-+ ")
        if not all(c in allowed_chars for c in number):
            raise ValueError("invalid character in phone number")

        digits = re.sub(r"\D", "", number)

        if len(digits) == 11:
            if digits[0] == "1":
                digits = digits[1:]
            else:
                raise ValueError("11 digits must start with 1")
        elif len(digits) != 10:
            raise ValueError("incorrect number of digits")

        if digits[0] == "0":
            raise ValueError("area code cannot start with zero")
        if digits[0] == "1":
            raise ValueError("area code cannot start with one")
        if digits[3] == "0":
            raise ValueError("exchange code cannot start with zero")
        if digits[3] == "1":
            raise ValueError("exchange code cannot start with one")

        self.number = digits
