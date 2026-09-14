def transpose(text):
    if not text:
        return ""

    lines = text.split("\n")
    max_len = max(len(line) for line in lines)

    result = []
    for col in range(max_len):
        row_chars = []
        for row_idx, line in enumerate(lines):
            if col < len(line):
                row_chars.append(line[col])
            else:
                # Check if any subsequent row has a character at this column
                has_future = any(len(lines[r]) > col for r in range(row_idx + 1, len(lines)))
                if has_future:
                    row_chars.append(" ")
        result.append("".join(row_chars))

    return "\n".join(result)
