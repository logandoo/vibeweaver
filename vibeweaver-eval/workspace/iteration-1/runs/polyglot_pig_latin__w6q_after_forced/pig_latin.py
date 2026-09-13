def translate(text):
    words = text.split()
    return ' '.join(translate_word(w) for w in words)


def translate_word(word):
    vowels = set('aeiou')

    # Rule 1: starts with vowel, or "xr", or "yt"
    if word[0] in vowels or word.startswith('xr') or word.startswith('yt'):
        return word + 'ay'

    # Find the split point where the consonant cluster ends
    i = 0
    while i < len(word):
        ch = word[i]
        if ch in vowels:
            # Rule 3: "qu" moves as a unit
            if ch == 'u' and i > 0 and word[i - 1] == 'q':
                i += 1
                break
            break
        # Rule 4: 'y' after consonants acts as a vowel
        if ch == 'y' and i > 0:
            break
        i += 1

    return word[i:] + word[:i] + 'ay'
