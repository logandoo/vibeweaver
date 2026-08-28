def transpose(text):
    if not text:
        return ""
    rows = text.split("\n")
    max_len = max(len(row) for row in rows)
    result = []
    for i in range(max_len):
        last = len(rows) - 1
        while last >= 0 and i >= len(rows[last]):
            last -= 1
        line = []
        for j in range(last + 1):
            if i < len(rows[j]):
                line.append(rows[j][i])
            else:
                line.append(" ")
        result.append("".join(line))
    return "\n".join(result)
