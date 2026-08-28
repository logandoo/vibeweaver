> cap=5  stall=3×
1. `translate("apple")` returns `"appleay"` (rule 1: word starts with a vowel).
2. `translate("xray")` returns `"xrayay"` (rule 1: word starts with `"xr"`).
3. `translate("yttria")` returns `"yttriaay"` (rule 1: word starts with `"yt"`).
4. `translate("pig")` returns `"igpay"` (rule 2: single leading consonant).
5. `translate("chair")` returns `"airchay"` (rule 2: multiple leading consonants).
6. `translate("thrush")` returns `"ushthray"` (rule 2: consonant cluster).
7. `translate("quick")` returns `"ickquay"` (rule 3: leading `"qu"`, no preceding consonants).
8. `translate("square")` returns `"aresquay"` (rule 3: consonant(s) followed by `"qu"`).
9. `translate("my")` returns `"ymay"` (rule 4: single consonant followed by `"y"`).
10. `translate("rhythm")` returns `"ythmrhay"` (rule 4: consonant cluster followed by `"y"`).
11. `translate("quick fast run")` returns `"ickquay astfay unray"` (multi-word phrase translated per word).
12. `pig_latin.py` imports and runs with no syntax or runtime errors.
