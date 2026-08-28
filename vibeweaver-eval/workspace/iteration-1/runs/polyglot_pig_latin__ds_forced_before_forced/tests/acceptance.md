> cap=5  stall=3×

# Acceptance Criteria — Pig Latin `translate(text)`

1. Rule 1 vowel-start: "apple"→"appleay", "ear"→"earay", "igloo"→"iglooay", "object"→"objectay", "under"→"underay"
2. Rule 1 "xr"/"yt" prefixes: "xray"→"xrayay", "yttria"→"yttriaay"
3. Rule 2 single leading consonant: "pig"→"igpay", "koala"→"oalakay", "xenon"→"enonxay"
4. Rule 2 multi-consonant cluster: "chair"→"airchay", "therapy"→"erapythay", "thrush"→"ushthray", "school"→"oolschay"
5. Rule 3 "qu" cluster (with/without preceding consonant): "queen"→"eenquay", "square"→"aresquay"; "qat"→"atqay" (q without u)
6. Rule 4 consonant-cluster followed by "y": "my"→"ymay", "rhythm"→"ythmrhay"; "y" as consonant at word start: "yellow"→"ellowyay"
7. Vowel-start words containing "qu": "equal"→"equalay", "liquid"→"iquidlay"
8. Multi-word phrase: "quick fast run"→"ickquay astfay unray"
9. Module imports cleanly and `translate` raises no runtime error on any of the above inputs
