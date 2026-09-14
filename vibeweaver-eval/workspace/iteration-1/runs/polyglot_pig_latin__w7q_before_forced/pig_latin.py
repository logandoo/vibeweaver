import re


def translate(text):
    """Translate English text to Pig Latin."""
    words = text.split()
    return ' '.join(_translate_word(w) for w in words)


def _translate_word(word):
    """Translate a single word to Pig Latin using the four rules."""
    # Rule 1: starts with vowel sound
    if re.match(r'^(a|e|i|o|u)\w*', word, re.IGNORECASE):
        return word + 'ay'
    if re.match(r'^(xr|yt)\w*', word, re.IGNORECASE):
        return word + 'ay'

    # Find the split point where the consonant cluster ends
    # Rule 3: consonants followed by "qu" -> move consonants + "qu" to end
    m = re.match(r'^([^aeiou]*qu)(.*)', word)
    if m:
        return m.group(2) + m.group(1) + 'ay'

    # Rule 4: consonants followed by "y" -> y acts as vowel
    m = re.match(r'^([^aeiouy]+)y(.*)', word)
    if m:
        return 'y' + m.group(2) + m.group(1) + 'ay'

    # Rule 2: one or more consonants at start
    m = re.match(r'^([^aeiou]+)(.*)', word)
    if m:
        return m.group(2) + m.group(1) + 'ay'

    return word + 'ay'
