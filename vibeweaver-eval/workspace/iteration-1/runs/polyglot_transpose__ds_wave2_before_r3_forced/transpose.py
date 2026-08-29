def transpose(text):
    lines = text.split("\n")
    max_len = max((len(line) for line in lines), default=0)
    result = []
    for col in range(max_len):
        cells = []
        for line in lines:
            if col < len(line):
                cells.append(line[col])
            else:
                cells.append(None)
        while cells and cells[-1] is None:
            cells.pop()
        result.append("".join(" " if cell is None else cell for cell in cells))
    return "\n".join(result)
