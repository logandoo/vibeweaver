import re


def translate(text):
    """Translate English text to Pig Latin."""
    words = text.split()
    return ' '.join(_translate_word(w) for w in words)


def _translate_word(word):
    """Apply Pig Latin rules to a single word."""
    # Rule 1: starts with vowel sound (vowel letter, "xr", or "yt")
    if re.match(r'^(a|e|i|o|u|xr|yt)', word, re.IGNORECASE):
        return word + 'ay'

    # Find the split point where the initial consonant cluster ends
    # Rule 3: consonants followed by "qu" -> move consonants+qu to end
    # Rule 4: consonants followed by "y" -> y acts as vowel (move preceding consonants)
    # Rule 2: general consonant cluster -> move to end

    # Find first vowel-like character (a, e, i, o, u, or y not at position 0)
    for i, ch in enumerate(word):
        if ch.lower() in ('a', 'e', 'i', 'o', 'u'):
            # If this is 'u' after 'q', treat "qu" as a unit (Rule 3)
            if ch == 'u' and i > 0 and word[i - 1].lower() == 'q':
                split = i + 1
            else:
                split = i
            return word[split:] + word[:split] + 'ay'
        if ch == 'y' and i > 0:
            # 'y' after consonants acts as a vowel (Rule 4)
            return word[i:] + word[:i] + 'ay'

    # No vowel found (edge case, shouldn't happen with real words)
    return word + 'ay'
