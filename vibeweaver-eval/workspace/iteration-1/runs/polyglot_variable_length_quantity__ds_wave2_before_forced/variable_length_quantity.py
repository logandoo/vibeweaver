def encode(numbers):
    encoded = []
    for number in numbers:
        if number == 0:
            encoded.append(0)
            continue
        chunks = []
        while number:
            chunks.append(number & 0x7F)
            number >>= 7
        for index, chunk in enumerate(reversed(chunks)):
            if index < len(chunks) - 1:
                chunk |= 0x80
            encoded.append(chunk)
    return encoded


def decode(bytes_):
    decoded = []
    value = 0
    in_sequence = False
    for byte in bytes_:
        value = (value << 7) | (byte & 0x7F)
        in_sequence = True
        if byte & 0x80:
            continue
        decoded.append(value)
        value = 0
        in_sequence = False
    if in_sequence:
        raise ValueError("incomplete sequence")
    return decoded
