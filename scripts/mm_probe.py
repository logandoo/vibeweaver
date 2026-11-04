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

Comparative sub-probe (design-copy tasks, optional — TESTING_PROTOCOLS
§A4.1.2): the token probe proves recognition; this one probes COMPARATIVE
judgment (two nearly identical panels differing by exactly one change):
  python3 {VW_DIR}/scripts/mm_probe.py --compare-generate
    -> tests/probe_compare.png (two panels; ONE difference: moved / covered
       / color / added / removed, on a random shape) + hashed .expected.
  python3 {VW_DIR}/scripts/mm_probe.py --compare-check <variant> <shape>
    exit 0 = comparative judgment correct; 1 = incorrect/unreliable — record
    it and localize differences via T1/T2 clusters, never side-by-side
    eyeballing; 2 = usage (variant/shape not in the enumeration).
  Protocol guard (same rule as the token probe): do NOT open
  probe_compare.expected or brute-force --compare-check before reporting —
  the report must come from the pixels; repeated speculative --compare-check
  runs are a protocol violation.

Design notes (v2 — why it looks like this):
  * 5x7 dot-matrix glyphs (classic LCD proportions) rendered at 5px cells:
    a v1 3x5 font had 18+ glyph pairs differing by ONE pixel (S/5, V/Y,
    C/E, K/X, ...) and even a byte-identical pair (Z == 2), which made the
    old conjunctive "6/6 exact" check fail genuinely image-perceptive
    models on coin-flip glyphs (~68% of tokens contained a d<=2 pair).
  * TOKEN_ALPHABET is pruned to 28 chars: every pair is >= 4 bits apart
    (of 35). Run `--selftest` to re-verify this invariant after edits.
  * C3d (2026-10-15): the token is 10 chars and the expected file stores a
    WHOLE-TOKEN PBKDF2-HMAC-SHA256 (>=200k iters) + a slow color hash —
    reading probe_vision.expected must NOT let you compute the answer
    (the old per-position fast-SHA array was position-wise enumerable in
    ~360 derivations; a token hash is a 28^10 x 200k search). Exact match
    is required: a vision misread means re-Read and retry, not a weaker
    check (partial-credit scoring WAS the leak).
  * FAIL output never names expected characters.
    Repeated speculative --check runs are a protocol violation.
