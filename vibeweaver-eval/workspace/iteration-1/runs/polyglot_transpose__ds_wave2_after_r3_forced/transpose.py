def transpose(text):
    rows = text.split("\n")
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    out = []
    for column in range(width):
        line = "".join(
            row[column] if column < len(row) else " " for row in rows
        )
        while line and line[-1] == " " and len(rows[len(line) - 1]) <= column:
            line = line[:-1]
        out.append(line)
    return "\n".join(out)
