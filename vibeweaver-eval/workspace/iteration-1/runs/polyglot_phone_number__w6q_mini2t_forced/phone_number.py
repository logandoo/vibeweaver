import re


class PhoneNumber:
    def __init__(self, number):
        # Check for letters
        if re.search(r'[a-zA-Z]', number):
            raise ValueError("letters not permitted")

        # Check for invalid punctuation (allowed: +, -, ., (, ), space)
        if re.search(r'[^0-9\s\-\.\+\(\)\w]', number):
            raise ValueError("punctuations not permitted")

        # Extract only digits
        digits = re.sub(r'\D', '', number)

        # Handle country code
        if len(digits) == 11:
            if not digits.startswith('1'):
                raise ValueError("11 digits must start with 1")
            digits = digits[1:]
        elif len(digits) > 11:
            raise ValueError("must not be greater than 11 digits")
        elif len(digits) < 10:
            raise ValueError("must not be fewer than 10 digits")

        # Now digits should be exactly 10
        self._number = digits

        # Validate area code and exchange code
        area_code = self._number[:3]
        exchange_code = self._number[3:6]

        if area_code[0] == '0':
            raise ValueError("area code cannot start with zero")
        if area_code[0] == '1':
            raise ValueError("area code cannot start with one")
        if exchange_code[0] == '0':
            raise ValueError("exchange code cannot start with zero")
        if exchange_code[0] == '1':
            raise ValueError("exchange code cannot start with one")

    @property
    def number(self):
        return self._number

    @property
    def area_code(self):
        return self._number[:3]

    def pretty(self):
        return f"({self._number[:3]})-{self._number[3:6]}-{self._number[6:]}"
