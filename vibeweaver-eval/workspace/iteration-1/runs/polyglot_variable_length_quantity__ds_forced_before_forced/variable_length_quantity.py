def encode(numbers):
    result = []
    for number in numbers:
        groups = [number & 0x7F]
        number >>= 7
        while number:
            groups.append(number & 0x7F)
            number >>= 7
        groups.reverse()
        for i, group in enumerate(groups):
            if i < len(groups) - 1:
                result.append(group | 0x80)
            else:
                result.append(group)
    return result


def decode(bytes_):
    if not bytes_:
        return []
    result = []
    value = 0
    terminated = True
    for byte in bytes_:
        value = (value << 7) | (byte & 0x7F)
        if byte & 0x80:
            terminated = False
        else:
            result.append(value)
            value = 0
            terminated = True
    if not terminated:
        raise ValueError("incomplete byte sequence")
    return result
