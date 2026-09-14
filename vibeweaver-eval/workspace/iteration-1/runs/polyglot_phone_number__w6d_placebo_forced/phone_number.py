import re


class PhoneNumber:
    def __init__(self, number):
        self.number = self._clean(number)
        self.area_code = self.number[:3]

    def pretty(self):
        return "({}) {}-{}".format(
            self.area_code, self.number[3:6], self.number[6:]
        )

    def _clean(self, number):
        digits = re.sub(r"[^\d]", "", number)
        if len(digits) == 11 and digits[0] == "1":
            digits = digits[1:]
        if len(digits) != 10:
            raise ValueError("Invalid phone number")
        if digits[0] in "01" or digits[3] in "01":
            raise ValueError("Invalid phone number")
        return digits
