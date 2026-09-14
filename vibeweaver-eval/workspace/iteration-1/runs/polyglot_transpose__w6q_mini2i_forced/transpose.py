def transpose(text):
    if not text:
        return ""
    
    lines = text.split("\n")
    # Remove trailing empty row (from trailing newline)
    if lines and lines[-1] == "":
        lines = lines[:-1]
    
    if not lines:
        return ""
    
    # Find the max column index needed
    max_cols = max(len(line) for line in lines)
    
    result_rows = []
    for col in range(max_cols):
        chars = []
        for row_idx, line in enumerate(lines):
            if col < len(line):
                chars.append(line[col])
            else:
                # Pad with space if this row is shorter than the current column
                # but only if there's a longer row later
                # Check if any subsequent row has a character at this column
                has_later = any(col < len(lines[r]) for r in range(row_idx + 1, len(lines)))
                if has_later:
                    chars.append(" ")
        result_rows.append("".join(chars))
    
    return "\n".join(result_rows)
