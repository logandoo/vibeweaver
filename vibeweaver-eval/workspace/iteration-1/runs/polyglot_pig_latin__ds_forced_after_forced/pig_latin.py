def translate(text):
    return " ".join(_translate_word(word) for word in text.split())


def _translate_word(word):
    if word[0] in "aeiou" or word.startswith("xr") or word.startswith("yt"):
        return word + "ay"
    split = len(word)
    for i in range(1, len(word)):
        if word[i] in "aeiou" or word[i] == "y":
            if word[i] == "u" and word[i - 1] == "q":
                split = i + 1
            else:
                split = i
            break
    return word[split:] + word[:split] + "ay"
