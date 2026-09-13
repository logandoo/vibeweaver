import re

VOWELS = "aeiou"


def _translate_word(word):
    if word[0] in VOWELS or word.startswith(("xr", "yt")):
        return word + "ay"

    match = re.match(r"^([^aeiou]*qu)(.*)$", word)
    if match:
        return match.group(2) + match.group(1) + "ay"

    match = re.match(r"^([^aeiou]+)y(.*)$", word)
    if match:
        return "y" + match.group(2) + match.group(1) + "ay"

    match = re.match(r"^([^aeiou]+)(.*)$", word)
    if match:
        return match.group(2) + match.group(1) + "ay"

    return word + "ay"


def translate(text):
    return " ".join(_translate_word(word) for word in text.split())
