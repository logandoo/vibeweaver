def transpose(text):
    if not text:
        return ""

    lines = text.split('\n')

    # Find the maximum line length
    max_len = max(len(line) for line in lines)

    # Build the transposed result
    result_lines = []
    for col in range(max_len):
        chars = []
        for row in lines:
            if col < len(row):
                chars.append(row[col])
            else:
                chars.append(' ')
        result_lines.append(''.join(chars))

    return '\n'.join(result_lines)
