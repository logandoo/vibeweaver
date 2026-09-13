import re
from string import punctuation


class PhoneNumber:
    def __init__(self, number):
        cleaned = self._clean(number)
        self.number = cleaned
        self.area_code = cleaned[:3]
        self.exchange_code = cleaned[3:6]
        self.subscriber_number = cleaned[6:]

    def pretty(self):
        return f"({self.area_code})-{self.exchange_code}-{self.subscriber_number}"

    @staticmethod
    def _clean(number):
        digits = re.sub(r"[() +.\-]", "", number)

        if any(char.isalpha() for char in digits):
            raise ValueError("letters not permitted")

        if any(char in punctuation for char in digits):
            raise ValueError("punctuations not permitted")

        if not digits.isascii():
            raise ValueError("punctuations not permitted")

        if len(digits) == 11:
            if not digits.startswith("1"):
                raise ValueError("11 digits must start with 1")
            digits = digits[1:]

        if len(digits) < 10:
            raise ValueError("must not be fewer than 10 digits")

        if len(digits) > 11:
            raise ValueError("must not be greater than 11 digits")

        if digits[0] == "0":
            raise ValueError("area code cannot start with zero")
        if digits[0] == "1":
            raise ValueError("area code cannot start with one")
        if digits[3] == "0":
            raise ValueError("exchange code cannot start with zero")
        if digits[3] == "1":
            raise ValueError("exchange code cannot start with one")

        return digits
