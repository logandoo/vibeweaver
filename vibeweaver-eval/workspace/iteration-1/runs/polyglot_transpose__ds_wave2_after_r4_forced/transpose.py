def transpose(text):
    rows = text.splitlines()
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    transposed = []
    for col in range(width):
        cells = []
        for row in rows:
            cells.append(row[col] if col < len(row) else "")
        while cells and cells[-1] == "":
            cells.pop()
        transposed.append("".join(cell or " " for cell in cells))
    return "\n".join(transposed)
