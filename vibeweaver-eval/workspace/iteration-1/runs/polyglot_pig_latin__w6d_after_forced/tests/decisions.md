# Decisions (AUTO mode) — pig_latin

D-1 | trigger: algorithm choice for 4-rule translation | options: (a) regex-based rule matching, (b) single left-to-right consonant scan with qu/y special-cases | chosen: b | why: one pass, no regex dependency, reads directly from the rule text, handles overlapping qu/y precedence in one loop | revisit-if: rules gain non-prefix conditions (e.g. internal syllable rules)
