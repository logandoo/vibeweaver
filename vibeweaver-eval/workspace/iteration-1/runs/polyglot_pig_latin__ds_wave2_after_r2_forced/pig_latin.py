def translate(text):
    """Translate English text to Pig Latin per the four standard rules."""
    return " ".join(_translate_word(word) for word in text.split())


def _translate_word(word):
    vowels = "aeiou"
    if word[0] in vowels or word.startswith(("xr", "yt")):
        return word + "ay"
    for j in range(1, len(word)):
        if word[j] in vowels or word[j] == "y":
            split = j
            break
    else:
        split = len(word)
    if split < len(word) and word[split] == "u" and word[split - 1] == "q":
        split += 1
    return word[split:] + word[:split] + "ay"
