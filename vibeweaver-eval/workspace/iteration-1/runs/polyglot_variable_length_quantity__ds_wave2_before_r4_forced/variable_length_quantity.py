def encode(numbers):
    result = []
    for number in numbers:
        chunks = [number & 0x7F]
        number >>= 7
        while number:
            chunks.append((number & 0x7F) | 0x80)
            number >>= 7
        result.extend(reversed(chunks))
    return result


def decode(bytes_):
    numbers = []
    current = 0
    for byte in bytes_:
        current = (current << 7) | (byte & 0x7F)
        if not (byte & 0x80):
            numbers.append(current)
            current = 0
    if bytes_ and bytes_[-1] & 0x80:
        raise ValueError("incomplete byte sequence")
    return numbers
