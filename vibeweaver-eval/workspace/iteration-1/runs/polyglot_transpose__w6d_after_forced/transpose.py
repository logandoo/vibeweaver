def transpose(text):
    lines = text.split("\n")
    width = max((len(line) for line in lines), default=0)
    transposed = []
    for column in range(width):
        last_row = max(i for i, line in enumerate(lines) if len(line) > column)
        transposed.append(
            "".join(
                line[column] if column < len(line) else " "
                for line in lines[: last_row + 1]
            )
        )
    return "\n".join(transposed)
