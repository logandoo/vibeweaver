import re

VOWELS = "aeiou"


def _translate_word(word):
    if word[0] in VOWELS or word.startswith("xr") or word.startswith("yt"):
        return word + "ay"

    qu = re.match(r"^([^aeiou]*qu)(.*)$", word)
    if qu:
        return qu.group(2) + qu.group(1) + "ay"

    y = re.match(r"^([^aeiou]+)(y.*)$", word)
    if y:
        return y.group(2) + y.group(1) + "ay"

    consonant = re.match(r"^([^aeiou]+)(.*)$", word)
    return consonant.group(2) + consonant.group(1) + "ay"


def translate(text):
    return " ".join(_translate_word(word) for word in text.split())
