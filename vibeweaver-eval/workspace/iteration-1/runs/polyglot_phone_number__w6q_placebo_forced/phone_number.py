class PhoneNumber:
    def __init__(self, number):
        self.clean(number)

    def clean(self, number):
        # Extract only digits and letters
        digits = ""
        letters = ""
        for ch in number:
            if ch.isdigit():
                digits += ch
            elif ch.isalpha():
                letters += ch

        # Letters are not allowed
        if letters:
            raise ValueError("phone number cannot contain letters")

        # Check for invalid punctuation (anything that is not a digit, letter,
        # or one of the allowed punctuation chars: + - . ( ) space)
        allowed_punct = set("+-(). ")
        for ch in number:
            if not ch.isdigit() and not ch.isalpha() and ch not in allowed_punct:
                raise ValueError("phone number cannot contain punctuation")

        # Now handle the digit count
        if len(digits) < 10:
            raise ValueError("must not be fewer than 10 digits")
        if len(digits) > 11:
            raise ValueError("must not be greater than 11 digits")

        if len(digits) == 11:
            if digits[0] != "1":
                raise ValueError("11 digits must start with 1")
            digits = digits[1:]

        # Now digits should be exactly 10
        # Area code (NXX): first digit N must be 2-9
        if digits[0] == "0":
            raise ValueError("area code cannot start with zero")
        if digits[0] == "1":
            raise ValueError("area code cannot start with one")

        # Exchange code (NXX): first digit N must be 2-9
        if digits[3] == "0":
            raise ValueError("exchange code cannot start with zero")
        if digits[3] == "1":
            raise ValueError("exchange code cannot start with one")

        self.number = digits
        return self.number
