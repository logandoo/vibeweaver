> cap=5  stall=3×

# Acceptance criteria — Pig Latin `translate(text)`

1. Vowel-initial words append `ay`: apple→appleay, ear→earay, igloo→iglooay, object→objectay, under→underay.
2. Words beginning with `xr`/`yt` append `ay`: xray→xrayay, yttria→yttriaay.
3. Leading consonant cluster moves to the end, then `ay`: pig→igpay, koala→oalakay, xenon→enonxay, qat→atqay, liquid→iquidlay, chair→airchay, therapy→erapythay, thrush→ushthray, school→oolschay.
4. `qu` (with zero or more preceding consonants) moves as a unit then `ay`: equal→equalay, queen→eenquay, square→aresquay.
5. Leading consonants followed by `y` move before `y`, then `ay`: rhythm→ythmrhay, my→ymay; a leading `y` acts as a consonant: yellow→ellowyay.
6. Multi-word phrases translate word-by-word: "quick fast run"→"ickquay astfay unray".
7. `pig_latin.py` imports with no syntax/runtime error and `translate` returns a `str`.
