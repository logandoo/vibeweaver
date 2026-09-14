def transpose(text):
    """Transpose the given text so that rows become columns.

    Rows of different lengths are aligned by treating the missing cells on
    the right of a short row as blanks.  Those blanks are dropped from the
    end of the transposed rows, while spaces that actually occur in the
    input (including blanks that are only trailing padding for one row but
    fall inside a longer row) are preserved.
    """
    if text == "":
        return ""

    rows = text.split("\n")
    width = max(len(row) for row in rows)
    padded = [row.ljust(width, "\x00") for row in rows]

    transposed = []
    for column in range(width):
        line = "".join(row[column] for row in padded)
        transposed.append(line.rstrip("\x00").replace("\x00", " "))

    return "\n".join(transposed)
