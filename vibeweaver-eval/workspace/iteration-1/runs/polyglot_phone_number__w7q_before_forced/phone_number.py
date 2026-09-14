class PhoneNumber:
    def __init__(self, number):
        digits = ""
        letters = ""
        punctuations_allowed = "+-(). "
        for ch in number:
            if ch.isdigit():
                digits += ch
            elif ch.isalpha():
                letters += ch
            elif ch not in punctuations_allowed:
                raise ValueError("phone number must contain only digits, allowed punctuation, and letters are not permitted")

        if letters:
            raise ValueError("phone number must not contain letters")

        if len(digits) < 10:
            raise ValueError("must not be fewer than 10 digits")

        if len(digits) > 11:
            raise ValueError("must not be greater than 11 digits")

        if len(digits) == 11:
            if digits[0] != "1":
                raise ValueError("11 digits must start with 1")
            digits = digits[1:]

        # Now we have exactly 10 digits
        area_code = digits[0:3]
        exchange_code = digits[3:6]

        if area_code[0] == "0":
            raise ValueError("area code must not start with zero")
        if area_code[0] == "1":
            raise ValueError("area code must not start with one")
        if exchange_code[0] == "0":
            raise ValueError("exchange code must not start with zero")
        if exchange_code[0] == "1":
            raise ValueError("exchange code must not start with one")

        self.number = digits
        self.area_code = area_code
        self.parsed_number = digits

    def __str__(self):
        return self.number
