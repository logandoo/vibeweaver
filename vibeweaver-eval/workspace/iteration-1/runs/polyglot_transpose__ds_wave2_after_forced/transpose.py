def transpose(text):
    if not text:
        return text

    lines = text.split("\n")
    max_len = max(len(line) for line in lines)
    result = []
    for i in range(max_len):
        row = []
        for j, line in enumerate(lines):
            if i < len(line):
                row.append(line[i])
            elif any(len(lines[k]) > i for k in range(j + 1, len(lines))):
                row.append(" ")
            else:
                break
        result.append("".join(row))
    return "\n".join(result)
