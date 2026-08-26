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
"""

import argparse
import json
import os
import random
import struct
import sys
import zlib

TOKEN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I ambiguity

PALETTE = [
    ("red", (220, 50, 50)),
    ("green", (50, 180, 90)),
    ("blue", (40, 100, 220)),
    ("orange", (235, 150, 30)),
    ("purple", (150, 60, 200)),
]

# 3x5 pixel font (rows of 3 bits, '1' = lit). Uppercase A-Z, digits 2-9.
# O/I/0/1 excluded by the alphabet above.
GLYPHS = {
    "A": [7, 5, 7, 5, 5], "B": [6, 5, 6, 5, 6], "C": [7, 4, 4, 4, 7],
    "D": [6, 5, 5, 5, 6], "E": [7, 4, 6, 4, 7], "F": [7, 4, 6, 4, 4],
    "G": [7, 4, 5, 5, 7], "H": [5, 5, 7, 5, 5], "I": [7, 2, 2, 2, 7],
    "J": [1, 1, 1, 5, 7], "K": [5, 5, 6, 5, 5], "L": [4, 4, 4, 4, 7],
    "M": [5, 7, 7, 5, 5], "N": [5, 7, 7, 7, 5], "O": [7, 5, 5, 5, 7],
    "P": [7, 5, 7, 4, 4], "Q": [7, 5, 5, 7, 1], "R": [7, 5, 7, 6, 5],
    "S": [7, 4, 7, 1, 7], "T": [7, 2, 2, 2, 2], "U": [5, 5, 5, 5, 7],
    "V": [5, 5, 5, 2, 2], "W": [5, 5, 7, 7, 5], "X": [5, 5, 2, 5, 5],
    "Y": [5, 5, 2, 2, 2], "Z": [7, 1, 2, 4, 7],
    "2": [7, 1, 2, 4, 7], "3": [6, 1, 2, 1, 6], "4": [5, 5, 7, 1, 1],
    "5": [7, 4, 6, 1, 6], "6": [7, 4, 6, 5, 7], "7": [7, 1, 2, 2, 2],
    "8": [7, 5, 7, 5, 7], "9": [7, 5, 7, 1, 7],
}


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


def render(token, color):
    """300x120 white canvas: color block top-left, token text below."""
    w, h, scale = 300, 120, 4
    bg = (250, 250, 250)
    rows = [[bg for _ in range(w)] for _ in range(h)]
    for y in range(24, 66):                    # color block: y 24-66
        for x in range(24, 66):
            rows[y][x] = color
    tx, ty, ls = 24, 74, 4                     # text at (24, 74), 4px cells
    for ch in token:
        for row_i, bits in enumerate(GLYPHS[ch]):
            for col_i in range(3):
                if bits & (1 << (2 - col_i)):
                    for dy in range(ls):
                        for dx in range(ls):
                            rows[ty + row_i * ls + dy][tx + col_i * ls + dx] = (30, 30, 30)
        tx += 4 * ls
    return make_png(w, h, rows)


def generate(dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    token = "".join(random.SystemRandom().choice(TOKEN_ALPHABET) for _ in range(6))
    color_name, color_rgb = random.choice(PALETTE)
    png_path = os.path.join(dest_dir, "probe_vision.png")
    exp_path = os.path.join(dest_dir, "probe_vision.expected")
    with open(png_path, "wb") as f:
        f.write(render(token, color_rgb))
    with open(exp_path, "w") as f:
        json.dump({"token": token, "color": color_name}, f)
    print(f"probe image written: {png_path}")
    print(f"ground truth written: {exp_path}")
    print("Now Read the PNG with the Read tool, report the token + color,")
    print("then run: --check <reported-token> <reported-color>")


def check(report_token, report_color, dest_dir):
    exp_path = os.path.join(dest_dir, "probe_vision.expected")
    if not os.path.exists(exp_path):
        print("FAIL: probe_vision.expected missing — run --generate first")
        return 2
    with open(exp_path) as f:
        gt = json.load(f)
    tok_ok = report_token.strip().upper() == gt["token"]
    col_ok = report_color.strip().lower() == gt["color"]
    if tok_ok and col_ok:
        print(f"PASS: model perceives images (token={gt['token']}, color={gt['color']})")
        return 0
    print(f"FAIL: expected token={gt['token']!r} color={gt['color']!r} | "
          f"reported token={report_token!r} color={report_color!r}")
    print("Model is NOT image-perceptive → fall back to mm-sensor / direct read")
    return 1


def main():
    ap = argparse.ArgumentParser(description="vibeweaver model-native multimodal probe")
    ap.add_argument("--generate", action="store_true",
                    help="write tests/probe_vision.png + probe_vision.expected")
    ap.add_argument("--check", nargs=2, metavar=("TOKEN", "COLOR"),
                    help="validate the model's report against ground truth")
    ap.add_argument("--dir", default="tests", help="probe file directory (default: tests)")
    args = ap.parse_args()
    if args.generate:
        generate(args.dir)
        return 0
    if args.check is not None:
        return check(args.check[0], args.check[1], args.dir)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
