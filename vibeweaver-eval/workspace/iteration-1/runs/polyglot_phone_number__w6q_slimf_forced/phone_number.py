class PhoneNumber:
    def __init__(self, number):
        # Extract only digits
        digits = ''.join(ch for ch in number if ch.isdigit())

        # Handle 11-digit numbers with country code '1'
        if len(digits) == 11:
            if digits[0] == '1':
                digits = digits[1:]
            else:
                raise ValueError("Invalid phone number")

        # Must be exactly 10 digits
        if len(digits) != 10:
            raise ValueError("Invalid phone number")

        # Check for letters or invalid punctuation in original string
        allowed_prefix_chars = {'+', '(', ')', '-', '.', ' '}
        for ch in number:
            if ch.isalpha():
                raise ValueError("Invalid phone number")
            if not (ch.isdigit() or ch in allowed_prefix_chars):
                raise ValueError("Invalid phone number")

        area_code = digits[:3]
        exchange_code = digits[3:6]

        # Area code first digit must be 2-9
        if area_code[0] < '2':
            raise ValueError("Invalid phone number")

        # Exchange code first digit must be 2-9
        if exchange_code[0] < '2':
            raise ValueError("Invalid phone number")

        self._number = digits
        self._area_code = area_code

    @property
    def number(self):
        return self._number

    @property
    def area_code(self):
        return self._area_code

    def pretty(self):
        return f"({self._area_code}) {self._number[3:6]}-{self._number[6:]}"
