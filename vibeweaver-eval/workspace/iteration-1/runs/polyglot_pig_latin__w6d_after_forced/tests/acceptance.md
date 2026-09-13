> cap=5  stall=3×

# Acceptance Criteria — pig_latin.translate

1. Rule 1: a word beginning with a vowel, or with `xr`/`yt`, gets `ay` appended unchanged (`apple`→`appleay`, `xray`→`xrayay`, `yttria`→`yttriaay`).
2. Rule 2: a word beginning with one or more consonants moves those leading consonants to the end then appends `ay` (`pig`→`igpay`, `chair`→`airchay`, `thrush`→`ushthray`).
3. Rule 3: a word beginning with zero or more consonants followed by `qu` moves that prefix (consonants + `qu`) to the end then appends `ay` (`quick`→`ickquay`, `square`→`aresquay`).
4. Rule 4: a word beginning with one or more consonants followed by `y` moves only the consonants before the `y` to the end then appends `ay` (`my`→`ymay`, `rhythm`→`ythmrhay`).
5. `translate` handles multi-word input by translating each whitespace-separated word and joining with single spaces.
6. The module imports and runs without syntax or runtime errors.
