def transpose(text):
    rows = text.split("\n")
    max_len = max((len(row) for row in rows), default=0)
    out = []
    for i in range(max_len):
        col = [row[i] if i < len(row) else " " for row in rows]
        k = len(col) - 1
        while k >= 0 and col[k] == " " and i >= len(rows[k]):
            k -= 1
        out.append("".join(col[: k + 1]))
    return "\n".join(out)
