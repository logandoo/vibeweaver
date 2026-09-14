def transpose(text):
    lines = text.split("\n")
    max_length = max(len(line) for line in lines)

    rows = []
    for column in range(max_length):
        # Last input line that actually has a character in this column.
        # Lines shorter than this are left-padded with spaces; lines below
        # it are dropped so output rows are never padded on the right.
        last_row = max(
            index for index, line in enumerate(lines) if len(line) > column
        )
        rows.append(
            "".join(
                lines[index][column] if column < len(lines[index]) else " "
                for index in range(last_row + 1)
            )
        )

    return "\n".join(rows)
