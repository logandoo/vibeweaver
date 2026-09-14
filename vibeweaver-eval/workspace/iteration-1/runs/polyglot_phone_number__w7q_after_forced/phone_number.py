import re


class PhoneNumber:
    def __init__(self, number):
        # Extract only digits and letters (to detect invalid alpha chars)
        letters = re.findall(r'[a-zA-Z]', number)
        if letters:
            raise ValueError("letters not permitted")

        # Check for invalid punctuation: anything that's not allowed
        # Allowed: digits, spaces, +, -, ., (, )
        cleaned = re.sub(r'[^0-9+\-().\s]', '', number)
        if cleaned != number:
            # There were disallowed characters
            raise ValueError("punctuations not permitted")

        # Extract only digits
        digits = re.sub(r'\D', '', number)

        # Validate length
        if len(digits) < 10:
            raise ValueError("must not be fewer than 10 digits")
        if len(digits) > 11:
            raise ValueError("must not be greater than 11 digits")

        if len(digits) == 11:
            if digits[0] == '1':
                digits = digits[1:]
            else:
                raise ValueError("11 digits must start with 1")

        # Now we have exactly 10 digits
        # Validate area code (first digit, index 0)
        if digits[0] == '0':
            raise ValueError("area code cannot start with zero")
        if digits[0] == '1':
            raise ValueError("area code cannot start with one")

        # Validate exchange code (fourth digit, index 3)
        if digits[3] == '0':
            raise ValueError("exchange code cannot start with zero")
        if digits[3] == '1':
            raise ValueError("exchange code cannot start with one")

        self._number = digits

    @property
    def number(self):
        return self._number

    @property
    def area_code(self):
        return self._number[:3]

    def pretty(self):
        n = self._number
        return f"({n[:3]})-{n[3:6]}-{n[6:]}"
