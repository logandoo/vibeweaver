VOWELS = "aeiou"


def _translate_word(word):
    if word[0] in VOWELS or word.startswith(("xr", "yt")):
        return word + "ay"
    for i, ch in enumerate(word):
        if ch in VOWELS or (ch == "y" and i > 0):
            if ch == "u" and i > 0 and word[i - 1] == "q":
                continue
            return word[i:] + word[:i] + "ay"
    return word + "ay"


def translate(text):
    return " ".join(_translate_word(word) for word in text.split())
