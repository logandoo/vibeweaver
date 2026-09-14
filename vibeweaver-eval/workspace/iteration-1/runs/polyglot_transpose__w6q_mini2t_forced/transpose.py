def transpose(text):
    if not text:
        return ""
    lines = text.split('\n')
    max_len = max(len(line) for line in lines)
    result = []
    for col in range(max_len):
        row_chars = []
        last_content_idx = -1
        for i, line in enumerate(lines):
            if col < len(line):
                row_chars.append(line[col])
                last_content_idx = i
            else:
                row_chars.append(' ')
        # Strip trailing padding spaces (beyond last line with content)
        # But keep spaces that are actual input characters
        row_str = ''.join(row_chars)
        if last_content_idx < len(lines) - 1:
            # There are trailing padding spaces
            # Keep only up to the last line that has content at this column
            row_str = row_str[:last_content_idx + 1]
        result.append(row_str)
    return '\n'.join(result)
