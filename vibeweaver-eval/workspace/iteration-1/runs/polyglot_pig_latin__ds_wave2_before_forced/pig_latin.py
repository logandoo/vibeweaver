import re


def translate(text):
    return " ".join(_translate_word(word) for word in text.split())


def _translate_word(word):
    if re.match(r"^(?:[aeiou]|xr|yt)", word):
        return word + "ay"
    m = re.match(r"^([^aeiou]*qu)", word)
    if m:
        head = m.group(1)
        return word[len(head):] + head + "ay"
    m = re.match(r"^([^aeiou]+)([aeiouy].*)", word)
    if m:
        return m.group(2) + m.group(1) + "ay"
    return word + "ay"
