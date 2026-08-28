def transpose(text):
    if not text:
        return ""

    lines = text.splitlines()
    width = max(len(line) for line in lines)

    sentinel = "\x00"
    while sentinel in text:
        sentinel = chr(ord(sentinel) + 1)

    padded = [line + sentinel * (width - len(line)) for line in lines]
    columns = ["".join(row[col] for row in padded) for col in range(width)]

    return "\n".join(
        col.rstrip(sentinel).replace(sentinel, " ") for col in columns
    )
