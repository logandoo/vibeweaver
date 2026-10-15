#!/usr/bin/env python3
"""ui_fidelity.py — design-copy fidelity measurement (stdlib only).

Measures whether a re-implemented UI matches a reference, for tasks whose
acceptance criteria name pixel/geometry fidelity (TESTING_PROTOCOLS.md
§A4.1.2 — the T1/T2 measurement tiers; templates in APPENDIX.md §A4.1.2):

  diff   REF.png CAND.png  — pixel diff with the pixelmatch v5.3.0 algorithm
         (YIQ colorDelta + anti-aliasing detection; ported from
         https://github.com/mapbox/pixelmatch, MIT (c) Mapbox) + diff
         clustering, writing a diff image and a JSON report.
  boxes  REF.json CAND.json — per-element bounding-box deltas (size/position),
         overlap detection (non-containment intersections), and occlusion
         verdicts (elements whose `occluded_by` list from the capture snippet
         is non-empty).
  refboxes REF.png — candidate foreground regions of a reference IMAGE
         (background = most frequent coarse color, or --bg RRGGBB), clustered
         with gap-merge; output ui-refboxes-<name>.json uses the boxes element
         schema (+"pixels") so it can serve as the REF.json of `boxes` when
         the reference is an image (pair candidate dumps in reading order —
         the ordinal fallback needs disjoint, equal-length name sets).
         Alpha is composited over white (transparent = white page); assumes a
         (near-)flat background — gradients/photos/stripes produce noise
         regions (check the preview). Stdout reports `N/total` with a
         truncation note when merging was skipped (> --merge-cap components)
         or results exceed --max-boxes; a partial ref list silently mispairs
         via the ordinal fallback, so read the count line.

Analysis is instrumental: deterministic, offline, no model/network/deps.
Capture (Playwright at a fixed viewport/DPR, animations frozen, fonts
awaited, caret hidden — APPENDIX.md §A4.1.2) happens in the project's own test
code; this script only scores the captured artifacts.

Exit codes: diff/boxes — 0 = pass · 1 = fail (diff/tolerance/overlap; a size
mismatch stays a fail even after --allow-dim-mismatch) · 2 = usage/IO error
(bad flags, missing/unreadable/corrupt files, malformed dumps) · 3 = image
size mismatch refused. refboxes — 0 = success (extraction has no pass/fail;
the downstream `boxes` gate decides), 2 = usage/IO error.

JSON schemas (version 1):
  diff:  {"version":1,"kind":"pixel-diff","ref","cand","width","height",
          "diff_pixels","total_pixels","diff_percent","max_diff_percent",
          "threshold","aa":bool,"pass":bool,
          "dimensions":{"ref":[w,h],"cand":[w,h],"mismatch":bool},
          "aa_pixels","clusters":[{"x","y","w","h","pixels"}],
          "total_clusters","clusters_truncated","diff_image"}
          ("clusters" holds the top 50; total_clusters/clusters_truncated
          keep the truncation visible; "diff_image"/"aa_pixels"/"clusters"
          are null/empty when the size mismatch is refused)
  boxes: {"version":1,"kind":"boxes","pass","tolerance_px",
          "elements":[{"name","ref":[x,y,w,h],"cand":[x,y,w,h],"dx","dy",
                       "dw","dh","status","occluded_by"}],
          "missing_in_cand":[...],"extra_in_cand":[...],
          "overlaps":[{"a","b","x","y","w","h","area"}]}
  status: ok | moved | resized | moved+resized | occluded | missing_in_cand
          | extra_in_cand

--selftest runs in-memory synthetic checks (PNG codec roundtrip, known
diff count/cluster, threshold behavior, dimension handling, box delta and
overlap logic) and prints PASS/FAIL — no project files touched.

Gray output rounding follows the browser Uint8ClampedArray convention (±1
vs the Node CLI's Buffer truncation on unchanged pixels only; counts and
classification are identical).
"""

import argparse
import json
import os
import struct
import sys
import tempfile
import zlib

PNG_SIG = b"\x89PNG\r\n\x1a\n"

# ==========================================================================
# PNG codec (8-bit RGB/RGBA, non-interlaced — Playwright/browser output)
# ==========================================================================


