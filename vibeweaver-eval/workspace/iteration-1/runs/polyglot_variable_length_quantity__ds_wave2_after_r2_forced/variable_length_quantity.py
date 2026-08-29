def encode(numbers):
    encoded = []
    for number in numbers:
        chunks = [number & 0x7F]
        number >>= 7
        while number:
            chunks.insert(0, 0x80 | (number & 0x7F))
            number >>= 7
        encoded.extend(chunks)
    return encoded


def decode(bytes_):
    numbers = []
    value = 0
    in_sequence = False
    for byte in bytes_:
        value = (value << 7) | (byte & 0x7F)
        in_sequence = bool(byte & 0x80)
        if not in_sequence:
            numbers.append(value)
            value = 0
    if in_sequence:
        raise ValueError("incomplete sequence")
    return numbers
