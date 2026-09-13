import re


def translate(text):
    """Translate English text to Pig Latin."""
    return ' '.join(_translate_word(word) for word in text.split())


def _translate_word(word):
    # Rule 1: starts with vowel sound (vowel, "xr", or "yt")
    if re.match(r'^([aeiou]|xr|yt)', word):
        return word + 'ay'

    # Find the split point where the consonant cluster ends
    # We need to find the first "vowel-like" character
    # Vowels are a, e, i, o, u
    # 'y' acts as a vowel only when not at position 0
    # 'qu' is treated as a unit — the 'u' after 'q' is not a vowel split point

    for i, ch in enumerate(word):
        if ch in 'aeiou':
            # Rule 3: if we hit 'u' and the previous char is 'q', include 'qu'
            if ch == 'u' and i > 0 and word[i - 1] == 'q':
                continue
            split = i
            break
        elif ch == 'y' and i > 0:
            # Rule 4: 'y' after consonants acts as a vowel
            split = i
            break
    else:
        # No vowel-like character found; treat entire word as consonant cluster
        return word + 'ay'

    return word[split:] + word[:split] + 'ay'
