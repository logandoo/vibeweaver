VOWELS = "aeiou"


def translate(text):
    return " ".join(_translate_word(word) for word in text.split())


def _translate_word(word):
    if word[0] in VOWELS or word[:2] in ("xr", "yt"):
        return word + "ay"

    i = 0
    while i < len(word) and word[i] not in VOWELS:
        if word[i] == "y" and i > 0:
            break
        i += 1

    if i < len(word) and word[i] == "u" and i > 0 and word[i - 1] == "q":
        i += 1

    return word[i:] + word[:i] + "ay"
