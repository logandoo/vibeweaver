def transpose(text):
    if text == "":
        return [""]
    rows = text.split("\n")
    max_len = max((len(r) for r in rows), default=0)
    if max_len == 0:
        return [""] * len(rows)
    result = []
    for col in range(max_len):
        line = ""
        for row in rows:
            if col < len(row):
                line += row[col]
            else:
                line += " "
        result.append(line.rstrip())
    return result
