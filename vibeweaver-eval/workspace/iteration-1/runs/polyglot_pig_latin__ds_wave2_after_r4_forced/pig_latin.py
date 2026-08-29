def translate(text):
    def translate_word(word):
        if word[0] in "aeiou" or word.startswith("xr") or word.startswith("yt"):
            return word + "ay"
        for i, char in enumerate(word):
            if char in "aeiou" or (char == "y" and i > 0):
                if char == "u" and i > 0 and word[i - 1] == "q":
                    return word[i + 1:] + word[:i + 1] + "ay"
                return word[i:] + word[:i] + "ay"
        return word + "ay"

    return " ".join(translate_word(word) for word in text.split())
