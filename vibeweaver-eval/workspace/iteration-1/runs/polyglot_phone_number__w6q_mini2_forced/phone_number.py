class PhoneNumber:
    def __init__(self, number):
        digits = "".join(c for c in number if c.isdigit())

        if len(digits) == 11:
            if digits[0] == "1":
                digits = digits[1:]
            else:
                self.number = "invalid"
                return
        elif len(digits) != 10:
            self.number = "invalid"
            return

        if len(digits) != 10:
            self.number = "invalid"
            return

        if digits[0] == "0" or digits[0] == "1":
            self.number = "invalid"
            return

        if digits[3] == "0" or digits[3] == "1":
            self.number = "invalid"
            return

        self.number = digits
