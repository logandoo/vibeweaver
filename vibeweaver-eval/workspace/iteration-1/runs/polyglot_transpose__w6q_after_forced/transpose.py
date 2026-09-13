def transpose(text):
    lines = text.split('\n') if text else []
    if not lines:
        return ''

    max_len = max(len(line) for line in lines)

    # Pad each line to max_len with spaces on the right
    padded = [line.ljust(max_len) for line in lines]

    # Transpose: each column becomes a row
    result_lines = []
    for col in range(max_len):
        row_chars = []
        for row in range(len(padded)):
            row_chars.append(padded[row][col])
        result_lines.append(''.join(row_chars).rstrip())

    return '\n'.join(result_lines)
