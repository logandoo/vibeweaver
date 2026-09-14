import string


class PhoneNumber:
    def __init__(self, number):
        # Check for letters
        for ch in number:
            if ch.isalpha():
                raise ValueError("letters not permitted")

        # Check for invalid punctuation (anything that's not digits, spaces,
        # +, -, ., (, ) which are all allowed)
        allowed_chars = set(string.digits + " +-.()")
        for ch in number:
            if ch not in allowed_chars:
                raise ValueError("punctuations not permitted")

        # Strip allowed punctuation to get raw digits
        digits = "".join(ch for ch in number if ch.isdigit())

        # Handle country code
        if len(digits) == 11:
            if digits[0] == "1":
                digits = digits[1:]
            else:
                raise ValueError("11 digits must start with 1")
        elif len(digits) == 10:
            pass
        else:
            raise ValueError("incorrect number of digits")

        # Now digits should be exactly 10
        if len(digits) != 10:
            raise ValueError("incorrect number of digits")

        # Area code (first digit) must be 2-9
        if digits[0] < "2":
            raise ValueError("area code cannot start with zero")
        if digits[0] < "2":
            raise ValueError("area code cannot start with one")

        # Exchange code (fourth digit) must be 2-9
        if digits[3] == "0":
            raise ValueError("exchange code cannot start with zero")
        if digits[3] == "1":
            raise ValueError("exchange code cannot start with one")

        self.number = digits
