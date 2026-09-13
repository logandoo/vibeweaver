class PhoneNumber:
    def __init__(self, number):
        digits = [c for c in str(number) if c.isdigit()]

        if any(c.isalpha() for c in str(number)):
            raise ValueError("letters not permitted")
        if any(not c.isdigit() and not c.isspace() and c not in "+()-." for c in str(number)):
            raise ValueError("punctuations not permitted")

        if len(digits) == 11:
            if digits[0] != "1":
                raise ValueError("11 digits must start with 1")
            digits = digits[1:]
        elif len(digits) < 10:
            raise ValueError("incorrect number of digits")
        elif len(digits) > 11:
            raise ValueError("more than 11 digits")

        if digits[0] == "0":
            raise ValueError("area code cannot start with zero")
        if digits[0] == "1":
            raise ValueError("area code cannot start with one")
        if digits[3] == "0":
            raise ValueError("exchange code cannot start with zero")
        if digits[3] == "1":
            raise ValueError("exchange code cannot start with one")

        self._number = "".join(digits)

    @property
    def number(self):
        return self._number

    def area_code(self):
        return self._number[:3]

    def pretty(self):
        return "({}) {}-{}".format(
            self._number[:3], self._number[3:6], self._number[6:]
        )
