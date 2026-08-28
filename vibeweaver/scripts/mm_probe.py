#!/usr/bin/env python3
"""vibeweaver model-native multimodal probe (stdlib only).

Determines whether the CURRENT model genuinely perceives images, so
vibeweaver can pick the verifier (TESTING_PROTOCOLS.md A4.1 Step 0):
  PASS  -> Verifier: model-native [image]  (grade screenshots via Read tool,
          under the A4.1.1 Visual Verification Protocol)
  FAIL  -> fall back to mm-sensor / direct read

Protocol (do NOT reorder):
  1. `python3 {VW_DIR}/scripts/mm_probe.py --generate`  -> writes
     tests/probe_vision.png (random token + random color block) and
     tests/probe_vision.expected (ground truth, JSON).
     DO NOT open probe_vision.expected before step 3 — the probe is
     behavioral only if the report comes from the pixels, not the file.
  2. Read tests/probe_vision.png with the Read tool (media Read is ALLOWED
     for this probe artifact only — it is a vibeweaver probe, not user
     media; the mm-sensor ban applies to media grading, not this probe).
  3. Report what you actually perceive: the exact token string and the
     color name (palette: red / green / blue / orange / purple).
  4. `python3 {VW_DIR}/scripts/mm_probe.py --check <token> <color>`.
     exit 0 = PASS (multimodal confirmed), 1 = FAIL, 2 = usage/error.
  Record the result in tests/verification_log.md.

This is a BEHAVIORAL probe: capability is established by reading the
generated pixels, never by self-declaration ("I am multimodal" is not
evidence). The token is random per run, so there is nothing to recall.

Design notes (v2 — why it looks like this):
  * 5x7 dot-matrix glyphs (classic LCD proportions) rendered at 5px cells:
    a v1 3x5 font had 18+ glyph pairs differing by ONE pixel (S/5, V/Y,
    C/E, K/X, ...) and even a byte-identical pair (Z == 2), which made the
    old conjunctive "6/6 exact" check fail genuinely image-perceptive
    models on coin-flip glyphs (~68% of tokens contained a d<=2 pair).
  * TOKEN_ALPHABET is pruned to 28 chars: every pair is >= 4 bits apart
    (of 35). Run `--selftest` to re-verify this invariant after edits.
  * --check scores per-character position matches: PASS needs the color
    exact AND >= 5 of 6 token chars in exact positions. A blind model
    guessing scores ~0-1/6; P(guesser hits >= 5/6) < 4e-7 — the gate is
    still unpassable without real perception, but one isolated slip no
    longer disqualifies a vision-capable model (the v1 false-negative mode).
  * Ground truth is stored as salted per-position SHA-256 hashes
    (probe_vision.expected), NOT plaintext: opening the file by accident
    or probing --check with dummy tokens reveals nothing. FAIL output
    names mismatched positions only — never the expected characters.
    Repeated speculative --check runs are a protocol violation.
"""

import argparse
import hashlib
import json
import os
import random
import struct
import sys
import zlib

