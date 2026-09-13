def transpose(text):
    if not text:
        return ''
    lines = text.split('\n')
    max_len = max(len(line) for line in lines)

    result = []
    for col in range(max_len):
        row_chars = []
        for row in lines:
            if col < len(row):
                row_chars.append(row[col])
            else:
                row_chars.append(' ')
        result.append(''.join(row_chars).rstrip())

    return '\n'.join(result)
