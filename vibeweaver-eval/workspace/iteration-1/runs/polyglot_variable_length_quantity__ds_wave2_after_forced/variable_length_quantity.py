def encode(numbers):
    encoded = []
    for number in numbers:
        chunks = []
        chunks.append(number % 0x80)
        number //= 0x80
        while number:
            chunks.insert(0, number % 0x80 + 0x80)
            number //= 0x80
        encoded.extend(chunks)
    return encoded


def decode(bytes_):
    numbers = []
    value = 0
    for byte in bytes_:
        value = (value << 7) | (byte & 0x7F)
        if byte & 0x80:
            continue
        numbers.append(value)
        value = 0
    if value or (bytes_ and bytes_[-1] & 0x80):
        raise ValueError("incomplete sequence")
    return numbers