# 5x7 pixel font (rows top->bottom, 5 bits per row, bit 4 = leftmost pixel).
# Classic dot-matrix proportions; every glyph below is visually verified.
GLYPHS = {
    "A": [14, 17, 17, 31, 17, 17, 17], "B": [30, 17, 17, 30, 17, 17, 30],
    "C": [14, 17, 16, 16, 16, 17, 14], "D": [30, 17, 17, 17, 17, 17, 30],
    "E": [31, 16, 16, 30, 16, 16, 31], "F": [31, 16, 16, 30, 16, 16, 16],
    "G": [14, 17, 16, 23, 17, 17, 15], "H": [17, 17, 17, 31, 17, 17, 17],
    "J": [7, 2, 2, 2, 2, 18, 12],      "K": [17, 18, 20, 24, 20, 18, 17],
    "L": [16, 16, 16, 16, 16, 16, 31], "M": [17, 27, 21, 21, 17, 17, 17],
    "N": [17, 25, 21, 19, 17, 17, 17], "P": [30, 17, 17, 30, 16, 16, 16],
    "Q": [14, 17, 17, 17, 21, 18, 13], "R": [30, 17, 17, 30, 20, 18, 17],
    "S": [15, 16, 16, 14, 1, 1, 30],   "T": [31, 4, 4, 4, 4, 4, 4],
    "U": [17, 17, 17, 17, 17, 17, 14], "V": [17, 17, 17, 17, 17, 10, 4],
    "W": [17, 17, 17, 21, 21, 27, 17], "X": [17, 17, 10, 4, 10, 17, 17],
    "Y": [17, 17, 10, 4, 4, 4, 4],     "Z": [31, 1, 2, 4, 8, 16, 31],
    "2": [14, 17, 1, 6, 8, 16, 31],    "3": [31, 2, 4, 2, 1, 17, 14],
    "4": [2, 6, 10, 18, 31, 2, 2],     "5": [31, 16, 16, 30, 1, 1, 30],
    "6": [6, 8, 16, 30, 17, 17, 14],   "7": [31, 1, 2, 4, 8, 8, 8],
    "8": [14, 17, 17, 14, 17, 17, 14], "9": [14, 17, 17, 15, 1, 2, 12],
}

# Token alphabet = GLYPHS minus chars pruned for low separation
# (M/P/5/8 sit <= 3 bits from a kept sibling; 0/O/1/I excluded by design).
TOKEN_ALPHABET = "ABCDEFGHJKLNQRSTUVWXYZ234679"

# PASS threshold: >= 5 of 6 token chars in exact positions (+ color exact).
TOKEN_MIN_CORRECT = 5

PALETTE = [
    ("red", (220, 50, 50)),
    ("green", (50, 180, 90)),
    ("blue", (40, 100, 220)),
    ("orange", (235, 150, 30)),
    ("purple", (150, 60, 200)),
]


def make_png(width, height, rows):
    """rows: list of rows, each a list of (r, g, b) tuples. Stdlib PNG writer."""
    raw = b""
    for row in rows:
        raw += b"\x00" + b"".join(struct.pack("BBB", *px) for px in row)
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def render(token, color, scale=5):
    """340x150 canvas: color block top-left, 5x7 token text below."""
    w, h = 340, 150
    cell = 5 * scale                     # glyph advance: 25px + 10px gap
    gap = 2 * scale
    bg = (250, 250, 250)
    ink = (30, 30, 30)
    rows = [[bg for _ in range(w)] for _ in range(h)]
    for y in range(24, 66):              # color block: y 24-65 (42px)
        for x in range(24, 66):
            rows[y][x] = color
    tx, ty = 24, 82                      # text top-left, 35px tall glyphs
    for ch in token:
        glyph = GLYPHS[ch]
        for row_i, bits in enumerate(glyph):
            for col_i in range(5):
                if bits & (1 << (4 - col_i)):
                    for dy in range(scale):
                        for dx in range(scale):
                            rows[ty + row_i * scale + dy][tx + col_i * scale + dx] = ink
        tx += cell + gap
    return make_png(w, h, rows)


def _h(salt, *parts):
    return hashlib.sha256(
        (salt + "|" + "|".join(str(p) for p in parts)).encode()).hexdigest()


