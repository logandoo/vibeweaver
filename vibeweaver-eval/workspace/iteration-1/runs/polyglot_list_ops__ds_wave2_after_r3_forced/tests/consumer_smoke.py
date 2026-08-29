"""C7 downstream consumer smoke: import list_ops as an external consumer would
and run one realistic mini-pipeline across the whole API."""

import sys

sys.path.insert(0, ".")

import list_ops

rows = ["alpha", "beta", "gamma", "delta"]
upper = list_ops.map(lambda s: s.upper(), rows)
kept = list_ops.filter(lambda s: s.startswith("A") or s.startswith("D"), upper)
n = list_ops.length(kept)
total = list_ops.foldl(lambda acc, s: acc + s, kept, "")
rev = list_ops.reverse(kept)
flat = list_ops.concat([rev, ["E"]])
r = list_ops.foldr(lambda acc, s: acc + "|" + s, flat, "")

assert upper == ["ALPHA", "BETA", "GAMMA", "DELTA"], upper
assert kept == ["ALPHA", "DELTA"], kept
assert n == 2, n
assert total == "ALPHADELTA", total
assert rev == ["DELTA", "ALPHA"], rev
assert flat == ["DELTA", "ALPHA", "E"], flat
assert r == "|E|ALPHA|DELTA", r

print("CONSUMER-SMOKE: PASS — pipeline (map→filter→length→foldl→reverse→concat→foldr) OK")
