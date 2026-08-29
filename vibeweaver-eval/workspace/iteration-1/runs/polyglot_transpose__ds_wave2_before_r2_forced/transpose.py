def transpose(text):
    lines = text.split("\n")
    max_len = max((len(line) for line in lines), default=0)
    result = []
    for i in range(max_len):
        column = [line[i] if i < len(line) else " " for line in lines]
        keep = len(lines)
        while keep and len(lines[keep - 1]) <= i:
            keep -= 1
        result.append("".join(column[:keep]))
    return "\n".join(result)
