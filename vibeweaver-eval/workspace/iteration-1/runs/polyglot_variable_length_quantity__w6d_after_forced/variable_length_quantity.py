def encode(numbers):
    result = []
    for number in numbers:
        chunk = number & 0x7F
        number >>= 7
        chunks = [chunk]
        while number:
            chunks.append((number & 0x7F) | 0x80)
            number >>= 7
        result.extend(reversed(chunks))
    return result


def decode(bytes_):
    result = []
    value = 0
    for byte in bytes_:
        value = (value << 7) | (byte & 0x7F)
        if byte & 0x80:
            continue
        result.append(value)
        value = 0
    if bytes_ and bytes_[-1] & 0x80:
        raise ValueError("incomplete sequence")
    return result
