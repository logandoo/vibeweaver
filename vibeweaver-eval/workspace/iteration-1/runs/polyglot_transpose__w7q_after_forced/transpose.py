def transpose(text):
    if not text:
        return ""
    lines = text.split("\n")
    max_len = max(len(line) for line in lines)
    result = []
    for col in range(max_len):
        row_chars = []
        for line in lines:
            if col < len(line):
                row_chars.append(line[col])
            else:
                row_chars.append(" ")
        result.append("".join(row_chars).rstrip())
    return "\n".join(result)
