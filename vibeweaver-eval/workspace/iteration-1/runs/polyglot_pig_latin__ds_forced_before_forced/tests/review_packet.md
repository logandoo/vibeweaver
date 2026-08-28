# A4.9 Review Packet — pig_latin.py

## Scope
Change type: behavior-semantic change (single-file: `pig_latin.py`, starter stub → full implementation). No git baseline exists (eval workspace, untracked).

## Spec (prompt.md rules)
1. Words starting with a vowel sound → append "ay" (a, e, i, o, u) or "xr"/"yt"
2. Words starting with one or more consonants → move the consonant cluster to the end, add "ay"
3. Words starting with zero+ consonants then "qu" → move the cluster+qu to the end, add "ay"
4. Words starting with consonants then "y" → move the consonants to the end, add "ay"

## Implementation under review
```python
VOWELS = "aeiou"


def _translate_word(word):
    if word[0] in VOWELS or word.startswith(("xr", "yt")):
        return word + "ay"
    for i, ch in enumerate(word):
        if ch in VOWELS or (ch == "y" and i > 0):
            if ch == "u" and i > 0 and word[i - 1] == "q":
                continue
            return word[i:] + word[:i] + "ay"
    return word + "ay"


def translate(text):
    return " ".join(_translate_word(word) for word in text.split())
```

## Verification evidence
- RED (starter stub): tests/red_baseline.log — 0/23 passed, exit 1
- GREEN (implementation): tests/verification_output.log — 23/23 canonical cases + 4/4 edge cases (empty string, collapsed whitespace, vowel-less word, "spray"), py_compile OK
- Hidden grading contract (read-only, must not be created/copied): tasks/polyglot_pig_latin/hidden_tests/pig_latin_test.py imports `from pig_latin import translate`
