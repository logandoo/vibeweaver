# A4.9 Independent Review Package — polyglot_pig_latin

**Trigger:** change implements the task's core feature (rule A4.9 applies);
no risk-tier paths touched (group 16 non-skippable check not triggered), change
is small/reversible, but an independent pass was run for rigor.

**Change under review:** `pig_latin.py` — replace `translate(text)` stub with a
working Pig Latin translator. Commit `1645302` (wave `8020354..1645302`).

```diff
diff --git a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_pig_latin__ds_wave2_after_r3_forced/pig_latin.py b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_pig_latin__ds_wave2_after_r3_forced/pig_latin.py
index dda3f07..ff32bec 100644
--- a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_pig_latin__ds_wave2_after_r3_forced/pig_latin.py
+++ b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_pig_latin__ds_wave2_after_r3_forced/pig_latin.py
@@ -1,2 +1,18 @@
+VOWELS = "aeiou"
+
+
 def translate(text):
-    pass
+    return " ".join(_translate_word(word) for word in text.split())
+
+
+def _translate_word(word):
+    if not word:
+        return word
+    if word[0] in VOWELS or word.startswith("xr") or word.startswith("yt"):
+        return word + "ay"
+    for i, ch in enumerate(word):
+        if ch in VOWELS or (i > 0 and ch == "y"):
+            if ch == "u" and i > 0 and word[i - 1] == "q":
+                i += 1
+            return word[i:] + word[:i] + "ay"
+    return word + "ay"
```

**Spec (from prompt.md, 4 rules):**
1. Starts with vowel, `xr`, or `yt` → append `ay`.
2. Starts with one+ consonants → move cluster to end + `ay`.
3. Starts with 0+ consonants + `qu` → move consonants+`qu` + `ay`.
4. Starts with one+ consonants + `y` → move consonants + `ay` (y = vowel after index 0).

**Reviewer verdict:** **APPROVE** — all 22 canonical vectors pass, no spec
violations found in-scope (independent reviewer executed the code in /tmp;
repo untouched). Edge cases examined: `qu` inside word absorbed into leading
cluster (correct); all-consonant words fall through to `word+"ay"` (consistent
with rule 2); `y`-first words consonant (correct); empty string safe.
Out-of-scope (spec never exercises): punctuation/case normalization.
No real bugs found. Evidence: canonical hidden suite 22/22
(tests/grading_run.log, tests/fresh_run.log) + reviewer's own 22/22 execution.
