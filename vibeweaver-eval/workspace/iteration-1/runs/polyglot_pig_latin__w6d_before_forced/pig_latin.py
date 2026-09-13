VOWELS = frozenset("aeiou")


def _translate_word(word):
    if not word:
        return word

    if word[0] in VOWELS or word[:2] in ("xr", "yt"):
        return word + "ay"

    index = 0
    length = len(word)
    while index < length and word[index] not in VOWELS:
        if word[index] == "y" and index > 0:
            break
        if word[index] == "q" and index + 1 < length and word[index + 1] == "u":
            index += 2
            break
        index += 1

    return word[index:] + word[:index] + "ay"


def translate(text):
    return " ".join(_translate_word(word) for word in text.split())