"""

import argparse
import hashlib
import json
import os
import random
import shutil
import struct
import sys
import tempfile
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
# C3d keeps the 28-char separable set — the plan's "36" needs the exact
# confusable pairs the font design excluded; 28^10 = 2^47.5 already beats
# the >=2^40 work factor (and PBKDF2 multiplies it). Selftest pins the
# pairwise >=4-bit separation invariant.
TOKEN_ALPHABET = "ABCDEFGHJKLNQRSTUVWXYZ234679"
TOKEN_LEN = 10

# C3d: the answer file must NOT allow computing the answer. Per-character
# fast hashes are position-wise enumerable (36 candidates/position) — the
# stored secret is a whole-token PBKDF2-HMAC-SHA256 (>=200k iterations):
# reading the expected file costs you a 32^10 x 200k search. Exact match
# (the old 5/6 partial-credit hash array WAS the leak); a misread means
# re-Read the PNG and retry, not a weaker check.
PBKDF2_ITERS = 200000
TOKEN_MIN_CORRECT = TOKEN_LEN

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
    """>=340x150 canvas (width grows with the token): color block top-left,
    5x7 token text below."""
    cell = 5 * scale                     # glyph advance: 25px + 10px gap
    gap = 2 * scale
    w = max(340, 24 + len(token) * (cell + gap) + 10)
    h = 150
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


def _slow(salt, secret):
    """C3d slow hash — shared by token/color/variant answers."""
    return hashlib.pbkdf2_hmac("sha256", str(secret).encode(),
                               str(salt).encode(), PBKDF2_ITERS).hex()


def generate(dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    rng = random.SystemRandom()
    token = "".join(rng.choice(TOKEN_ALPHABET) for _ in range(TOKEN_LEN))
    color_name, color_rgb = rng.choice(PALETTE)
    salt = rng.choice(TOKEN_ALPHABET) + "".join(
        rng.choice(TOKEN_ALPHABET) for _ in range(15))
    png_path = os.path.join(dest_dir, "probe_vision.png")
    exp_path = os.path.join(dest_dir, "probe_vision.expected")
    with open(png_path, "wb") as f:
        f.write(render(token, color_rgb))
    with open(exp_path, "w") as f:
        json.dump({
            "v": 3,
            "salt": salt,
            "token_len": len(token),
            "token_hash": _slow(salt, token),
            # color is BOUND to the token (review R-I3): a 5-guess palette
            # enumeration of an unbound color hash leaked half the answer
            "color_hash": _slow(salt + "|color", token + "|" + color_name),
        }, f)
    print(f"probe image written: {png_path}")
    print(f"ground truth (hashed) written: {exp_path}")
    print("Now Read the PNG with the Read tool, report the token + color,")
    print("then run: --check <reported-token> <reported-color>")
    return token, color_name


def check(report_token, report_color, dest_dir):
    exp_path = os.path.join(dest_dir, "probe_vision.expected")
    if not os.path.exists(exp_path):
        print("ERROR: probe_vision.expected missing — run --generate first")
        return 2
    with open(exp_path) as f:
        gt = json.load(f)
    if gt.get("v") != 3:
        print("ERROR: probe_vision.expected is a pre-C3d (fast-hash) file — "
              "regenerate it (--generate); reading it must not reveal the answer")
        return 2
    got_tok = report_token.strip().upper()
    n = int(gt.get("token_len", TOKEN_LEN))
    salt = gt["salt"]
    tok_ok = len(got_tok) == n and _slow(salt, got_tok) == gt["token_hash"]
    col_ok = _slow(salt + "|color", got_tok + "|" + report_color.strip().lower()) == gt["color_hash"]
    print(f"token: {'OK' if tok_ok else 'MISMATCH'} ({n} chars exact) | color: "
          f"{'OK' if col_ok else 'MISMATCH'}")
    if tok_ok and col_ok:
        print(f"PASS: model perceives images ({n}/{n} chars, color OK)")
        return 0
    if not tok_ok:
        print("FAIL: token mismatch — a one-char vision misread FAILS the probe "
              "by design (the expected file is brute-force-proof): re-Read "
              "tests/probe_vision.png and retry; if it keeps failing fall back "
              "to mm-sensor / direct read")
    else:
        print("FAIL: token read but color wrong — perception unreliable "
              "→ fall back to mm-sensor / direct read")
    return 1


# ==========================================================================
# Comparative sub-probe (GREEN) — two panels, exactly ONE difference;
# the report is <variant> <shape>; the ground truth is salted-hashed.
# ==========================================================================

COMPARE_VARIANTS = ("moved", "covered", "color", "added", "removed")
COMPARE_SHAPES = ("circle", "square", "bar", "dot")
COMPARE_PALETTE = [(220, 50, 50), (40, 100, 220), (50, 180, 90), (235, 150, 30),
                   (150, 60, 200), (60, 160, 200)]
PANEL_W, PANEL_H = 260, 160
PANEL_BG = (246, 246, 246)
COVER_COLOR = (110, 110, 110)
_HALF = {"circle": (14, 14), "square": (12, 12), "bar": (20, 6), "dot": (7, 7)}


def _fill_rect(rows, x, y, w, h, color):
    for yy in range(max(0, y), min(len(rows), y + h)):
        row = rows[yy]
        for xx in range(max(0, x), min(len(row), x + w)):
            row[xx] = color


def _fill_circle(rows, cx, cy, r, color):
    for yy in range(max(0, cy - r), min(len(rows), cy + r + 1)):
        row = rows[yy]
        for xx in range(max(0, cx - r), min(len(row), cx + r + 1)):
            if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                row[xx] = color


def _draw_shape(rows, shape, cx, cy, color):
    """Fixed glyph sizes — _shape_bbox must mirror them exactly."""
    if shape == "circle":
        _fill_circle(rows, cx, cy, 14, color)
    elif shape == "square":
        _fill_rect(rows, cx - 12, cy - 12, 24, 24, color)
    elif shape == "bar":
        _fill_rect(rows, cx - 20, cy - 6, 40, 12, color)
    else:  # dot
        _fill_circle(rows, cx, cy, 7, color)


def _shape_bbox(shape, cx, cy):
    if shape == "circle":
        return (cx - 14, cy - 14, 29, 29)
    if shape == "square":
        return (cx - 12, cy - 12, 24, 24)
    if shape == "bar":
        return (cx - 20, cy - 6, 40, 12)
    return (cx - 7, cy - 7, 15, 15)


def _compare_scenes(rng=None, variant=None):
    """Build the two panels; return (scene_a, scene_b, meta, info).
    info: {"changed": [raster rects], "samples": [(x, y, rgb), ...]}
    — enough for an independent semantic check of render-vs-claim."""
    rng = rng or random.SystemRandom()
    variant = variant or rng.choice(COMPARE_VARIANTS)
    slots = [(70, 50), (140, 45), (205, 115), (80, 118), (190, 45)]
    rng.shuffle(slots)
    shapes_pick = list(COMPARE_SHAPES)
    rng.shuffle(shapes_pick)
    colors = list(COMPARE_PALETTE)
    rng.shuffle(colors)
    items = [[shapes_pick[i], slots[i][0], slots[i][1], colors[i]]
             for i in range(3)]

    scene_a = [[PANEL_BG] * PANEL_W for _ in range(PANEL_H)]
    for shape, cx, cy, col in items:
        _draw_shape(scene_a, shape, cx, cy, col)
    scene_b = [row[:] for row in scene_a]

    target = items[rng.randrange(len(items))]
    t_rect = _shape_bbox(target[0], target[1], target[2])
    info = {"changed": [], "samples": []}
    if variant == "moved":
        dx, dy = rng.choice([(14, 0), (-14, 0), (0, 14), (0, -14)])
        _draw_shape(scene_b, target[0], target[1], target[2], PANEL_BG)
        tx = min(max(target[1] + dx, 40), PANEL_W - 40)
        ty = min(max(target[2] + dy, 32), PANEL_H - 32)
        _draw_shape(scene_b, target[0], tx, ty, target[3])
        n_rect = _shape_bbox(target[0], tx, ty)
        info["changed"] = [t_rect, n_rect]
        # vacated sample: the old shape's far edge along the move axis — a
        # point guaranteed inside the OLD mask and outside the NEW one (the
        # old center can sit inside the shifted shape when radius >= shift)
        hx, hy = _HALF[target[0]]
        edx, edy = tx - target[1], ty - target[2]
        if edx:
            vac = (target[1] - hx * (1 if edx > 0 else -1), target[2])
        else:
            vac = (target[1], target[2] - hy * (1 if edy > 0 else -1))
        info["samples"] = [vac + (PANEL_BG,),   # vacated pixel is background
                           (tx, ty, target[3])]
        shape_name = target[0]
    elif variant == "covered":
        bx, by, bw, bh = t_rect
        _fill_rect(scene_b, bx - 6, by - 6, bw + 12, bh + 12, COVER_COLOR)
        info["changed"] = [(bx - 6, by - 6, bw + 12, bh + 12)]
        info["samples"] = [(bx + 1, by + 1, COVER_COLOR),
                           (bx + bw - 1, by + 1, COVER_COLOR),
                           (bx + 1, by + bh - 1, COVER_COLOR),
                           (bx + bw - 1, by + bh - 1, COVER_COLOR),
                           (target[1], target[2], COVER_COLOR)]    # full cover
        shape_name = target[0]
    elif variant == "color":
        _draw_shape(scene_b, target[0], target[1], target[2], PANEL_BG)
        alt = [c for c in COMPARE_PALETTE + [(90, 90, 90), (60, 60, 220)]
               if c != target[3]]
        new_col = rng.choice(alt)
        _draw_shape(scene_b, target[0], target[1], target[2], new_col)
        info["changed"] = [t_rect]
        info["samples"] = [(target[1], target[2], new_col)]
        shape_name = target[0]
    elif variant == "added":
        extra = shapes_pick[3]
        _draw_shape(scene_b, extra, slots[3][0], slots[3][1], colors[3])
        a_rect = _shape_bbox(extra, slots[3][0], slots[3][1])
        info["changed"] = [a_rect]
        info["samples"] = [(slots[3][0], slots[3][1], colors[3])]
        shape_name = extra
    else:  # removed
        _draw_shape(scene_b, target[0], target[1], target[2], PANEL_BG)
        info["changed"] = [t_rect]
        info["samples"] = [(target[1], target[2], PANEL_BG)]
        shape_name = target[0]

    diff = 0
    for ya in range(PANEL_H):
        ra, rb = scene_a[ya], scene_b[ya]
        for xa in range(PANEL_W):
            if ra[xa] != rb[xa]:
                diff += 1
    meta = {"variant": variant, "shape": shape_name, "diff_pixels": diff}
    return scene_a, scene_b, meta, info


def render_compare(rng=None, variant=None):
    """Return (png_bytes, meta) — meta: {variant, shape, diff_pixels}.
    Exactly ONE change distinguishes panel B from panel A."""
    scene_a, scene_b, meta, _info = _compare_scenes(rng, variant)
    canvas_w, canvas_h = PANEL_W * 2 + 40, PANEL_H + 20
    canvas = [[(255, 255, 255)] * canvas_w for _ in range(canvas_h)]
    _fill_rect(canvas, 8, 8, PANEL_W + 4, PANEL_H + 4, (60, 60, 60))
    _fill_rect(canvas, PANEL_W + 28, 8, PANEL_W + 4, PANEL_H + 4, (60, 60, 60))
    for y in range(PANEL_H):
        for x in range(PANEL_W):
            canvas[10 + y][10 + x] = scene_a[y][x]
            canvas[10 + y][PANEL_W + 30 + x] = scene_b[y][x]
    return make_png(canvas_w, canvas_h, canvas), meta


def generate_compare(dest_dir, rng=None):
    """Write probe_compare.png + salted-hash probe_compare.expected.
    Returns the PNG path. The variant/shape never appear in plaintext."""
    os.makedirs(dest_dir, exist_ok=True)
    rng = rng or random.SystemRandom()
    png, meta = render_compare(rng=rng)
    salt = "".join(rng.choice(TOKEN_ALPHABET) for _ in range(16))
    png_path = os.path.join(dest_dir, "probe_compare.png")
    with open(png_path, "wb") as f:
        f.write(png)
    with open(os.path.join(dest_dir, "probe_compare.expected"), "w") as f:
        json.dump({
            "v": 1,
            "salt": salt,
            "variant_hash": _slow(salt + "|variant", meta["variant"]),
            "shape_hash": _slow(salt + "|shape", meta["shape"]),
        }, f)
    return png_path


def _compare_verify(gt, variant, shape):
    salt = gt["salt"]
    return (_slow(salt + "|variant", variant) == gt.get("variant_hash")
            and _slow(salt + "|shape", shape) == gt.get("shape_hash"))


def check_compare(report_variant, report_shape, dest_dir):
    exp_path = os.path.join(dest_dir, "probe_compare.expected")
    if not os.path.exists(exp_path):
        print("ERROR: probe_compare.expected missing — run --compare-generate first")
        return 2
    variant = report_variant.strip().lower()
    shape = report_shape.strip().lower()
    if variant not in COMPARE_VARIANTS or shape not in COMPARE_SHAPES:
        print(f"usage: variant from {COMPARE_VARIANTS}, shape from {COMPARE_SHAPES}")
        return 2
    try:
        with open(exp_path) as f:
            gt = json.load(f)
    except (ValueError, OSError) as e:
        print(f"ERROR: probe_compare.expected unreadable ({e}) — "
              f"re-run --compare-generate")
        return 2
    if (not isinstance(gt, dict)
            or not isinstance(gt.get("salt"), str)
            or not isinstance(gt.get("variant_hash"), str)
            or not isinstance(gt.get("shape_hash"), str)):
        print("ERROR: probe_compare.expected malformed — re-run --compare-generate")
        return 2
    ok_variant = _slow(gt["salt"] + "|variant", variant) == gt.get("variant_hash")
    ok_shape = _slow(gt["salt"] + "|shape", shape) == gt.get("shape_hash")
    if ok_variant and ok_shape:
        print("PASS: comparative judgment correct (variant + shape)")
        return 0
    wrong = ", ".join(name for name, ok in (("variant", ok_variant),
                                            ("shape", ok_shape)) if not ok)
    print(f"FAIL: comparative judgment incorrect/unreliable — wrong: {wrong}. "
          f"Record it; localize differences via T1/T2 clusters, never "
          f"side-by-side eyeballing.")
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
    # comparative sub-probe invariants: render-vs-claim semantics + uniqueness
    def _raster_area(_shape):
        scratch = [[PANEL_BG] * 40 for _ in range(40)]
        _draw_shape(scratch, _shape, 20, 20, (0, 0, 0))
        return sum(1 for row in scratch for px in row if px != PANEL_BG)

    for variant in COMPARE_VARIANTS:
        cscene_a, cscene_b, cmeta, cinfo = _compare_scenes(
            variant=variant, rng=random.Random(7))
        cpng, _cm = render_compare(variant=variant, rng=random.Random(7))
        if not (cpng.startswith(b"\x89PNG\r\n\x1a\n")
                and cpng[-8:-4] == b"IEND"):
            errors.append(f"compare render malformed PNG ({variant})")
        if cmeta.get("variant") != variant:
            errors.append(f"compare variant meta wrong ({variant})")
        if cmeta.get("diff_pixels", 0) < 80:
            errors.append(f"compare diff too small "
                          f"({variant}: {cmeta.get('diff_pixels')})")
        outside = 0
        for yy in range(PANEL_H):
            for xx in range(PANEL_W):
                if cscene_a[yy][xx] != cscene_b[yy][xx] and not any(
                        rx <= xx < rx + rw and ry <= yy < ry + rh
                        for rx, ry, rw, rh in cinfo["changed"]):
                    outside += 1
        if outside:
            errors.append(f"compare {variant}: {outside} diff px outside "
                          f"the declared change")
        for sx, sy, expected in cinfo["samples"]:
            if cscene_b[sy][sx] != expected:
                errors.append(f"compare {variant}: sample ({sx},{sy}) "
                              f"= {cscene_b[sy][sx]} != {expected}")
        if variant == "removed" and \
                cmeta["diff_pixels"] != _raster_area(cmeta["shape"]):
            errors.append("compare removed: shape name inconsistent with "
                          "the erased area")
    # C3d invariants: expected file is brute-force-proof + roundtrip works
    tmpq = tempfile.mkdtemp(prefix="mmprobe-seed-")
    try:
        tok, col = generate(tmpq)
        with open(os.path.join(tmpq, "probe_vision.expected")) as f:
            gt = json.load(f)
        if gt.get("v") != 3 or "token_hashes" in gt:
            errors.append(f"C3d: expected file not v3 whole-token (keys={sorted(gt)})")
        if len(tok) != TOKEN_LEN or any(c not in TOKEN_ALPHABET for c in tok):
            errors.append(f"C3d: token shape wrong ({tok!r})")
        if check(tok, col, tmpq) != 0:
            errors.append("C3d: generate->check roundtrip failed")
        if check("A" * TOKEN_LEN, "red" if col != "red" else "blue", tmpq) == 0:
            errors.append("C3d: a WRONG answer passed the check")
    finally:
        shutil.rmtree(tmpq, ignore_errors=True)
    tmpc = tempfile.mkdtemp(prefix="mmprobe-compare-")
    cpath = generate_compare(tmpc, rng=random.Random(11))
    if not os.path.exists(cpath):
        errors.append("compare png not written")
    exp = os.path.join(tmpc, "probe_compare.expected")
    if not os.path.exists(exp):
        errors.append("compare expected file not written")
    else:
        with open(exp) as f:
            cgt = json.load(f)
        solved = [(v, s) for v in COMPARE_VARIANTS for s in COMPARE_SHAPES
                  if _compare_verify(cgt, v, s)]
        if len(solved) != 1:
            errors.append(f"compare solution not unique (got {len(solved)})")
        if cgt.get("variant") or cgt.get("shape"):
            errors.append("compare expected file leaks plaintext")
    shutil.rmtree(tmpc, ignore_errors=True)
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
    ap.add_argument("--compare-generate", action="store_true",
                    help="write tests/probe_compare.png + .expected (comparative sub-probe)")
    ap.add_argument("--compare-check", nargs=2, metavar=("VARIANT", "SHAPE"),
                    help="validate the comparative report (variant + shape)")
    ap.add_argument("--dir", default="tests", help="probe file directory (default: tests)")
    args = ap.parse_args()
    actions = [bool(args.generate), args.check is not None,
               bool(args.compare_generate), args.compare_check is not None,
               bool(args.selftest)]
    if sum(actions) > 1:
        print("pick exactly ONE action (--generate / --check / "
              "--compare-generate / --compare-check / --selftest)",
              file=sys.stderr)
        return 2
    if args.generate:
        generate(args.dir)
        return 0
    if args.check is not None:
        return check(args.check[0], args.check[1], args.dir)
    if args.compare_generate:
        cpath = generate_compare(args.dir)
        print(f"compare probe written: {cpath}")
        print("Report the change: --compare-check <variant> <shape> "
              f"(variant from {COMPARE_VARIANTS}, shape from {COMPARE_SHAPES})")
        return 0
    if args.compare_check is not None:
        return check_compare(args.compare_check[0], args.compare_check[1],
                             args.dir)
    if args.selftest:
        return selftest()
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
