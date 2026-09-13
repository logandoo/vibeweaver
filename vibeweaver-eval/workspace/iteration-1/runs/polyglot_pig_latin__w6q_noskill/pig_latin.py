def translate(text):
    words = text.split()
    return ' '.join(translate_word(word) for word in words)


def translate_word(word):
    vowels = set('aeiou')

    # Rule 1: starts with vowel, "xr", or "yt"
    if word[0] in vowels or word.startswith('xr') or word.startswith('yt'):
        return word + 'ay'

    # Find the split point for consonant clusters
    i = 0
    while i < len(word):
        char = word[i]
        # Rule 4: 'y' after at least one consonant acts as a vowel
        if char == 'y' and i > 0:
            return word[i:] + word[:i] + 'ay'
        # Rule 3: 'qu' treated as a consonant cluster
        if char == 'q' and i + 1 < len(word) and word[i + 1] == 'u':
            i += 2
            continue
        # Rule 2: regular vowel splits the consonant cluster
        if char in vowels:
            return word[i:] + word[:i] + 'ay'
        i += 1

    return word + 'ay'
