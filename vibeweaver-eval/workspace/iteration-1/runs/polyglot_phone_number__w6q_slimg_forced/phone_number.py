class PhoneNumber:
    def __init__(self, number):
        # Strip allowed punctuation characters: + - . ( ) and spaces
        digits = ""
        for ch in number:
            if ch.isdigit():
                digits += ch
            elif ch in "+-.() ":
                continue
            else:
                raise ValueError(f"invalid character '{ch}'")

        # Handle country code
        if len(digits) == 11:
            if digits[0] == "1":
                digits = digits[1:]
            else:
                raise ValueError("11-digit number must start with 1")
        elif len(digits) == 10:
            pass
        else:
            raise ValueError("invalid number length")

        # Validate NANP rules: NXX-NXX-XXXX where N is 2-9
        area_code = digits[0:3]
        exchange_code = digits[3:6]

        if area_code[0] == "0":
            raise ValueError("area code cannot start with 0")
        if area_code[0] == "1":
            raise ValueError("area code cannot start with 1")
        if exchange_code[0] == "0":
            raise ValueError("exchange code cannot start with 0")
        if exchange_code[0] == "1":
            raise ValueError("exchange code cannot start with 1")

        self.number = digits
