def encode(numbers):
    result = []
    for number in numbers:
        if not 0 <= number <= 0xFFFFFFFF:
            raise ValueError("number out of 32-bit unsigned range")
        if number == 0:
            result.append(0)
            continue
        groups = []
        while number > 0:
            groups.append(number & 0x7F)
            number >>= 7
        for i, group in enumerate(reversed(groups)):
            if i != len(groups) - 1:
                group |= 0x80
            result.append(group)
    return result


def decode(bytes_):
    result = []
    value = 0
    for byte in bytes_:
        value = (value << 7) | (byte & 0x7F)
        if not (byte & 0x80):
            if value > 0xFFFFFFFF:
                raise ValueError("number out of 32-bit unsigned range")
            result.append(value)
            value = 0
    if bytes_ and (bytes_[-1] & 0x80):
        raise ValueError("incomplete sequence")
    return result
