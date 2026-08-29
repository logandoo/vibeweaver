def translate(text):
    vowels = "aeiou"
    translated = []
    for word in text.split():
        if word[0] in vowels or word.startswith(("xr", "yt")):
            translated.append(word + "ay")
            continue
        index = 0
        for i, char in enumerate(word):
            if char in vowels or (i > 0 and char == "y"):
                index = i
                break
        if index > 0 and word[index] == "u" and word[index - 1] == "q":
            index += 1
        translated.append(word[index:] + word[:index] + "ay")
    return " ".join(translated)
