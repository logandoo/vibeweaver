class PhoneNumber:
    _allowed_punctuation = set(" ()-+.")

    def __init__(self, number):
        self._number = self._clean(number)

    @property
    def number(self):
        return self._number

    @property
    def area_code(self):
        return self._number[:3]

    def pretty(self):
        return f"({self._number[:3]})-{self._number[3:6]}-{self._number[6:]}"

    def _clean(self, number):
        digits = []
        for char in number:
            if char.isdigit():
                digits.append(char)
            elif char in self._allowed_punctuation:
                continue
            elif char.isalpha():
                raise ValueError("letters not permitted")
            else:
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

        return "".join(digits)
