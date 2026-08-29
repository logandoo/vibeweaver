def transpose(text):
    lines = text.split("\n")
    max_len = max((len(line) for line in lines), default=0)
    transposed = []
    for col in range(max_len):
        column = "".join(line[col] if col < len(line) else " " for line in lines)
        last_real = len(lines) - 1
        while last_real >= 0 and len(lines[last_real]) <= col:
            last_real -= 1
        transposed.append(column[: last_real + 1])
    return "\n".join(transposed)
