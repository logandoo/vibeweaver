import re


def translate(text):
    words = text.split()
    return ' '.join(_translate_word(w) for w in words)


def _translate_word(word):
    # Rule 1: starts with vowel sound (vowel letter, "xr", or "yt")
    if re.match(r'^([aeiou]|xr|yt)', word):
        return word + 'ay'

    # Find the split point where the consonant cluster ends
    # Rule 3: consonants followed by "qu" -> move consonants+qu to end
    # Rule 4: consonants followed by "y" -> y acts as vowel, move preceding consonants
    # Rule 2: plain consonant cluster followed by vowel

    m = re.match(r'^([^aeiou]*qu)(.*)', word)
    if m:
        return m.group(2) + m.group(1) + 'ay'

    m = re.match(r'^([^aeiouy]+)(y.*)', word)
    if m:
        return m.group(2) + m.group(1) + 'ay'

    m = re.match(r'^([^aeiou]+)(.*)', word)
    if m and m.group(2):
        return m.group(2) + m.group(1) + 'ay'

    return word + 'ay'