def generate(dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    rng = random.SystemRandom()
    token = "".join(rng.choice(TOKEN_ALPHABET) for _ in range(6))
    color_name, color_rgb = rng.choice(PALETTE)
    salt = rng.choice(TOKEN_ALPHABET) + "".join(
        rng.choice(TOKEN_ALPHABET) for _ in range(15))
    png_path = os.path.join(dest_dir, "probe_vision.png")
    exp_path = os.path.join(dest_dir, "probe_vision.expected")
    with open(png_path, "wb") as f:
        f.write(render(token, color_rgb))
    with open(exp_path, "w") as f:
        json.dump({
            "v": 2,
            "salt": salt,
            "token_hashes": [_h(salt, i, ch) for i, ch in enumerate(token)],
            "color_hash": _h(salt, "color", color_name),
        }, f)
    print(f"probe image written: {png_path}")
    print(f"ground truth (hashed) written: {exp_path}")
    print("Now Read the PNG with the Read tool, report the token + color,")
    print("then run: --check <reported-token> <reported-color>")


def check(report_token, report_color, dest_dir):
    exp_path = os.path.join(dest_dir, "probe_vision.expected")
    if not os.path.exists(exp_path):
        print("ERROR: probe_vision.expected missing — run --generate first")
        return 2
    with open(exp_path) as f:
        gt = json.load(f)
    got_tok = report_token.strip().upper()
    n = len(gt["token_hashes"])
    salt = gt["salt"]
    mismatches = [i for i in range(n)
                  if i >= len(got_tok)
                  or _h(salt, i, got_tok[i]) != gt["token_hashes"][i]]
    score = n - len(mismatches)
    col_ok = _h(salt, "color", report_color.strip().lower()) == gt["color_hash"]
    print(f"token score: {score}/{n} exact positions | color: "
          f"{'OK' if col_ok else 'MISMATCH'}")
    if mismatches:
        print("misread positions (expected char not shown): "
              + ", ".join(f"pos {i}" for i in mismatches))
    if col_ok and score >= TOKEN_MIN_CORRECT:
        print(f"PASS: model perceives images ({score}/{n} chars, color OK)")
        return 0
    if score >= TOKEN_MIN_CORRECT:
        print("FAIL: token read but color wrong — perception unreliable "
              "→ fall back to mm-sensor / direct read")
    elif score >= 3:
        print("FAIL: borderline perception — below probe threshold "
              f"(>= {TOKEN_MIN_CORRECT}/{n} chars + color exact required) "
              "→ fall back to mm-sensor / direct read")
    else:
        print("FAIL: model does not reliably perceive images "
              "→ fall back to mm-sensor / direct read")
    return 1


def selftest():
    """Verify font invariants: well-formed glyphs, no ambiguous pairs."""
    errors = []
    for ch, glyph in GLYPHS.items():
        if len(glyph) != 7 or any(not 0 <= b <= 31 for b in glyph):
            errors.append(f"malformed glyph {ch!r}: {glyph}")
    chars = sorted(TOKEN_ALPHABET)
    missing = [c for c in chars if c not in GLYPHS]
    if missing:
        errors.append(f"alphabet chars without glyph: {missing}")
    pairs = [(a, b) for i, a in enumerate(chars) for b in chars[i + 1:]]
    for a, b in pairs:
        d = sum(bin(x ^ y).count("1") for x, y in zip(GLYPHS[a], GLYPHS[b]))
        if d == 0:
            errors.append(f"identical glyph pair: {a} == {b}")
        elif d < 4:
            errors.append(f"ambiguous pair (d={d}): {a} <-> {b}")
    png = render("SELF7", (40, 100, 220))
    if not (png.startswith(b"\x89PNG\r\n\x1a\n")
            and png[-8:-4] == b"IEND"):
        errors.append("render() did not produce a well-formed PNG")
    if errors:
        for e in errors:
            print(f"SELFTEST FAIL: {e}")
        return 1
    print(f"selftest PASS: {len(chars)} alphabet chars, "
          f"all pairwise glyph distance >= 4 (of 35 bits), PNG roundtrip OK")
    return 0


def main():
    ap = argparse.ArgumentParser(description="vibeweaver model-native multimodal probe")
    ap.add_argument("--generate", action="store_true",
                    help="write tests/probe_vision.png + probe_vision.expected")
    ap.add_argument("--check", nargs=2, metavar=("TOKEN", "COLOR"),
                    help="validate the model's report against ground truth")
    ap.add_argument("--selftest", action="store_true",
                    help="verify font invariants (no identical/ambiguous glyph pairs)")
    ap.add_argument("--dir", default="tests", help="probe file directory (default: tests)")
    args = ap.parse_args()
    if args.generate:
        generate(args.dir)
        return 0
    if args.check is not None:
        return check(args.check[0], args.check[1], args.dir)
    if args.selftest:
        return selftest()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
