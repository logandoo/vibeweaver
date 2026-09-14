def transpose(text):
    if not text:
        return ""

    lines = text.split("\n")

    # Determine the maximum line length (width of the matrix)
    max_len = max(len(line) for line in lines)

    result_lines = []
    for col in range(max_len):
        row_chars = []
        for row in range(len(lines)):
            if col < len(lines[row]):
                row_chars.append(lines[row][col])
            else:
                # Pad with space only if a later row has a character at this col
                # Check if any subsequent row has content at this column
                if any(col < len(lines[r]) for r in range(row + 1, len(lines))):
                    row_chars.append(" ")
                # Otherwise, don't pad (truncate to the right)
        result_lines.append("".join(row_chars))

    return "\n".join(result_lines)
