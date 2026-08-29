def transpose(text):
    lines = text.split('\n')
    width = max((len(line) for line in lines), default=0)
    result = []
    for col in range(width):
        column = ''.join(line[col] if col < len(line) else ' ' for line in lines)
        last = next(i for i in range(len(lines) - 1, -1, -1) if len(lines[i]) > col)
        result.append(column[:last + 1])
    return '\n'.join(result)
