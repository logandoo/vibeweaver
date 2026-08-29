def translate(text):
    return " ".join(_translate_word(word) for word in text.split())


def _translate_word(word):
    if word[0] in "aeiou" or word.startswith("xr") or word.startswith("yt"):
        return word + "ay"
    i = 0
    while i < len(word):
        ch = word[i]
        if ch in "aeiou" or (ch == "y" and i > 0):
            break
        i += 1
    prefix = word[:i]
    rest = word[i:]
    if prefix.endswith("q"):
        return rest[1:] + prefix + "u" + "ay"
    return rest + prefix + "ay"
