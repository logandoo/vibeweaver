import re

VOWELS = "aeiou"


def translate(text):
    return " ".join(_translate_word(word) for word in text.split())


def _translate_word(word):
    if word[0] in VOWELS or word.startswith("xr") or word.startswith("yt"):
        return word + "ay"

    match = re.match(r"([^aeiou]*qu)(.*)", word)
    if match:
        prefix, rest = match.groups()
        return rest + prefix + "ay"

    match = re.match(r"([^aeiou]+)(y.*)", word)
    if match:
        prefix, rest = match.groups()
        return rest + prefix + "ay"

    match = re.match(r"([^aeiou]+)(.*)", word)
    if match:
        prefix, rest = match.groups()
        return rest + prefix + "ay"

    return word + "ay"
