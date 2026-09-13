def transpose(text):
    lines = text.split("\n")
    max_len = max((len(line) for line in lines), default=0)

    rows = []
    for col in range(max_len):
        column = []
        for line in lines:
            if col < len(line):
                column.append(line[col])
            else:
                column.append(None)
        while column and column[-1] is None:
            column.pop()
        rows.append("".join(" " if char is None else char for char in column))

    return "\n".join(rows)
