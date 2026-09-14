def transpose(text):
    if not text:
        return ""

    lines = text.split('\n')

    # Find the maximum line length
    max_len = max(len(line) for line in lines)

    result_lines = []
    for col in range(max_len):
        # Find the last row that has content at this column
        last_row_with_content = -1
        for row_idx in range(len(lines) - 1, -1, -1):
            if col < len(lines[row_idx]):
                last_row_with_content = row_idx
                break

        if last_row_with_content == -1:
            # No row has content at this column - shouldn't happen since we use max_len
            continue

        row_chars = []
        for row_idx in range(last_row_with_content + 1):
            if col < len(lines[row_idx]):
                row_chars.append(lines[row_idx][col])
            else:
                row_chars.append(' ')
        result_lines.append(''.join(row_chars))

    return '\n'.join(result_lines)
