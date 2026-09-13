import re


class PhoneNumber:
    def __init__(self, number):
        # Check for letters - must raise ValueError if present
        if re.search(r'[a-zA-Z]', number):
            raise ValueError("phone number cannot contain letters")

        # Check for invalid punctuation (anything that's not allowed)
        allowed_chars = set('+.() -')
        for char in number:
            if not char.isdigit() and char not in allowed_chars:
                raise ValueError("phone number cannot contain punctuation")

        # Remove all non-digit characters
        digits = re.sub(r'\D', '', number)

        # Handle country code
        if len(digits) == 11:
            if digits[0] == '1':
                digits = digits[1:]
            else:
                raise ValueError("11-digit number must start with 1")
        elif len(digits) == 10:
            pass
        else:
            raise ValueError("incorrect number of digits")

        # Area code (first digit) cannot be 0 or 1
        if digits[0] == '0':
            raise ValueError("area code cannot start with zero")
        if digits[0] == '1':
            raise ValueError("area code cannot start with one")

        # Exchange code (fourth digit) cannot be 0 or 1
        if digits[3] == '0':
            raise ValueError("exchange code cannot start with zero")
        if digits[3] == '1':
            raise ValueError("exchange code cannot start with one")

        self.number = digits
        self.area_code = digits[:3]
        self.exchange_code = digits[3:6]
        self.subscriber_number = digits[6:]

    def __str__(self):
        return self.number

    def __repr__(self):
        return f"PhoneNumber('{self.number}')"
