class PhoneNumber:
    def __init__(self, number):
        # Extract only digits
        digits = "".join(ch for ch in number if ch.isdigit())

        # Handle country code
        if len(digits) == 11:
            if digits[0] == "1":
                digits = digits[1:]
            else:
                raise ValueError("11-digit number must start with country code 1")

        # Validate length
        if len(digits) < 10:
            raise ValueError("must not be fewer than 10 digits")
        if len(digits) > 10:
            raise ValueError("more than 11 digits")

        # Validate area code (first 3 digits, NXX where N is 2-9)
        if digits[0] == "0":
            raise ValueError("area code cannot start with zero")
        if digits[0] == "1":
            raise ValueError("area code cannot start with one")

        # Validate exchange code (next 3 digits, NXX where N is 2-9)
        if digits[3] == "0":
            raise ValueError("exchange code cannot start with zero")
        if digits[3] == "1":
            raise ValueError("exchange code cannot start with one")

        # Check for letters
        if any(ch.isalpha() for ch in number):
            raise ValueError("letters not permitted")

        # Check for invalid punctuation
        valid_chars = set("+-(). ")
        for ch in number:
            if not ch.isdigit() and ch not in valid_chars:
                raise ValueError("punctuations not permitted")

        self.number = digits
        self.area_code = digits[:3]
        self.exchange_code = digits[3:6]
        self.subscriber_number = digits[6:]
