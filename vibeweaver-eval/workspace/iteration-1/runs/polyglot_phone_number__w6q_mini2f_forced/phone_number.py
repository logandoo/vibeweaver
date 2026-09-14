import re


class PhoneNumber:
    def __init__(self, number):
        cleaned = re.sub(r'\D', '', number)

        if len(cleaned) == 11:
            if cleaned[0] == '1':
                cleaned = cleaned[1:]
            else:
                raise ValueError("Invalid phone number")
        elif len(cleaned) != 10:
            raise ValueError("Invalid phone number")

        if cleaned[0] == '0':
            raise ValueError("Invalid phone number")
        if cleaned[0] == '1':
            raise ValueError("Invalid phone number")
        if cleaned[3] == '0':
            raise ValueError("Invalid phone number")
        if cleaned[3] == '1':
            raise ValueError("Invalid phone number")

        self.number = cleaned
        self.area_code = cleaned[:3]

    def pretty(self):
        return f"({self.area_code}) {self.number[3:6]}-{self.number[6:]}"
