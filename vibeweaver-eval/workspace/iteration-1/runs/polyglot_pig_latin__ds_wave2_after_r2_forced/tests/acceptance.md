> cap=5  stall=3×

# Acceptance Criteria — pig_latin.translate (source: prompt.md, Exercism Pig Latin)

1. Word beginning with a vowel is returned with "ay" appended (apple -> appleay)
2. Word beginning with "xr" or "yt" is returned with "ay" appended (xray -> xrayay, yttria -> yttriaay)
3. Word with one or more leading consonants has them moved to the end, then "ay" appended (pig -> igpay, chair -> airchay, thrush -> ushthray)
4. Word with zero or more consonants followed by "qu" has the consonants and "qu" moved to the end, then "ay" appended (quick -> ickquay, square -> aresquay)
5. Word with one or more consonants followed by "y" has the leading consonants moved to the end, then "ay" appended (my -> ymay, rhythm -> ythmrhay)
6. Multi-word text is translated word-by-word, results joined by a single space
