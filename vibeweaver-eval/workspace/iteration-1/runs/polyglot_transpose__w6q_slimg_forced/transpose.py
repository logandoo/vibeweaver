def transpose(text):
    if not text:
        return ""

    lines = text.split("\n")

    # Remove trailing empty lines
    while lines and lines[-1] == "":
        lines.pop()

    if not lines:
        return ""

    # Find the maximum line length
    max_len = max(len(line) for line in lines) if lines else 0

    result_lines = []
    for col in range(max_len):
        row_chars = []
        last_real = -1  # rightmost position that came from a real character
        for row_idx, line in enumerate(lines):
            if col < len(line):
                row_chars.append(line[col])
                last_real = len(row_chars) - 1
            else:
                row_chars.append(" ")

        if last_real < 0:
            # All padding — skip this column (shouldn't happen normally)
            continue

        # Truncate to the last real character
        s = "".join(row_chars[:last_real + 1])
        result_lines.append(s)

    return "\n".join(result_lines)
