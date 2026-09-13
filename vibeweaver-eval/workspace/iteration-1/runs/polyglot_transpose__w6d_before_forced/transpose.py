def transpose(text):
    lines = text.split("\n")
    width = max(len(line) for line in lines)

    rows = []
    for col in range(width):
        last = max(i for i, line in enumerate(lines) if col < len(line))
        rows.append(
            "".join(
                line[col] if col < len(line) else " "
                for line in lines[: last + 1]
            )
        )

    return "\n".join(rows)