def read_png(path):
    """Return (width, height, rgba_bytes). Raises ValueError on unsupported PNG."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != PNG_SIG:
        raise ValueError(f"{path}: not a PNG file")
    w = h = bitdepth = colortype = interlace = None
    idat = b""
    pos = 8
    while pos + 8 <= len(data):
        ln = int.from_bytes(data[pos:pos + 4], "big")
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        pos += 12 + ln
        if ctype == b"IHDR":
            w, h, bitdepth, colortype, _comp, _filt, interlace = struct.unpack(">IIBBBBB", body)
        elif ctype == b"IDAT":
            idat += body
        elif ctype == b"IEND":
            break
    if w is None or bitdepth != 8 or interlace != 0 or colortype not in (2, 6):
        raise ValueError(
            f"{path}: unsupported PNG (need 8-bit RGB/RGBA, non-interlaced)")
    raw = zlib.decompress(idat)
    bpp = 4 if colortype == 6 else 3
    stride = w * bpp
    out = bytearray()
    prev = bytearray(stride)
    p = 0
    for _y in range(h):
        flt = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if flt == 0:
            pass
        elif flt == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif flt == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif flt == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif flt == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                pa, pb, pc = abs(a + b - c - a), abs(a + b - c - b), abs(a + b - c - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        else:
            raise ValueError(f"{path}: unknown PNG filter {flt}")
        out += line
        prev = line
    if colortype == 6:
        rgba = bytes(out)
    else:
        rgba = bytearray(len(out) // 3 * 4)
        for i in range(len(out) // 3):
            rgba[4 * i:4 * i + 3] = out[3 * i:3 * i + 3]
            rgba[4 * i + 3] = 255
        rgba = bytes(rgba)
    return w, h, rgba


def write_png(path, w, h, rgba):
    """Write an 8-bit RGBA PNG (filter type 0, color type 6)."""
    raw = bytearray()
    stride = w * 4
    for y in range(h):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]

    def chunk(tag, body):
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

    data = (PNG_SIG
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)


def crop_rgba(rgba, w, h, cw, ch):
    """Crop to (cw, ch) keeping the top-left origin."""
    out = bytearray()
    for y in range(ch):
        out += rgba[(y * w) * 4:(y * w + cw) * 4]
    return bytes(out)


# ==========================================================================
# pixelmatch v5.3.0 port (GREEN) — YIQ colorDelta + anti-aliasing detection,
# faithful to https://github.com/mapbox/pixelmatch (MIT (c) Mapbox).
# color_delta: "Measuring perceived color difference using YIQ NTSC
# transmission color space" (Kotsarenko & Ramos, 2010); antialiased():
# Vyšniauskas, "Anti-aliased Pixel and Intensity Slope Detector" (2009).
# ==========================================================================


def rgb2y(r, g, b):
    return r * 0.29889531 + g * 0.58662247 + b * 0.11448223


def rgb2i(r, g, b):
    return r * 0.59597799 - g * 0.27417610 - b * 0.32180189


def rgb2q(r, g, b):
    return r * 0.21147017 - g * 0.52261711 + b * 0.31114694


def _blend(c, a):
    return 255 + (c - 255) * a


def color_delta(img1, img2, k, m, y_only=False):
    """Squared YIQ distance at two offsets; sign negative if img2 is darker."""
    r1, g1, b1, a1 = img1[k], img1[k + 1], img1[k + 2], img1[k + 3]
    r2, g2, b2, a2 = img2[m], img2[m + 1], img2[m + 2], img2[m + 3]
    if a1 == a2 and r1 == r2 and g1 == g2 and b1 == b2:
        return 0
    if a1 < 255:
        af = a1 / 255
        r1, g1, b1 = _blend(r1, af), _blend(g1, af), _blend(b1, af)
    if a2 < 255:
        af = a2 / 255
        r2, g2, b2 = _blend(r2, af), _blend(g2, af), _blend(b2, af)
    y = rgb2y(r1, g1, b1) - rgb2y(r2, g2, b2)
    if y_only:
        return y
    i = rgb2i(r1, g1, b1) - rgb2i(r2, g2, b2)
    q = rgb2q(r1, g1, b1) - rgb2q(r2, g2, b2)
    delta = 0.5053 * y * y + 0.299 * i * i + 0.1957 * q * q
    return -delta if y > 0 else delta


def has_many_siblings(img, x1, y1, width, height):
    """True when a pixel has 3+ adjacent pixels of the same color."""
    x0, y0 = max(x1 - 1, 0), max(y1 - 1, 0)
    x2, y2 = min(x1 + 1, width - 1), min(y1 + 1, height - 1)
    pos = (y1 * width + x1) * 4
    zeroes = 1 if (x1 == x0 or x1 == x2 or y1 == y0 or y1 == y2) else 0
    for x in range(x0, x2 + 1):
        for y in range(y0, y2 + 1):
            if x == x1 and y == y1:
                continue
            pos2 = (y * width + x) * 4
            if (img[pos] == img[pos2] and img[pos + 1] == img[pos2 + 1]
                    and img[pos + 2] == img[pos2 + 2]
                    and img[pos + 3] == img[pos2 + 3]):
                zeroes += 1
            if zeroes > 2:
                return True
    return False


def antialiased(img, x1, y1, width, height, img2):
    """True when the pixel at (x1,y1) is likely anti-aliasing (pixelmatch rule)."""
    x0, y0 = max(x1 - 1, 0), max(y1 - 1, 0)
    x2, y2 = min(x1 + 1, width - 1), min(y1 + 1, height - 1)
    pos = (y1 * width + x1) * 4
    zeroes = 1 if (x1 == x0 or x1 == x2 or y1 == y0 or y1 == y2) else 0
    mn = mx = 0
    min_x = min_y = max_x = max_y = 0
    for x in range(x0, x2 + 1):
        for y in range(y0, y2 + 1):
            if x == x1 and y == y1:
                continue
            delta = color_delta(img, img, pos, (y * width + x) * 4, True)
            if delta == 0:
                zeroes += 1
                if zeroes > 2:
                    return False
            elif delta < mn:
                mn = delta
                min_x, min_y = x, y
            elif delta > mx:
                mx = delta
                max_x, max_y = x, y
    if mn == 0 or mx == 0:
        return False
    return ((has_many_siblings(img, min_x, min_y, width, height)
             and has_many_siblings(img2, min_x, min_y, width, height))
            or (has_many_siblings(img, max_x, max_y, width, height)
                and has_many_siblings(img2, max_x, max_y, width, height)))


def _gray_pixel(img, pos):
    v = _blend(rgb2y(img[pos], img[pos + 1], img[pos + 2]),
               0.1 * img[pos + 3] / 255)
    v = int(round(v))
    return bytes((max(0, min(255, v)),) * 3 + (255,))


def diff_images(img1, img2, width, height, threshold=0.1, include_aa=False,
                draw=True):
    """Pixel-diff two RGBA buffers (same size).

    Returns (diff_count, out_rgba_or_None, aa_count, diff_points) where
    out_rgba draws: unchanged = dimmed gray, anti-aliased = yellow, differing
    = red (pixelmatch's output convention)."""
    if len(img1) != width * height * 4 or len(img2) != width * height * 4:
        raise ValueError("RGBA data does not match width*height*4")
    if img1 == img2:  # fast path if identical
        if not draw:
            return 0, None, 0, []
        out = bytearray(width * height * 4)
        for i in range(width * height):
            out[i * 4:i * 4 + 4] = _gray_pixel(img1, i * 4)
        return 0, bytes(out), 0, []
    max_delta = 35215 * threshold * threshold
    out = bytearray(width * height * 4) if draw else None
    diff = 0
    aa_count = 0
    points = []
    for y in range(height):
        for x in range(width):
            pos = (y * width + x) * 4
            delta = color_delta(img1, img2, pos, pos)
            if abs(delta) > max_delta:
                if (not include_aa) and (
                        antialiased(img1, x, y, width, height, img2)
                        or antialiased(img2, x, y, width, height, img1)):
                    aa_count += 1
                    if draw:
                        out[pos:pos + 4] = bytes((255, 255, 0, 255))
                else:
                    diff += 1
                    points.append((x, y))
                    if draw:
                        out[pos:pos + 4] = bytes((255, 0, 0, 255))
            elif draw:
                out[pos:pos + 4] = _gray_pixel(img1, pos)
    return diff, (bytes(out) if draw else None), aa_count, points


# ==========================================================================
# Diff clustering
# ==========================================================================


def cluster_pixels(points, gap=4, max_clusters=50, merge_cap=1024):
    """8-connected components over diff pixels, then merge component
    bounding boxes within `gap` px (union-find rounds; merging is skipped
    above `merge_cap` components to keep worst-case runtime bounded).

    Returns (clusters, total, merge_skipped) — `clusters` holds the top
    `max_clusters` by pixel count; `total` is the cluster count AFTER
    gap-merging (before the top-`max_clusters` cut), so
    `clusters_truncated = len(clusters) < total` never false-positives on a
    fully listed merged set; `merge_skipped` says the gap-merge stage was
    skipped (component count > merge_cap — results may be under-merged)."""
    remaining = set(points)
    raw = []
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        minx = maxx = seed[0]
        miny = maxy = seed[1]
        n = 1
        while stack:
            x, y = stack.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in remaining:
                        remaining.remove(q)
                        stack.append(q)
                        n += 1
                        minx = min(minx, q[0])
                        maxx = max(maxx, q[0])
                        miny = min(miny, q[1])
                        maxy = max(maxy, q[1])
        raw.append([minx, miny, maxx, maxy, n])
    merge_skipped = len(raw) > 1 and len(raw) > merge_cap

    def gap_between(a, b):
        dx = max(0, max(a[0], b[0]) - min(a[2], b[2]) - 1)
        dy = max(0, max(a[1], b[1]) - min(a[3], b[3]) - 1)
        return max(dx, dy)

    if 1 < len(raw) <= merge_cap:
        parent = list(range(len(raw)))
        bbox = [list(c) for c in raw]

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        while True:
            merged = False
            roots = sorted({find(i) for i in range(len(raw))})
            for ii in range(len(roots)):
                for jj in range(ii + 1, len(roots)):
                    a, b = find(roots[ii]), find(roots[jj])
                    if a == b:
                        continue
                    if gap_between(bbox[a], bbox[b]) <= gap:
                        parent[b] = a
                        ab, bb = bbox[a], bbox[b]
                        bbox[a] = [min(ab[0], bb[0]), min(ab[1], bb[1]),
                                   max(ab[2], bb[2]), max(ab[3], bb[3]),
                                   ab[4] + bb[4]]
                        merged = True
            if not merged:
                break
        raw = [bbox[i] for i in range(len(raw)) if parent[i] == i]

    total = len(raw)
    raw.sort(key=lambda c: -c[4])
    clusters = [{"x": c[0], "y": c[1], "w": c[2] - c[0] + 1,
                 "h": c[3] - c[1] + 1, "pixels": c[4]}
                for c in raw[:max_clusters]]
    return clusters, total, merge_skipped


# ==========================================================================
# diff subcommand
# ==========================================================================


def run_diff(ref_path, cand_path, out_dir, name, threshold, max_diff_percent,
             include_aa, allow_dim_mismatch):
    w1, h1, img1 = read_png(ref_path)
    w2, h2, img2 = read_png(cand_path)
    dim_mismatch = (w1, h1) != (w2, h2)
    if dim_mismatch and not allow_dim_mismatch:
        report = {
            "version": 1, "kind": "pixel-diff", "ref": ref_path, "cand": cand_path,
            "width": w1, "height": h1, "diff_pixels": None, "total_pixels": w1 * h1,
            "diff_percent": None, "max_diff_percent": max_diff_percent,
            "threshold": threshold, "aa": not include_aa, "pass": False,
            "dimensions": {"ref": [w1, h1], "cand": [w2, h2], "mismatch": True},
            "aa_pixels": None, "clusters": [], "total_clusters": 0,
            "clusters_truncated": False, "diff_image": None,
        }
        _write_reports(out_dir, name, report, None)
        print(f"[ui_fidelity] diff: size mismatch {w1}x{h1} vs {w2}x{h2} — "
              f"refused (allow with --allow-dim-mismatch)")
        return 3
    w, h = min(w1, w2), min(h1, h2)
    if dim_mismatch:
        img1 = crop_rgba(img1, w1, h1, w, h)
        img2 = crop_rgba(img2, w2, h2, w, h)
    diff_px, out_rgba, aa_px, points = diff_images(
        img1, img2, w, h, threshold=threshold, include_aa=include_aa, draw=True)
    total = w * h
    pct = diff_px / total * 100.0 if total else 0.0
    clusters, total_clusters, _mskip = cluster_pixels(points) if points \
        else ([], 0, False)
    passed = (pct <= max_diff_percent) and not dim_mismatch
    report = {
        "version": 1, "kind": "pixel-diff", "ref": ref_path, "cand": cand_path,
        "width": w, "height": h, "diff_pixels": diff_px, "total_pixels": total,
        "diff_percent": round(pct, 4), "max_diff_percent": max_diff_percent,
        "threshold": threshold, "aa": not include_aa, "pass": passed,
        "dimensions": {"ref": [w1, h1], "cand": [w2, h2], "mismatch": dim_mismatch},
        "aa_pixels": aa_px, "clusters": clusters,
        "total_clusters": total_clusters,
        "clusters_truncated": len(clusters) < total_clusters,
        "diff_image": f"ui-diff-{name}.png",
    }
    _write_reports(out_dir, name, report, out_rgba, (w, h))
    verdict = "PASS" if passed else "FAIL"
    print(f"[ui_fidelity] diff: {diff_px}/{total} px ({pct:.4f}%) | "
          f"max {max_diff_percent:.4f}% | clusters {len(clusters)}/{total_clusters} "
          f"| aa {aa_px} | sizes {w1}x{h1} vs {w2}x{h2} | {verdict}")
    for c in clusters[:10]:
        print(f"  cluster: x={c['x']} y={c['y']} w={c['w']} h={c['h']} px={c['pixels']}")
    return 0 if passed else 1


# ==========================================================================
# boxes subcommand
# ==========================================================================


def _contains(outer, inner, tol=0.0):
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return (ox - tol <= ix and oy - tol <= iy
            and ox + ow + tol >= ix + iw and oy + oh + tol >= iy + ih)


def _synthesize_names(elements):
    """Name-less dumps (e.g. positional crops) get stable positional names so
    keyed matching works; explicit names are never overloaded."""
    if all(not e.get("name") for e in elements):
        return [dict(e, name=f"elem#{i}") for i, e in enumerate(elements)]
    return elements


def boxes_report(ref, cand, tol_px, allow_overlap=(), allow_occluded=()):
    """ref/cand: lists of {"name","x","y","w","h"[,"occluded_by"]}.
    Returns the boxes report dict (without IO)."""
    ref = _synthesize_names(ref)
    cand = _synthesize_names(cand)
    ref_names = [e["name"] for e in ref]
    cand_names = [e["name"] for e in cand]
    dup_names = (len(set(ref_names)) != len(ref_names)
                 or len(set(cand_names)) != len(cand_names))
    ref_by = {e["name"]: e for e in ref}
    cand_by = {e["name"]: e for e in cand}
    elements = []
    missing = [n for n in ref_names if n not in cand_by]
    extra = [n for n in cand_names if n not in ref_by]

    # ordinal fallback: ONE side uses a different selector vocabulary (equal
    # length, disjoint, duplicate-free) — pair positionally. Duplicate names
    # or overlapping sets disable it: a wrong pairing reported as clean is
    # worse than reporting missing/extra.
    if (not dup_names) and missing and extra and len(ref) == len(cand) \
            and not (set(ref_names) & set(cand_names)):
        for r_el, c_el in zip(ref, cand):
            if r_el["name"] in missing and c_el["name"] in extra:
                missing.remove(r_el["name"])
                extra.remove(c_el["name"])
                cand_by[r_el["name"]] = c_el

    for r_el in ref:
        name = r_el["name"]
        c_el = cand_by.get(name)
        if c_el is None:
            elements.append({"name": name, "ref": _rect(r_el), "cand": None,
                             "dx": None, "dy": None, "dw": None, "dh": None,
                             "status": "missing_in_cand",
                             "occluded_by": []})
            continue
        dx = c_el["x"] - r_el["x"]
        dy = c_el["y"] - r_el["y"]
        dw = c_el["w"] - r_el["w"]
        dh = c_el["h"] - r_el["h"]
        flags = []
        if abs(dx) > tol_px or abs(dy) > tol_px:
            flags.append("moved")
        if abs(dw) > tol_px or abs(dh) > tol_px:
            flags.append("resized")
        occl = list(c_el.get("occluded_by") or [])
        if occl and name not in allow_occluded:
            flags.append("occluded")
        elements.append({
            "name": name, "ref": _rect(r_el), "cand": _rect(c_el),
            "dx": round(dx, 2), "dy": round(dy, 2),
            "dw": round(dw, 2), "dh": round(dh, 2),
            "status": "+".join(flags) if flags else "ok", "occluded_by": occl,
        })
    for name in extra:
        c_el = cand_by[name]
        elements.append({"name": name, "ref": None, "cand": _rect(c_el),
                         "dx": None, "dy": None, "dw": None, "dh": None,
                         "status": "extra_in_cand", "occluded_by": []})

    # overlap detection among candidate boxes (non-containment intersections)
    overlaps = []
    allow_pairs = set()
    for p in allow_overlap:
        a, sep, b = p.rpartition(":")
        if sep:  # split on the LAST colon: selector names may contain ':'
            allow_pairs.add(tuple(sorted((a, b))))
    rects = [(e["name"], _rect(e)) for e in cand]
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            (na, ra), (nb, rb) = rects[i], rects[j]
            if tuple(sorted((na, nb))) in allow_pairs:
                continue
            ix = max(ra[0], rb[0])
            iy = max(ra[1], rb[1])
            ix2 = min(ra[0] + ra[2], rb[0] + rb[2])
            iy2 = min(ra[1] + ra[3], rb[1] + rb[3])
            iw, ih = ix2 - ix, iy2 - iy
            if iw <= 0 or ih <= 0:
                continue
            if _contains(ra, rb, 0.5) or _contains(rb, ra, 0.5):
                continue  # parent/child containment is not a collision
            overlaps.append({"a": na, "b": nb, "x": ix, "y": iy,
                             "w": iw, "h": ih, "area": iw * ih})

    passed = (not missing and not extra
              and all(e["status"] == "ok" for e in elements)
              and not overlaps)
    return {"version": 1, "kind": "boxes", "pass": passed,
            "tolerance_px": tol_px, "elements": elements,
            "missing_in_cand": missing, "extra_in_cand": extra,
            "overlaps": overlaps}


def _rect(e):
    return [round(e["x"], 2), round(e["y"], 2), round(e["w"], 2), round(e["h"], 2)]


def run_boxes(ref_path, cand_path, out_dir, name, tol_px, allow_overlap, allow_occluded):
    with open(ref_path) as f:
        ref = json.load(f)
    with open(cand_path) as f:
        cand = json.load(f)
    if not isinstance(ref, list) or not isinstance(cand, list):
        raise ValueError("boxes inputs must be JSON arrays of element objects")
    for label, lst in (("ref", ref), ("cand", cand)):
        for e in lst:
            if not isinstance(e, dict) or not all(
                    k in e for k in ("name", "x", "y", "w", "h")):
                raise ValueError(
                    f"{label} element missing name/x/y/w/h: {e!r}")
    report = boxes_report(ref, cand, tol_px, allow_overlap, allow_occluded)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"ui-boxes-{name}.json"), "w") as f:
        json.dump(report, f, indent=1)
    with open(os.path.join(out_dir, f"ui-boxes-{name}.md"), "w") as f:
        f.write("| element | status | dx | dy | dw | dh |\n|---|---|---|---|---|---|\n")
        for e in report["elements"]:
            f.write(f"| {e['name']} | {e['status']} | {e['dx']} | {e['dy']} "
                    f"| {e['dw']} | {e['dh']} |\n")
    verdict = "PASS" if report["pass"] else "FAIL"
    print(f"[ui_fidelity] boxes: {len(report['elements'])} elements | "
          f"missing {len(report['missing_in_cand'])} | extra {len(report['extra_in_cand'])} "
          f"| overlaps {len(report['overlaps'])} | tol {tol_px}px | {verdict}")
    for e in report["elements"]:
        if e["status"] != "ok":
            print(f"  {e['status']}: {e['name']} dx={e['dx']} dy={e['dy']} "
                  f"dw={e['dw']} dh={e['dh']}")
    return 0 if report["pass"] else 1


