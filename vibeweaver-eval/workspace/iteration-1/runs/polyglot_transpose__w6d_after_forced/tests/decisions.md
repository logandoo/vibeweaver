# Decisions (AUTO mode)

D-1 | trigger: padding semantics of ragged input are described as "pad to the left" but worked examples imply otherwise | options: (a) left-pad (rjust) + transpose; (b) right-pad (ljust) + transpose, dropping only trailing padding rows | chosen: (b) | why: (b) reproduces every canonical Exercism case (verified: 14/14) including `"h   "` / `"ei "` where real trailing spaces are preserved, and both prompt.md examples; (a) contradicts the canonical expected output | revisit-if: a hidden test asserts left-padding behavior that canonical data does not cover
