def encode(numbers):
    output = []
    for number in numbers:
        if not isinstance(number, int):
            raise ValueError("integer required")
        if number < 0:
            raise ValueError("negative integer")
        if number > 0xFFFFFFFF:
            raise ValueError("integer too large")
        sequence = [number & 0x7F]
        number >>= 7
        while number:
            sequence.append(0x80 | (number & 0x7F))
            number >>= 7
        output.extend(reversed(sequence))
    return output


def decode(bytes_):
    values = []
    value = 0
    count = 0
    for byte in bytes_:
        value = (value << 7) | (byte & 0x7F)
        count += 1
        if byte & 0x80 == 0:
            values.append(value)
            value = 0
            count = 0
    if count:
        raise ValueError("incomplete sequence")
    return values