def _write_reports(out_dir, name, report, out_rgba=None, size=None):
    os.makedirs(out_dir, exist_ok=True)
    if out_rgba is not None and size is not None:
        write_png(os.path.join(out_dir, f"ui-diff-{name}.png"),
                  size[0], size[1], out_rgba)
    with open(os.path.join(out_dir, f"ui-diff-{name}.json"), "w") as f:
        json.dump(report, f, indent=1)


# ==========================================================================
# refboxes — reference-image region extraction (GREEN)
# Candidate foreground regions (background differs beyond --tol), clustered
# with the same 8-connectivity + gap-merge as the diff clusters. Output uses
# the boxes element schema so it can serve as the REF.json of `boxes` when
# the reference is an image (pair candidate dumps in reading order).
# ==========================================================================


def _flat_rgb(rgba, o):
    """Pixel RGB composited over white (same alpha handling as color_delta);
    a fully transparent pixel reads as white — invisible on a white page."""
    a = rgba[o + 3]
    if a >= 255:
        return (rgba[o], rgba[o + 1], rgba[o + 2])
    af = a / 255
    return (int(_blend(rgba[o], af) + 0.5),
            int(_blend(rgba[o + 1], af) + 0.5),
            int(_blend(rgba[o + 2], af) + 0.5))


