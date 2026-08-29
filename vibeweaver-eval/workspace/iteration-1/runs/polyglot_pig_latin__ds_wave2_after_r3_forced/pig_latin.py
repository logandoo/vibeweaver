VOWELS = "aeiou"


def translate(text):
    return " ".join(_translate_word(word) for word in text.split())


def _translate_word(word):
    if not word:
        return word
    if word[0] in VOWELS or word.startswith("xr") or word.startswith("yt"):
        return word + "ay"
    for i, ch in enumerate(word):
        if ch in VOWELS or (i > 0 and ch == "y"):
            if ch == "u" and i > 0 and word[i - 1] == "q":
                i += 1
            return word[i:] + word[:i] + "ay"
    return word + "ay"
