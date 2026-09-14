def transpose(text):
    rows = text.split("\n")
    height = max(len(row) for row in rows)
    result = []
    for col in range(height):
        last = max(i for i, row in enumerate(rows) if len(row) > col)
        result.append(
            "".join(
                rows[i][col] if col < len(rows[i]) else " "
                for i in range(last + 1)
            )
        )
    return "\n".join(result)