def _auto_bg(w, h, rgba):
    """Most frequent coarse-quantized color over a sampled grid, averaged."""
    step = max(1, min(w, h) // 64)
    counts = {}
    for y in range(0, h, step):
        base = y * w * 4
        for x in range(0, w, step):
            r, g, b = _flat_rgb(rgba, base + x * 4)
            key = (r >> 4, g >> 4, b >> 4)
            counts[key] = counts.get(key, 0) + 1
    key = max(counts, key=counts.get)
    acc = [0, 0, 0]
    n = 0
    for y in range(0, h, step):
        base = y * w * 4
        for x in range(0, w, step):
            r, g, b = _flat_rgb(rgba, base + x * 4)
            if (r >> 4, g >> 4, b >> 4) == key:
                acc[0] += r
                acc[1] += g
                acc[2] += b
                n += 1
    return (acc[0] // n, acc[1] // n, acc[2] // n)


def refboxes_report(w, h, rgba, bg=None, tol=24, min_area=64, gap=6,
                    max_boxes=200, merge_cap=2048):
    """Return (regions, bg, truncated, total_kept). Foreground = white-
    composited pixels differing from `bg` by more than `tol` on any channel;
    regions use the boxes element schema (+"pixels"). `truncated` is True
    when cluster merging was skipped (raw components > merge_cap) or more
    than max_boxes regions survived the min-area filter."""
    if bg is None:
        bg = _auto_bg(w, h, rgba)
    points = []
    for y in range(h):
        base = y * w * 4
        for x in range(w):
            r, g, b = _flat_rgb(rgba, base + x * 4)
            if (abs(r - bg[0]) > tol or abs(g - bg[1]) > tol
                    or abs(b - bg[2]) > tol):
                points.append((x, y))
    clusters, total, merge_skipped = cluster_pixels(
        points, gap=gap, max_clusters=max(max_boxes * 4, 256),
        merge_cap=merge_cap)
    regions = [c for c in clusters
               if c["pixels"] >= min_area and c["w"] >= 3 and c["h"] >= 3]
    truncated = (len(clusters) < total or len(regions) > max_boxes
                 or merge_skipped)
    regions.sort(key=lambda c: (c["y"] // 20, c["x"]))
    out = [{"name": f"region#{i}", "x": c["x"], "y": c["y"],
            "w": c["w"], "h": c["h"], "pixels": c["pixels"]}
           for i, c in enumerate(regions[:max_boxes], 1)]
    return out, bg, truncated, len(regions)


def _draw_outline(buf, w, h, x, y, bw, bh, color=(220, 30, 30), t=2):
    """Draw a t-px rectangle outline into an RGBA bytearray (in place)."""
    for yy in range(max(0, y), min(h, y + bh)):
        for xx in range(max(0, x), min(w, x + bw)):
            if (xx < x + t or xx >= x + bw - t
                    or yy < y + t or yy >= y + bh - t):
                o = (yy * w + xx) * 4
                buf[o:o + 3] = bytes(color)


def run_refboxes(ref_path, out_dir, name, bg_hex, tol, min_area, gap,
                 max_boxes, merge_cap):
    w, h, rgba = read_png(ref_path)
    bg = None
    if bg_hex:
        if not (len(bg_hex) == 6
                and all(c in "0123456789abcdefABCDEF" for c in bg_hex)):
            raise ValueError("--bg must be exactly 6 hex digits (RRGGBB)")
        bg = tuple(int(bg_hex[i:i + 2], 16) for i in (0, 2, 4))
    regions, bg, truncated, total = refboxes_report(
        w, h, rgba, bg=bg, tol=tol, min_area=min_area, gap=gap,
        max_boxes=max_boxes, merge_cap=merge_cap)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"ui-refboxes-{name}.json"), "w") as f:
        json.dump(regions, f, indent=1)
    dim = bytearray(len(rgba))
    for i in range(0, len(rgba), 4):
        for k in range(3):
            dim[i + k] = int(rgba[i + k] * 0.55 + 54)
        dim[i + 3] = 255
    for reg in regions:
        _draw_outline(dim, w, h, reg["x"], reg["y"], reg["w"], reg["h"])
    write_png(os.path.join(out_dir, f"ui-refboxes-{name}.png"), w, h,
              bytes(dim))
    note = ""
    if truncated:
        note = (" (truncated — candidates were dropped by --merge-cap/"
                "--max-boxes; results may be partial)")
    print(f"[ui_fidelity] refboxes: {len(regions)}/{total} regions{note} | "
          f"bg={bg} | sizes {w}x{h}")
    return 0


# ==========================================================================
# selftest
# ==========================================================================


def selftest():
    checks = 0
    fails = []

    def ok(cond, msg):
        nonlocal checks
        checks += 1
        if not cond:
            fails.append(msg)

    tmp = tempfile.mkdtemp(prefix="uif-selftest-")

    # 1. PNG codec roundtrip
    w, h = 20, 12
    px = bytes((i * 7) % 256 for i in range(w * h * 4))
    p1 = os.path.join(tmp, "a.png")
    write_png(p1, w, h, px)
    w2, h2, px2 = read_png(p1)
    ok((w2, h2) == (w, h) and px2 == px, "PNG codec roundtrip")

    # 2. identical images -> 0 diff
    d, _out, aa, pts = diff_images(px, px, w, h, 0.1, False, draw=False)
    ok(d == 0 and aa == 0 and not pts, "identical images -> 0 diff")

    # 3. known block change: 40x30 gray, black rect x10..15 y10..13 (6x4=24 px)
    bw, bh = 40, 30
    base = bytearray()
    for _i in range(bw * bh):
        base += bytes((200, 200, 200, 255))
    cand = bytearray(base)
    for y in range(10, 14):
        for x in range(10, 16):
            o = (y * bw + x) * 4
            cand[o:o + 4] = bytes((0, 0, 0, 255))
    base_b, cand_b = bytes(base), bytes(cand)
    d, _out, aa, pts = diff_images(base_b, cand_b, bw, bh, 0.1, False, draw=False)
    ok(d == 24 and aa == 0, f"block change -> exactly 24 diff px (got {d}, aa {aa})")
    cl, cl_total, _sk = cluster_pixels(pts)
    ok(cl_total == 1 and len(cl) == 1
       and cl[0] == {"x": 10, "y": 10, "w": 6, "h": 4, "pixels": 24},
       f"single cluster (10,10,6,4,24) (got {cl}, total {cl_total})")

    # 4. two separated blocks -> 2 clusters
    cand2 = bytearray(base)
    for y in range(2, 4):
        for x in range(2, 5):
            o = (y * bw + x) * 4
            cand2[o:o + 4] = bytes((0, 0, 0, 255))
    for y in range(20, 22):
        for x in range(30, 33):
            o = (y * bw + x) * 4
            cand2[o:o + 4] = bytes((0, 0, 0, 255))
    d2, _o, _a, pts2 = diff_images(base_b, bytes(cand2), bw, bh, 0.1, False, draw=False)
    cl2, tot2, _sk2 = cluster_pixels(pts2)
    ok(d2 == 12 and len(cl2) == 2 and tot2 == 2, "two blocks -> 2 clusters")

    # 5. threshold behavior: tiny 2/255 shift is below t=0.1, 40/255 above
    shift2 = bytearray(base)
    for i in range(bw * bh):
        shift2[i * 4] = shift2[i * 4 + 1] = shift2[i * 4 + 2] = 202
    d3, _o, _a, _p = diff_images(base_b, bytes(shift2), bw, bh, 0.1, False, draw=False)
    ok(d3 == 0, f"2/255 shift below threshold (got {d3})")
    shift40 = bytearray(base)
    for i in range(bw * bh):
        shift40[i * 4] = shift40[i * 4 + 1] = shift40[i * 4 + 2] = 240
    d4, _o, _a, _p = diff_images(base_b, bytes(shift40), bw, bh, 0.1, False, draw=False)
    ok(d4 == bw * bh, f"40/255 shift above threshold, all cells flagged (got {d4})")

    # 6. color_delta sanity: identical -> 0; black vs white -> ~32857
    cid = bytes((10, 20, 30, 255))
    ok(color_delta(cid, cid, 0, 0) == 0, "color_delta identical -> 0")
    black = bytes((0, 0, 0, 255))
    white = bytes((255, 255, 255, 255))
    cd = abs(color_delta(black, white, 0, 0))
    ok(abs(cd - 32857.13) < 0.5, f"color_delta black/white ~32857 (got {cd:.2f})")

    # 7. boxes: delta + overlap + containment + occlusion + missing/extra
    ref = [{"name": "nav", "x": 0, "y": 0, "w": 100, "h": 20},
           {"name": "cta", "x": 10, "y": 40, "w": 60, "h": 20},
           {"name": "panel", "x": 0, "y": 80, "w": 100, "h": 60}]
    cand = [{"name": "nav", "x": 1, "y": 0, "w": 100, "h": 20},
            {"name": "cta", "x": 13, "y": 40, "w": 60, "h": 24,
             "occluded_by": [".banner"]},
            {"name": "panel", "x": 0, "y": 80, "w": 100, "h": 60}]
    rep = boxes_report(ref, cand, 2)
    st = {e["name"]: e["status"] for e in rep["elements"]}
    ok(st["nav"] == "ok", f"boxes: within tolerance ok (got {st['nav']})")
    ok(st["cta"] == "moved+resized+occluded", f"boxes: flags combined (got {st['cta']})")
    ok(not rep["pass"], "boxes: failing set -> pass False")

    cand_clean = [dict(e) for e in ref]
    cand_clean[1] = {"name": "cta", "x": 10, "y": 40, "w": 60, "h": 20}
    ok(boxes_report(ref, cand_clean, 2)["pass"], "boxes: clean -> pass True")

    ref_c = [{"name": "card", "x": 0, "y": 0, "w": 100, "h": 50}]
    cand_c = [{"name": "card", "x": 0, "y": 0, "w": 100, "h": 50},
              {"name": "dot", "x": 40, "y": 20, "w": 6, "h": 6}]
    rep_c = boxes_report(ref_c, cand_c, 2)
    ok(not rep_c["overlaps"] and "extra_in_cand" == rep_c["elements"][1]["status"],
       "boxes: containment not an overlap; extra element flagged")

    o1 = [{"name": "a", "x": 0, "y": 0, "w": 50, "h": 50},
          {"name": "b", "x": 40, "y": 40, "w": 50, "h": 50}]
    rep_o = boxes_report(o1, o1, 2)
    ok(len(rep_o["overlaps"]) == 1 and rep_o["overlaps"][0]["area"] == 100,
       f"boxes: sibling intersection -> overlap area 100 (got {rep_o['overlaps']})")
    ok(boxes_report(o1, o1, 2, allow_overlap=("a:b",))["pass"],
       "boxes: allow_overlap suppresses the pair")

    # 8. crop helper
    cw, ch = 20, 10
    crop = crop_rgba(bytes(base), bw, bh, cw, ch)
    ok(len(crop) == cw * ch * 4 and crop[:4] == bytes((200, 200, 200, 255)),
       "crop helper")

    # 9. CLI contract: dimension refusal (3) + allow-dim compares crop (1)
    p_full = os.path.join(tmp, "full.png")
    p_half = os.path.join(tmp, "half.png")
    write_png(p_full, bw, bh, base_b)
    write_png(p_half, bw, bh // 2, base_b[: bw * (bh // 2) * 4])
    rc = run_diff(p_full, p_half, tmp, "dim", 0.1, 1.0, False, False)
    ok(rc == 3, f"dimension mismatch refused -> exit 3 (got {rc})")
    rc2 = run_diff(p_full, p_half, tmp, "dim2", 0.1, 1.0, False, True)
    ok(rc2 == 1, f"allow-dim compares crop yet still fails -> exit 1 (got {rc2})")

    # 10. refboxes: two exact regions found, speck filtered, auto bg
    rw, rh = 64, 40
    img = bytearray()
    for y in range(rh):
        for x in range(rw):
            c = (240, 240, 240)
            if 8 <= x < 28 and 6 <= y < 18:
                c = (200, 60, 60)
            if 40 <= x < 56 and 20 <= y < 30:
                c = (60, 60, 200)
            if 60 <= x < 62 and 2 <= y < 4:
                c = (10, 10, 10)          # speck: 4 px < min_area
            img += bytes(c) + b"\xff"
    regions, rbg, rtrunc, rtotal = refboxes_report(rw, rh, bytes(img), tol=24,
                                                   min_area=64, gap=6)
    ok(rbg == (240, 240, 240), f"refboxes auto-bg (got {rbg})")
    ok(not rtrunc and rtotal == 2, f"refboxes not truncated (got {rtotal})")
    ok(len(regions) == 2, f"refboxes finds 2 regions (got {len(regions)})")
    if len(regions) == 2:
        ok((regions[0]["x"], regions[0]["y"], regions[0]["w"],
            regions[0]["h"]) == (8, 6, 20, 12),
           f"refboxes region A exact (got {regions[0]})")
        ok((regions[1]["x"], regions[1]["y"], regions[1]["w"],
            regions[1]["h"]) == (40, 20, 16, 10),
           f"refboxes region B exact (got {regions[1]})")

    # 10b. refboxes alpha: transparent margins composite over white; the
    # solid card stays the only region
    aw, ah = 40, 30
    aimg = bytearray()
    for y in range(ah):
        for x in range(aw):
            if 8 <= x < 28 and 6 <= y < 18:
                aimg += bytes((200, 60, 60, 255))
            else:
                aimg += b"\x00\x00\x00\x00"
    areg, abg, _at, _an = refboxes_report(aw, ah, bytes(aimg), tol=24,
                                          min_area=64, gap=6)
    ok(abg == (255, 255, 255), f"refboxes alpha bg -> white (got {abg})")
    ok(len(areg) == 1 and (areg[0]["x"], areg[0]["y"], areg[0]["w"],
                           areg[0]["h"]) == (8, 6, 20, 12),
       f"refboxes alpha card region (got {areg})")

    if fails:
        for m in fails:
            print("SELFTEST FAIL: " + m)
        print(f"selftest: {checks - len(fails)}/{checks} checks passed")
        return 1
    print(f"selftest PASS: {checks} checks")
    return 0


# ==========================================================================
# CLI
# ==========================================================================


def main():
    ap = argparse.ArgumentParser(
        description="Design-copy fidelity measurement (pixel diff + DOM box deltas)")
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    d = sub.add_parser("diff", help="pixel-diff two PNGs")
    d.add_argument("ref")
    d.add_argument("cand")
    d.add_argument("--out", default="tests")
    d.add_argument("--name", default="")
    d.add_argument("--threshold", type=float, default=0.1,
                   help="per-pixel YIQ tolerance 0-1 (pixelmatch default 0.1)")
    d.add_argument("--max-diff-percent", type=float, default=1.0)
    d.add_argument("--no-aa", action="store_true",
                   help="count anti-aliased pixels as differences too")
    d.add_argument("--allow-dim-mismatch", action="store_true",
                   help="compare the common crop instead of refusing (still reported)")

    b = sub.add_parser("boxes", help="compare DOM box dumps")
    b.add_argument("ref")
    b.add_argument("cand")
    b.add_argument("--out", default="tests")
    b.add_argument("--name", default="")
    b.add_argument("--tol-px", type=float, default=2.0)
    b.add_argument("--allow-overlap", default="",
                   help="comma list a:b of expected overlaps")
    b.add_argument("--allow-occluded", default="",
                   help="comma list of element names allowed to be occluded")

    r = sub.add_parser("refboxes",
                       help="extract candidate regions from a reference image")
    r.add_argument("ref")
    r.add_argument("--out", default="tests")
    r.add_argument("--name", default="")
    r.add_argument("--bg", default="",
                   help="background color RRGGBB (default: auto from the image)")
    r.add_argument("--tol", type=float, default=24.0)
    r.add_argument("--min-area", type=int, default=64)
    r.add_argument("--gap", type=int, default=6)
    r.add_argument("--max-boxes", type=int, default=200)
    r.add_argument("--merge-cap", type=int, default=2048,
                   help="skip cluster gap-merge above this many components "
                        "(perf bound; check the truncated note)")

    args = ap.parse_args()
    try:
        if args.selftest:
            return selftest()
        if args.cmd == "diff":
            if not 0.0 <= args.threshold <= 1.0 or args.max_diff_percent < 0:
                print("[ui_fidelity] error: --threshold must be within 0..1 "
                      "and --max-diff-percent >= 0", file=sys.stderr)
                return 2
            name = args.name or os.path.splitext(os.path.basename(args.cand))[0]
            return run_diff(args.ref, args.cand, args.out, name,
                            args.threshold, args.max_diff_percent,
                            args.no_aa, args.allow_dim_mismatch)
        if args.cmd == "boxes":
            name = args.name or os.path.splitext(os.path.basename(args.cand))[0]
            return run_boxes(args.ref, args.cand, args.out, name, args.tol_px,
                             tuple(p for p in args.allow_overlap.split(",") if p),
                             tuple(p for p in args.allow_occluded.split(",") if p))
        if args.cmd == "refboxes":
            if (args.tol < 0 or args.min_area < 1 or args.gap < 0
                    or args.max_boxes < 1 or args.merge_cap < 0):
                print("[ui_fidelity] error: --tol/--gap/--merge-cap >= 0, "
                      "--min-area >= 1, --max-boxes >= 1", file=sys.stderr)
                return 2
            name = args.name or os.path.splitext(os.path.basename(args.ref))[0]
            return run_refboxes(args.ref, args.out, name, args.bg,
                                args.tol, args.min_area, args.gap,
                                args.max_boxes, args.merge_cap)
        ap.print_help()
        return 2
    except (ValueError, OSError, KeyError, zlib.error, IndexError,
            struct.error) as e:
        print(f"[ui_fidelity] error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
