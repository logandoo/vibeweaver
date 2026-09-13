VOWELS = "aeiou"


def _translate_word(word):
    # Rule 1: begins with a vowel, or "xr"/"yt" -> just append "ay".
    if word[0] in VOWELS or word[:2] in ("xr", "yt"):
        return word + "ay"

    # Rules 2/3/4: scan the leading consonants, stopping at the first vowel,
    # at a "qu" cluster (consume both letters), or at a "y" preceded by at
    # least one consonant.
    i = 0
    while i < len(word) and word[i] not in VOWELS:
        if word[i] == "y" and i > 0:
            break
        if word[i : i + 2] == "qu":
            i += 2
            break
        i += 1

    return word[i:] + word[:i] + "ay"


def translate(text):
    return " ".join(_translate_word(word) for word in text.split())
