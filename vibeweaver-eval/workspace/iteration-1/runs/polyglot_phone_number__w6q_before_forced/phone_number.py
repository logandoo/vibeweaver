class PhoneNumber:
    def __init__(self, number):
        # Extract only digits from the input
        digits = ''.join(ch for ch in number if ch.isdigit())

        # Handle 11-digit numbers (country code must be 1)
        if len(digits) == 11:
            if digits[0] == '1':
                digits = digits[1:]
            else:
                raise ValueError("11-digit number must start with country code 1")

        # Must be exactly 10 digits after cleaning
        if len(digits) < 10:
            raise ValueError("phone number must be 10 or 11 digits")
        if len(digits) > 10:
            raise ValueError("more than 11 digits")

        # Check for letters (already handled by digit extraction, but validate
        # that the original string didn't contain letters)
        if any(ch.isalpha() for ch in number):
            raise ValueError("phone number must not contain letters")

        # Check for invalid punctuation (anything that's not allowed)
        allowed_chars = set('0123456789+-(). ')
        for ch in number:
            if not ch.isdigit() and ch not in allowed_chars:
                raise ValueError("phone number must not contain punctuation")

        self.area_code = digits[:3]
        self.exchange_code = digits[3:6]
        self.subscriber_number = digits[6:]

        # Area code cannot start with 0 or 1
        if self.area_code[0] == '0':
            raise ValueError("area code cannot start with zero")
        if self.area_code[0] == '1':
            raise ValueError("area code cannot start with one")

        # Exchange code cannot start with 0 or 1
        if self.exchange_code[0] == '0':
            raise ValueError("exchange code cannot start with zero")
        if self.exchange_code[0] == '1':
            raise ValueError("exchange code cannot start with one")

        self.number = digits

    def pretty(self):
        return f"({self.area_code})-{self.exchange_code}-{self.subscriber_number}"

    def npx(self):
        return self.number

    def as_e164(self):
        return f"+1{self.number}"
