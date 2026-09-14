def encode(numbers):
    result = []
    for number in numbers:
        chunks = [number & 0x7F]
        number >>= 7
        while number:
            chunks.append(number & 0x7F)
            number >>= 7
        chunks.reverse()
        for i in range(len(chunks) - 1):
            chunks[i] |= 0x80
        result.extend(chunks)
    return result


def decode(bytes_):
    result = []
    value = 0
    in_progress = False
    for byte in bytes_:
        value = (value << 7) | (byte & 0x7F)
        in_progress = bool(byte & 0x80)
        if not in_progress:
            result.append(value)
            value = 0
    if in_progress:
        raise ValueError("incomplete byte sequence")
    return result
