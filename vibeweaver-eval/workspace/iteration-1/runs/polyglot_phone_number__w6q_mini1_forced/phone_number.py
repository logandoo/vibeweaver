class PhoneNumber:
    def __init__(self, number):
        self.number = self.clean(number)

    def clean(self, number):
        # Extract only digits
        digits = "".join(ch for ch in number if ch.isdigit())

        # Handle country code
        if len(digits) == 11:
            if digits[0] == "1":
                digits = digits[1:]
            else:
                raise ValueError("11-digit number must start with 1")

        if len(digits) != 10:
            raise ValueError("incorrect number of digits")

        # Area code: first digit must be 2-9
        if digits[0] == "0":
            raise ValueError("area code cannot start with zero")
        if digits[0] == "1":
            raise ValueError("area code cannot start with one")

        # Exchange code: fourth digit must be 2-9
        if digits[3] == "0":
            raise ValueError("exchange code cannot start with zero")
        if digits[3] == "1":
            raise ValueError("exchange code cannot start with one")

        return digits
