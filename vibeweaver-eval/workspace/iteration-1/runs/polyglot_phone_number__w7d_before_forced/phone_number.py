import re
from string import punctuation


class PhoneNumber:
    def __init__(self, number):
        self.number = self._clean(number)
        self.area_code = self.number[:3]
        self.exchange_code = self.number[3:6]
        self.subscriber_number = self.number[-4:]

    def pretty(self):
        return f"({self.area_code})-{self.exchange_code}-{self.subscriber_number}"

    def _clean(self, number):
        digits = re.sub(r"[() +\-.]", "", number)

        if any(char.isalpha() for char in digits):
            raise ValueError("letters not permitted")

        if any(char in punctuation for char in digits):
            raise ValueError("punctuations not permitted")

        return self._normalize(digits)

    def _normalize(self, number):
        if len(number) < 10:
            raise ValueError("must not be fewer than 10 digits")

        if len(number) > 11:
            raise ValueError("must not be greater than 11 digits")

        if len(number) == 11:
            if number[0] != "1":
                raise ValueError("11 digits must start with 1")
            number = number[1:]

        if number[0] == "0":
            raise ValueError("area code cannot start with zero")

        if number[0] == "1":
            raise ValueError("area code cannot start with one")

        if number[3] == "0":
            raise ValueError("exchange code cannot start with zero")

        if number[3] == "1":
            raise ValueError("exchange code cannot start with one")

        return number
