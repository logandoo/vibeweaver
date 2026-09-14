def transpose(text):
    if not text:
        return ""

    lines = text.split("\n")

    # Find the maximum line length
    max_len = max(len(line) for line in lines)

    result_lines = []
    for col in range(max_len):
        row_chars = []
        for row_idx, line in enumerate(lines):
            if col < len(line):
                row_chars.append(line[col])
            else:
                # Check if any subsequent row has a character at this column
                needs_pad = False
                for later_row in lines[row_idx + 1:]:
                    if col < len(later_row):
                        needs_pad = True
                        break
                if needs_pad:
                    row_chars.append(" ")
        result_lines.append("".join(row_chars))

    return "\n".join(result_lines)
