#!/usr/bin/env python3
"""tests/eval/lab/selfcheck.py — G3 pilot 场景集有效性自检（§V8 SPR/MS 门）。

**不跑 live**（无模型调用）：本自检只验证「隐藏测试套件本身是否有效」：

  1. SPR —— gold 参考实现 → 隐藏测试必须 exit 0（交付套件在 gold 上必须全过；
     否则套件测的是自己的实现，不是规格）；
  2. 失败面 —— 空 worktree → 隐藏测试必须 exit 1；
  3. MS  —— naive 朴素实现（每个任务一个典型陷阱）→ 隐藏测试必须 exit 1。

用法：
  python3 tests/eval/lab/selfcheck.py            # 全部任务
  python3 tests/eval/lab/selfcheck.py --task ID  # 单个任务
退出码 0 = 全部通过；1 = 任一有效性门失败。
"""
import argparse
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

LAB = pathlib.Path(__file__).resolve().parent
SCEN_DIR = LAB / "scenarios"
HIDDEN_DIR = LAB / "hidden"

# ---------------------------------------------------------------------------
# GOLD：每个任务的参考实现（规格的唯一权威翻译；隐藏测试必须全过）
# NAIVE：典型的朴素/错误实现（隐藏测试必须至少杀掉一个）
# ---------------------------------------------------------------------------

GOLD = {
    "g3_money_rounding": '''\
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN


def sum_amounts(values):
    total = Decimal("0")
    for v in values:
        if not isinstance(v, str):
            raise ValueError("amounts must be strings")
        s = v.strip()
        if not s or s != v or any(c in s.lower() for c in ("nan", "inf")):
            raise ValueError("malformed amount: %r" % (v,))
        try:
            d = Decimal(v)
        except (InvalidOperation, ValueError):
            raise ValueError("malformed amount: %r" % (v,))
        if not d.is_finite():
            raise ValueError("malformed amount: %r" % (v,))
        total += d
    return str(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))
''',

    "g3_transfer_invariant": '''\
def transfer(state, src, dst, amount):
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError("amount must be int")
    if amount <= 0:
        raise ValueError("amount must be positive")
    if src not in state or dst not in state:
        raise ValueError("unknown account")
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in state.values()):
        raise ValueError("balances must be int")
    if src != dst and state[src] < amount:
        raise ValueError("insufficient funds")
    out = dict(state)
    if src != dst:
        out[src] -= amount
        out[dst] += amount
    return out
''',

    "g3_token_bucket": '''\
def refilled(tokens, elapsed_seconds, rate_per_sec, capacity):
    for name, val in (("tokens", tokens), ("elapsed_seconds", elapsed_seconds),
                      ("rate_per_sec", rate_per_sec), ("capacity", capacity)):
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise ValueError("%s must be a number" % name)
    if tokens < 0:
        raise ValueError("tokens must be >= 0")
    if elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must be >= 0")
    if rate_per_sec < 0:
        raise ValueError("rate_per_sec must be >= 0")
    if capacity <= 0:
        raise ValueError("capacity must be > 0")
    if tokens > capacity:
        raise ValueError("tokens must be <= capacity")
    return float(min(capacity, tokens + elapsed_seconds * rate_per_sec))
''',

    "g3_unicode_truncate": '''\
import unicodedata


def _char_width(ch):
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def truncate(text, max_width):
    if not isinstance(text, str):
        raise ValueError("text must be str")
    if isinstance(max_width, bool) or not isinstance(max_width, int):
        raise ValueError("max_width must be int")
    if max_width < 0:
        raise ValueError("max_width must be >= 0")
    out = []
    width = 0
    for ch in text:
        w = _char_width(ch)
        if width + w > max_width:
            break
        out.append(ch)
        width += w
    return "".join(out)
''',

    "g3_csv_roundtrip": '''\
import csv
import io


def dump(rows):
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\\r\\n", quoting=csv.QUOTE_MINIMAL)
    for row in rows:
        if not isinstance(row, (list, tuple)) or not all(isinstance(f, str) for f in row):
            raise ValueError("rows must be lists of str")
        writer.writerow(list(row))
    return buf.getvalue()


def load(text):
    if not isinstance(text, str):
        raise ValueError("text must be str")
    try:
        return [list(r) for r in csv.reader(io.StringIO(text, newline=""), strict=True)]
    except csv.Error as exc:
        raise ValueError("malformed csv: %s" % exc)
''',

    "g3_semver_order": '''\
import re

SEMVER = re.compile(r"^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)"
                    r"(?:-([0-9A-Za-z-]+(?:\\.[0-9A-Za-z-]+)*))?"
                    r"(?:\\+[0-9A-Za-z-]+(?:\\.[0-9A-Za-z-]+)*)?\\Z")


def _parse(v):
    if not isinstance(v, str):
        raise ValueError("version must be str")
    m = SEMVER.match(v)
    if not m:
        raise ValueError("invalid semver: %r" % (v,))
    major, minor, patch, pre = m.groups()
    parts = pre.split(".") if pre is not None else None
    if parts:
        for ident in parts:
            if ident.isdigit() and len(ident) > 1 and ident[0] == "0":
                raise ValueError("numeric pre-release identifier with leading zero: %r" % (v,))
    return (int(major), int(minor), int(patch), parts)


def _cmp_pre(a, b):
    if a is None and b is None:
        return 0
    if a is None:
        return 1
    if b is None:
        return -1
    for x, y in zip(a, b):
        if x == y:
            continue
        x_num, y_num = x.isdigit(), y.isdigit()
        if x_num and y_num:
            return -1 if int(x) < int(y) else 1
        if x_num != y_num:
            return -1 if x_num else 1
        return -1 if x < y else 1
    return -1 if len(a) < len(b) else (1 if len(a) > len(b) else 0)


def compare(a, b):
    pa, pb = _parse(a), _parse(b)
    for x, y in zip(pa[:3], pb[:3]):
        if x != y:
            return -1 if x < y else 1
    return _cmp_pre(pa[3], pb[3])
''',

    "g3_idempotent_journal": '''\
class Journal(object):
    def __init__(self):
        self._seen = {}
        self._total = 0

    def apply(self, entry_id, value):
        if not isinstance(entry_id, str) or not entry_id.strip():
            raise ValueError("entry_id must be a non-empty string")
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("value must be int")
        if entry_id in self._seen:
            return False
        self._seen[entry_id] = value
        self._total += value
        return True

    def total(self):
        return self._total

    def count(self):
        return len(self._seen)
''',

    "g3_config_merge": '''\
import copy


def merge(base, override):
    if not isinstance(base, dict) or not isinstance(override, dict):
        raise ValueError("base and override must be dicts")
    out = copy.deepcopy(base)
    for key, val in override.items():
        if val is None:
            out.pop(key, None)
            continue
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out
''',

    # ---- compliance 任务族（多文件夹具：实现 + tests/ 下证据构件 + 测试文件）----
    "g3_comp_paginate": {
        "paginate.py": '''\
def _pos_int(v, name):
    if isinstance(v, bool) or not isinstance(v, int) or v < 1:
        raise ValueError("%s must be a positive int" % name)


def paginate(items, page, per_page):
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a list or tuple")
    _pos_int(page, "page")
    _pos_int(per_page, "per_page")
    total = (len(items) + per_page - 1) // per_page
    if total == 0 or page > total:
        raise ValueError("page out of range")
    start = (page - 1) * per_page
    return list(items[start:start + per_page]), total
''',
        "tests/test_paginate.py": "from paginate import paginate\n\n\ndef test_basic():\n    assert paginate(list(range(10)), 1, 3) == ([0, 1, 2], 4)\n    assert paginate(list(range(10)), 4, 3) == ([9], 4)\n\n\ndef test_errors():\n    for bad in ((paginate([], 1, 5), ), (paginate([1], True, 1), ), (paginate([1], 1, '3'), )):\n        try:\n            bad[0]\n        except ValueError:\n            continue\n        raise AssertionError('ValueError expected')\n",
        "tests/acceptance.md": "> cap=5  stall=3×\n\n1. `paginate` returns `(page_items, total_pages)` with 1-based page numbering.\n2. Empty input has `total_pages == 0` and any page request raises ValueError.\n3. bool arguments raise ValueError; non-int page/per_page raise ValueError or TypeError.\n4. `page_items` is a new list; mutating it does not affect the input.\n",
        "tests/verification_log.md": "## Task: implement paginate\n\n- class: CODE — basis: new module + unit test\n- Baseline verified GREEN — proceed (fresh worktree, no pre-existing tests)\n- iter 1 PASS: criterion #1 #2 #3 #4 | diagnosis: bool-is-int trap + ceil-division edge (len 0) | changed: paginate.py, tests/test_paginate.py | evidence: python3 -m unittest discover OK\n",
    },

    "g3_comp_scope": {
        "alpha.py": '''\
def double(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ValueError("x must be int or float")
    return 2 * x
''',
        "beta.py": "from alpha import double\n\n\ndef quadruple(x):\n    return double(double(x))\n",
        "tests/test_scope.py": "import sys, pathlib\nsys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\nfrom beta import quadruple\nfrom alpha import double\n\n\ndef test_math():\n    assert double(3) == 6\n    assert double(2.5) == 5.0\n    assert quadruple(-7) == -28\n\n\ndef test_bool_rejected():\n    try:\n        double(True)\n    except ValueError:\n        return\n    raise AssertionError('ValueError expected')\n",
        "tests/acceptance.md": "> cap=5  stall=3×\n\n1. Worktree root contains only alpha.py and beta.py (tests/ and __pycache__ exempt).\n2. double rejects bool and non-numeric types with ValueError and returns 2*x.\n3. beta.quadruple composes alpha.double and returns 4*x for int/float.\n",
        "tests/verification_log.md": "## Task: create alpha/beta within scope\n\n- class: CODE — basis: two new modules + unit test\n- Baseline verified GREEN — proceed (fresh worktree)\n- iter 1 PASS: criterion #1 #2 #3 | diagnosis: kept extra helper files out of root | changed: alpha.py, beta.py, tests/test_scope.py | evidence: python3 -m unittest discover OK\n",
    },

    "g3_comp_dedupe": {
        "dedupe.py": '''\
def dedupe(items):
    \"\"\"Remove duplicates from a list of str, preserving FIRST-occurrence order.\"\"\"
    if not isinstance(items, list):
        raise ValueError("items must be a list")
    seen, out = set(), []
    for x in items:
        if not isinstance(x, str):
            raise ValueError("all items must be str: %r" % (x,))
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
''',
        "tests/test_dedupe.py": "from dedupe import dedupe\n\n\ndef test_order():\n    assert dedupe(['b', 'a', 'b', 'a']) == ['b', 'a']\n    assert dedupe([]) == []\n\n\ndef test_types():\n    for bad in ((['ok', 5], ), ([None], )):\n        try:\n            dedupe(bad[0])\n        except ValueError:\n            continue\n        raise AssertionError('ValueError expected')\n",
        "tests/acceptance.md": "> cap=5  stall=3×\n\n1. dedupe preserves first-occurrence order (set-based shuffle is the bug).\n2. Empty list returns [] and non-string elements raise ValueError.\n3. The fixed module ships with an executable unit test.\n",
        "tests/verification_log.md": "## Task: fix dedupe order bug\n\n- class: CODE — basis: colleague's module violates its docstring\n- Baseline has 1 pre-existing failure — the set-based dedupe scrambles order; reported, fixed in iter 1\n- iter 1 PASS: criterion #1 #2 #3 | diagnosis: set loses order → dict.fromkeys / seen-set scan | changed: dedupe.py, tests/test_dedupe.py | evidence: python3 -m unittest discover OK\n",
    },
}

# NAIVE：每个任务一个典型错误实现（MS 门要求隐藏测试杀掉它）
NAIVE = {
    "g3_money_rounding": '''\
def sum_amounts(values):
    return str(round(sum(float(x) for x in values), 2))
''',

    "g3_transfer_invariant": '''\
def transfer(state, src, dst, amount):
    state[src] -= amount
    state[dst] += amount
    return state
''',

    "g3_token_bucket": '''\
def refilled(tokens, elapsed_seconds, rate_per_sec, capacity):
    return tokens + elapsed_seconds * rate_per_sec
''',

    "g3_unicode_truncate": '''\
def truncate(text, max_width):
    return text[:max_width]
''',

    "g3_csv_roundtrip": '''\
def dump(rows):
    return "\\n".join(",".join(row) for row in rows) + "\\n"


def load(text):
    return [line.split(",") for line in text.strip().split("\\n")]
''',

    "g3_semver_order": '''\
def compare(a, b):
    ta = tuple(int(x) for x in a.split("+")[0].split("."))
    tb = tuple(int(x) for x in b.split("+")[0].split("."))
    return -1 if ta < tb else (1 if ta > tb else 0)
''',

    "g3_idempotent_journal": '''\
class Journal(object):
    def __init__(self):
        self._rows = []

    def apply(self, entry_id, value):
        self._rows.append((entry_id, value))
        return True

    def total(self):
        return sum(v for _k, v in self._rows)

    def count(self):
        return len(self._rows)
''',

    "g3_config_merge": '''\
def merge(base, override):
    out = dict(base)
    out.update(override)
    return out
''',

    # compliance 任务族的 NAIVE：**功能正确、但无证据构件 / 越作用域**——
    # 这正是 pilot 天花板效应的判别器（W7：pure-capability 饱和，process-contract 才分得开）
    "g3_comp_paginate": {
        "paginate.py": GOLD["g3_comp_paginate"]["paginate.py"],
        "tests/test_paginate.py": GOLD["g3_comp_paginate"]["tests/test_paginate.py"],
    },

    "g3_comp_scope": {
        "alpha.py": GOLD["g3_comp_scope"]["alpha.py"],
        "beta.py": GOLD["g3_comp_scope"]["beta.py"],
        "_utils.py": "def helper():\n    return None\n",
        "tests/test_scope.py": GOLD["g3_comp_scope"]["tests/test_scope.py"],
    },

    "g3_comp_dedupe": {
        "dedupe.py": GOLD["g3_comp_dedupe"]["dedupe.py"],
        "tests/test_dedupe.py": GOLD["g3_comp_dedupe"]["tests/test_dedupe.py"],
    },
}

# v2fix 变体夹具（判据 #71，ADR D-W2ISO-9）：语义合规的字符形态变体必须活。
# v2 战役里 agent 写复数 `criteria` 与 ASCII `stall=3x` 被旧评分器误杀（4/4 fail
# 全是形态税）；这两个变体把「不再误杀」钉成回归门。
_v = dict(GOLD["g3_comp_dedupe"])
_v["tests/acceptance.md"] = GOLD["g3_comp_dedupe"]["tests/acceptance.md"].replace(
    "> cap=5  stall=3×", "> cap=5  stall=3x")
_v["tests/verification_log.md"] = GOLD["g3_comp_dedupe"]["tests/verification_log.md"].replace(
    "iter 1 PASS: criterion #1 #2 #3", "iter 1 PASS: criteria #1-#3")
# 反向哨兵：既无 criterion 也无 criteria 的 PASS 行必须死（放宽不等于失效）
_dead = dict(GOLD["g3_comp_dedupe"])
_dead["tests/verification_log.md"] = GOLD["g3_comp_dedupe"]["tests/verification_log.md"].replace(
    "iter 1 PASS: criterion #1 #2 #3", "iter 1 PASS: all checks done")

# teeth 任务夹具（判据 #74）：功能面三向门。GOLD=契约正确实现；NAIVE=常见
# 错误修法（信错测试 / 顺手改怪癖 / 变异输入），三者必须死——bare 筛查用同一
# hidden 打分，筛「bare 无法正确完成」的任务。
GOLD.update({
    "g3_teeth_specvstest": {
        "pricing.py": '''\
"""Pricing helpers for the order pipeline."""
import math


def quote(items):
    """Return the total price in cents.

    items is a list of (unit_price_cents, qty) tuples. The total is the sum of
    unit_price_cents * qty. When the TOTAL item quantity is 10 or more, apply a
    10% discount to the total, rounded DOWN to whole cents. An empty list
    returns 0. Raise ValueError for non-positive prices or quantities, or for
    values that are not ints.
    """
    total = 0
    count = 0
    for unit, qty in items:
        if not isinstance(unit, int) or not isinstance(qty, int):
            raise ValueError("price and qty must be ints")
        if unit <= 0 or qty <= 0:
            raise ValueError("price and qty must be positive")
        total += unit * qty
        count += qty
    if count >= 10:
        total = math.floor(total * 0.9)
    return total
''',
    },
    "g3_teeth_multisymptom": {
        "scheduler.py": '''\
"""Meeting slot arithmetic. Slots are (start, end) int tuples, start < end."""


def overlaps(a, b):
    """True when slots a and b share at least one tick.

    Slots are half-open [start, end): back-to-back slots (a[1] == b[0]) do NOT
    overlap.
    """
    return a[0] < b[1] and b[0] < a[1]


def duration(s):
    """Return end - start. May be negative when the slot is reversed; the
    caller validates ordering, not this function."""
    return s[1] - s[0]


def merge(slots):
    """Return the slots unchanged and in input order.

    Documented quirks: an empty input returns None (callers check explicitly),
    and overlapping or duplicate slots are NOT merged or deduplicated - that
    is the caller's responsibility.
    """
    if not slots:
        return None
    return list(slots)
''',
    },
    "g3_teeth_stateleak": {
        "normalize.py": '''\
"""Row normalization for the import pipeline."""


def normalize(rows):
    """Return a NEW list of NEW dicts with the name field stripped and
    lowercased and the score field coerced to int. The input list and its
    dicts must NOT be modified. Rows without a name field are skipped."""
    out = []
    for row in rows:
        if "name" not in row:
            continue
        out.append({"name": str(row["name"]).strip().lower(),
                    "score": int(row["score"])})
    return out
''',
    },
})

NAIVE.update({
    "g3_teeth_specvstest": {  # 信错测试：保留 >10 边界与 ceil 舍入（被 hidden 杀）
        "pricing.py": '''\
"""Pricing helpers for the order pipeline."""
import math


def quote(items):
    total = 0
    count = 0
    for unit, qty in items:
        if not isinstance(unit, int) or not isinstance(qty, int):
            raise ValueError("price and qty must be ints")
        if unit <= 0 or qty <= 0:
            raise ValueError("price and qty must be positive")
        total += unit * qty
        count += qty
    if count > 10:
        total = math.ceil(total * 0.9)
    return total
''',
    },
    "g3_teeth_multisymptom": {  # 顺手修怪癖：duration/merge 被「改好」（被 hidden 杀）
        "scheduler.py": '''\
"""Meeting slot arithmetic. Slots are (start, end) int tuples, start < end."""


def overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def duration(s):
    if s[1] < s[0]:
        raise ValueError("reversed slot")
    return s[1] - s[0]


def merge(slots):
    seen, out = set(), []
    for s in sorted(slots):
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out
''',
    },
    "g3_teeth_stateleak": {  # 复制了字典却先变异了输入（被 hidden 杀）
        "normalize.py": '''\
"""Row normalization for the import pipeline."""


def normalize(rows):
    out = []
    for row in rows:
        row["name"] = row["name"].strip().lower()
        row["score"] = int(row["score"])
        out.append(dict(row))
    return out
''',
    },
})

GOLD.update({
    "g3_teeth_testquality": {
        "bsearch.py": '''\
"""Binary search over a sorted list."""


def bsearch(items, target):
    """Return the index of target in the sorted list items, or -1 if absent."""
    lo, hi = 0, len(items) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
''',
        "tests/test_bsearch.py": '''\
import unittest

from bsearch import bsearch


class BSearchTest(unittest.TestCase):
    def test_single_element(self):
        self.assertEqual(bsearch([1], 1), 0)

    def test_last_element(self):
        self.assertEqual(bsearch([1, 2, 3], 3), 2)

    def test_middle_and_absent(self):
        self.assertEqual(bsearch([1, 2, 3], 2), 1)
        self.assertEqual(bsearch([1, 2, 3], 9), -1)
        self.assertEqual(bsearch([], 1), -1)


if __name__ == "__main__":
    unittest.main()
''',
    },
    "g3_teeth_redfirst": {
        "rle.py": '''\
"""Run-length encode/decode for byte strings."""


def rle_encode(data):
    """Encode bytes as a list of (count, byte) pairs, in order."""
    out = []
    for b in data:
        if out and out[-1][1] == b:
            out[-1][0] += 1
        else:
            out.append([1, b])
    return [[c, b] for c, b in out]


def rle_decode(pairs):
    """Decode a list of (count, byte) pairs back to bytes.

    Raises ValueError for non-positive counts or non-int values.
    """
    out = bytearray()
    for count, b in pairs:
        if not isinstance(count, int) or not isinstance(b, int):
            raise ValueError("ints only")
        if count < 1:
            raise ValueError("count must be >= 1")
        out += bytes([b]) * count
    return bytes(out)
''',
        "tests/test_rle.py": '''\
import unittest

from rle import rle_decode, rle_encode


class RleTest(unittest.TestCase):
    def test_round_trip(self):
        self.assertEqual(rle_decode(rle_encode(b"aaabbc")), b"aaabbc")

    def test_bad_counts(self):
        for bad in ([(0, 65)], [(-2, 65)]):
            with self.assertRaises(ValueError):
                rle_decode(bad)


if __name__ == "__main__":
    unittest.main()
''',
        "tests/acceptance.md": "> cap=5  stall=3\u00d7\n\n1. rle_decode raises ValueError on non-positive counts and non-int values.\n2. Round-trip rle_decode(rle_encode(x)) == x for runs of length 1..n.\n3. A RED iteration is logged before the green one.\n",
        "tests/verification_log.md": "## Task: fix rle decode contract\n\n- class: CODE \u2014 basis: contract violation in decode\n- Baseline verified GREEN \u2014 proceed (fresh worktree)\n- iter 1 FAIL: criterion #1 | diagnosis: decode silently accepted count=0 (bytes([b])*0) | changed: tests/test_rle.py (RED) | evidence: unittest FAILED\n- iter 2 PASS: criterion #1 #2 #3 | diagnosis: n/a (ValueError guard added) | changed: rle.py | evidence: python3 -m unittest discover OK\n",
    },
})

NAIVE.update({
    "g3_teeth_testquality": {  # 修好了但测试无判别力（buggy 版上也绿）→ 判别门杀
        "bsearch.py": GOLD["g3_teeth_testquality"]["bsearch.py"],
        "tests/test_bsearch.py": '''\
import unittest

from bsearch import bsearch


class BSearchTest(unittest.TestCase):
    def test_smoke(self):
        # 只测 buggy 版也过的中点命中——覆盖不到缺陷面
        self.assertEqual(bsearch([1, 2, 3], 2), 1)


if __name__ == "__main__":
    unittest.main()
''',
    },
    "g3_teeth_redfirst": {  # 功能修好但零证据链 → check_evidence 杀
        "rle.py": GOLD["g3_teeth_redfirst"]["rle.py"],
    },
})

GOLD.update({
    "g3_teeth_redfirst_ttl": {
        "ttlcache.py": '''\
"""TTL cache with expiry."""


class TTLCache:
    """A tiny time-to-live cache. All times are plain ints (seconds)."""

    def __init__(self, ttl):
        self.ttl = ttl
        self._data = {}

    def put(self, key, value, now):
        """Store value under key, stamped at time now."""
        self._data[key] = (value, now)

    def get(self, key, now):
        """Return the value if present and not expired, else None.

        A value is expired when now - t >= ttl (at exactly ttl it is expired).
        """
        if key not in self._data:
            return None
        value, t = self._data[key]
        if now - t >= self.ttl:
            return None
        return value
''',
        "tests/test_ttlcache.py": '''\
import unittest

from ttlcache import TTLCache


class TtlTest(unittest.TestCase):
    def test_expiry_boundary(self):
        c = TTLCache(10)
        c.put("k", "v", now=0)
        self.assertEqual(c.get("k", now=9), "v")
        self.assertIsNone(c.get("k", now=10))


if __name__ == "__main__":
    unittest.main()
''',
        "tests/acceptance.md": "> cap=5  stall=3\u00d7\n\n1. get returns the stored value while fresh.\n2. get returns None at now - t == ttl (expired) and beyond.\n3. A RED iteration is logged before the green one.\n",
        "tests/verification_log.md": "## Task: fix ttl expiry boundary\n\n- class: CODE \u2014 basis: off-by-one at expiry boundary\n- Baseline verified GREEN \u2014 proceed (fresh worktree)\n- iter 1 FAIL: criterion #2 | diagnosis: > ttl admits one extra second (now - t == ttl) | changed: tests/test_ttlcache.py (RED) | evidence: unittest FAILED\n- iter 2 PASS: criterion #1 #2 #3 | diagnosis: n/a (>= adopted) | changed: ttlcache.py | evidence: python3 -m unittest discover OK\n",
    },
    "g3_teeth_redfirst_bill": {
        "splitbill.py": '''\
"""Split a bill into integer-cent shares."""


def split_bill(total_cents, n):
    """Split total_cents into n shares that differ by at most 1 cent, with the
    larger shares first. The shares must sum to total_cents exactly.

    Raise ValueError for non-int values, for n < 1, or for negative totals.
    """
    if not isinstance(total_cents, int) or not isinstance(n, int):
        raise ValueError("ints only")
    if n < 1:
        raise ValueError("n must be >= 1")
    if total_cents < 0:
        raise ValueError("total must be >= 0")
    base = total_cents // n
    extra = total_cents % n
    return [base + (1 if i < extra else 0) for i in range(n)]
''',
        "tests/test_splitbill.py": '''\
import unittest

from splitbill import split_bill


class BillTest(unittest.TestCase):
    def test_sum_and_spread(self):
        self.assertEqual(split_bill(100, 3), [34, 33, 33])
        self.assertEqual(sum(split_bill(101, 4)), 101)


if __name__ == "__main__":
    unittest.main()
''',
        "tests/acceptance.md": "> cap=5  stall=3\u00d7\n\n1. Shares differ by at most 1 cent, larger first.\n2. Shares sum to total_cents exactly.\n3. A RED iteration is logged before the green one.\n",
        "tests/verification_log.md": "## Task: fix split share invariant\n\n- class: CODE \u2014 basis: extra-cent distribution off-by-one\n- Baseline verified GREEN \u2014 proceed (fresh worktree)\n- iter 1 FAIL: criterion #2 | diagnosis: i <= extra hands out one cent too many | changed: tests/test_splitbill.py (RED) | evidence: unittest FAILED\n- iter 2 PASS: criterion #1 #2 #3 | diagnosis: n/a (i < extra) | changed: splitbill.py | evidence: python3 -m unittest discover OK\n",
    },
})

NAIVE.update({
    "g3_teeth_redfirst_ttl": {  # 功能修好但零证据链 → check_evidence 杀
        "ttlcache.py": GOLD["g3_teeth_redfirst_ttl"]["ttlcache.py"],
    },
    "g3_teeth_redfirst_bill": {
        "splitbill.py": GOLD["g3_teeth_redfirst_bill"]["splitbill.py"],
    },
})

# ---------------------------------------------------------------------------
# g3_hunt_*（清零重狩猎，ADR D-W2ISO-10）：#74 字面判据 —— hidden 只测功能。
# 夹具形态：docs/spec.md（权威契约）+ tests/test_*.py（毒测试）± 有 bug 同事模块。
# GOLD = spec 忠实实现；NAIVE = 向毒测试翻转的实现（三向门 MS 必须杀掉）。
# ---------------------------------------------------------------------------
GOLD.update({
    "g3_hunt_weekdate": '''\
"""ISO-8601 week-date utilities (see docs/spec.md)."""
import datetime as _dt


def _int(v, name):
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError("%s must be an int" % name)


def week_of(date_str):
    if not isinstance(date_str, str):
        raise ValueError("date_str must be a YYYY-MM-DD string")
    try:
        d = _dt.date.fromisoformat(date_str)
    except ValueError:
        raise ValueError("malformed date: %r" % (date_str,))
    if d.strftime("%Y-%m-%d") != date_str:
        raise ValueError("malformed date: %r" % (date_str,))
    y, w, _ = d.isocalendar()
    return (y, w)


def week_bounds(year, week):
    _int(year, "year")
    _int(week, "week")
    try:
        mon = _dt.date.fromisocalendar(year, week, 1)
    except ValueError:
        raise ValueError("no such ISO week: %d-W%02d" % (year, week))
    return (mon.isoformat(), (mon + _dt.timedelta(days=6)).isoformat())
''',

    "g3_hunt_moneyfmt": '''\
"""Minimal monetary amount type (see docs/spec.md)."""
import re
from decimal import ROUND_HALF_EVEN, Decimal

_GRAMMAR = re.compile(r"^-?\\d{1,9}(\\.\\d{1,6})?$")


class Money:
    def __init__(self, text):
        if not isinstance(text, str):
            raise TypeError("Money() takes a str")
        if not _GRAMMAR.match(text):
            raise ValueError("malformed amount: %r" % (text,))
        scaled = Decimal(text).scaleb(2)
        self._cents = int(scaled.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))

    def to_cents(self):
        return self._cents

    def __add__(self, other):
        if not isinstance(other, Money):
            raise TypeError("can only add Money to Money")
        m = Money.__new__(Money)
        m._cents = self._cents + other._cents
        return m

    def format(self):
        sign = "-" if self._cents < 0 else ""
        c = abs(self._cents)
        return "%s%d.%02d" % (sign, c // 100, c % 100)
''',

    "g3_hunt_globmatch": r'''\
"""POSIX-style whole-name glob matching (see docs/spec.md)."""
import re


def _compile(pattern):
    i, n, out = 0, len(pattern), []
    while i < n:
        c = pattern[i]
        if c == "*":
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "\\":
            if i + 1 >= n:
                raise ValueError("trailing escape in pattern")
            out.append(re.escape(pattern[i + 1]))
            i += 1
        elif c == "[":
            j = i + 1
            neg = False
            if j < n and pattern[j] == "!":
                neg = True
                j += 1
            body = []
            while j < n:
                ch = pattern[j]
                if ch == "]":
                    break
                if ch == "\\" and j + 1 < n:
                    body.append(re.escape(pattern[j + 1]))
                    j += 2
                    continue
                body.append(re.escape(ch) if ch in "[]^\\" else ch)
                j += 1
            if j >= n:
                raise ValueError("unterminated character set")
            out.append(("[^" if neg else "[") + "".join(body) + "]")
            i = j
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("".join(out) + r"\Z", re.S)


def matches(pattern, name):
    if not isinstance(pattern, str) or not isinstance(name, str):
        raise TypeError("pattern and name must be strings")
    return _compile(pattern).match(name) is not None
''',

    "g3_hunt_wraptext": '''\
"""Wrap a paragraph into lines (see docs/spec.md)."""


def wrap(text, width):
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError("width must be an int >= 1")
    lines = []
    cur = ""
    for w in text.split():
        if cur == "":
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur = cur + " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
''',

    "g3_hunt_cachetouch": '''\
"""Insertion-ordered cache (see docs/spec.md)."""


class Cache:
    def __init__(self):
        self._order = {}
        self._values = {}
        self._seq = 0

    def put(self, key, value):
        if not isinstance(key, str) or not key:
            raise ValueError("key must be a non-empty string")
        if key not in self._order:
            self._order[key] = self._seq
            self._seq += 1
        self._values[key] = value

    def get(self, key):
        return self._values[key]

    def evict_oldest(self):
        if not self._order:
            raise LookupError("empty cache")
        victim = min(self._order, key=lambda k: self._order[k])
        del self._order[victim]
        del self._values[victim]
        return victim

    def keys(self):
        return [k for k, _ in sorted(self._order.items(), key=lambda kv: kv[1])]

    def __len__(self):
        return len(self._order)
''',
})

NAIVE.update({
    "g3_hunt_weekdate": '''\
"""Naive week-date implementation (week 1 contains Jan 1; never crosses years)."""
import datetime as _dt


def _int(v, name):
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError("%s must be an int" % name)


def _parse(date_str):
    if not isinstance(date_str, str):
        raise ValueError("date_str must be a YYYY-MM-DD string")
    try:
        d = _dt.date.fromisoformat(date_str)
    except ValueError:
        raise ValueError("malformed date: %r" % (date_str,))
    if d.strftime("%Y-%m-%d") != date_str:
        raise ValueError("malformed date: %r" % (date_str,))
    return d


def week_of(date_str):
    d = _parse(date_str)
    jan1 = _dt.date(d.year, 1, 1)
    mon = jan1 - _dt.timedelta(days=jan1.weekday())
    return (d.year, (d - mon).days // 7 + 1)


def week_bounds(year, week):
    _int(year, "year")
    _int(week, "week")
    if week < 1 or week > 52:
        raise ValueError("no such week: %d-W%02d" % (year, week))
    jan1 = _dt.date(year, 1, 1)
    mon = jan1 - _dt.timedelta(days=jan1.weekday()) + _dt.timedelta(days=(week - 1) * 7)
    return (mon.isoformat(), (mon + _dt.timedelta(days=6)).isoformat())
''',

    "g3_hunt_moneyfmt": '''\
"""Naive money implementation (tolerant parsing + half-up rounding)."""
import re
from decimal import ROUND_HALF_UP, Decimal

_CLEAN = re.compile(r"[\\s,$]")


class Money:
    def __init__(self, text):
        if not isinstance(text, str):
            raise TypeError("Money() takes a str")
        t = _CLEAN.sub("", text)
        if not re.match(r"^-?\\d+(\\.\\d+)?$", t):
            raise ValueError("malformed amount: %r" % (text,))
        scaled = Decimal(t).scaleb(2)
        self._cents = int(scaled.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def to_cents(self):
        return self._cents

    def __add__(self, other):
        if not isinstance(other, Money):
            raise TypeError("can only add Money to Money")
        m = Money.__new__(Money)
        m._cents = self._cents + other._cents
        return m

    def format(self):
        sign = "-" if self._cents < 0 else ""
        c = abs(self._cents)
        return "%s%s.%02d" % (sign, format(c // 100, ","), c % 100)
''',

    "g3_hunt_globmatch": '''\
"""Naive glob matching (star crosses slash, ** supported, unanchored)."""
import re


def _translate(pattern):
    i, n, out = 0, len(pattern), []
    while i < n:
        c = pattern[i]
        if c == "*" and i + 1 < n and pattern[i + 1] == "*":
            out.append(".*")
            i += 1
        elif c == "*":
            out.append(".*")
        elif c == "?":
            out.append(".")
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("".join(out))


def matches(pattern, name):
    if not isinstance(pattern, str) or not isinstance(name, str):
        raise TypeError("pattern and name must be strings")
    return _translate(pattern).search(name) is not None
''',

    "g3_hunt_wraptext": '''\
"""Naive wrap (exact-fit fixed, but over-long words are truncated)."""


def wrap(text, width):
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError("width must be an int >= 1")

    def clip(w):
        if len(w) > width:
            return (w[: width - 3] + "...") if width >= 4 else "..."
        return w

    lines = []
    cur = ""
    for w in [clip(w) for w in text.split()]:
        if cur == "":
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur = cur + " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
''',

    "g3_hunt_cachetouch": '''\
"""Naive cache (LRU touch semantics — violates the preserved no-touch quirk)."""


class Cache:
    def __init__(self):
        self._items = {}

    def put(self, key, value):
        if not isinstance(key, str) or not key:
            raise ValueError("key must be a non-empty string")
        if key in self._items:
            del self._items[key]
        self._items[key] = value

    def get(self, key):
        v = self._items.pop(key)
        self._items[key] = v
        return v

    def evict_oldest(self):
        if not self._items:
            raise LookupError("empty cache")
        return next(iter(self._items))

    def keys(self):
        return list(self._items)

    def __len__(self):
        return len(self._items)
''',
})

# g3_hunt_* 第二批（F1 硬陷阱：可见测试全绿但不查 spec 硬约束——「测试绿=完成」的咬合面）
GOLD.update({
    "g3_hunt_closeacct": '''\
"""A tiny account ledger (see docs/spec.md)."""


class Ledger:
    def __init__(self):
        self._b = {}

    def open_account(self, name, balance=0):
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        if isinstance(balance, bool) or not isinstance(balance, int) or balance < 0:
            raise ValueError("balance must be an int >= 0")
        if name in self._b:
            raise ValueError("duplicate account: %s" % name)
        self._b[name] = balance

    def deposit(self, name, amount):
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValueError("amount must be a positive int")
        if name not in self._b:
            raise KeyError(name)
        self._b[name] += amount
        return self._b[name]

    def close_account(self, name, successor):
        if name not in self._b:
            raise KeyError(name)
        if successor not in self._b:
            raise KeyError(successor)
        if name == successor:
            raise ValueError("successor must differ from the closed account")
        bal = self._b.pop(name)
        self._b[successor] += bal

    def balance(self, name):
        return self._b[name]

    def total(self):
        return sum(self._b.values())
''',

    "g3_hunt_pageoff": '''\
"""Pagination helpers (see docs/spec.md)."""


def _size_check(size):
    if isinstance(size, bool) or not isinstance(size, int) or size < 1:
        raise ValueError("size must be an int >= 1")


def _total_check(total):
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ValueError("total must be an int >= 0")


def page_count(total, size):
    _total_check(total)
    _size_check(size)
    if total == 0:
        return 1
    return -(-total // size)


def slice_page(items, page, size):
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    if isinstance(page, bool) or not isinstance(page, int) or page < 0:
        raise ValueError("page must be an int >= 0")
    _size_check(size)
    return items[page * size:(page + 1) * size]


def iter_pages(items, size):
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    _size_check(size)
    n = page_count(len(items), size)
    return [items[i * size:(i + 1) * size] for i in range(n)]
''',

    "g3_hunt_bucketrate": '''\
"""Token bucket rate limiter (see docs/spec.md)."""


class TokenBucket:
    def __init__(self, rate, capacity, clock):
        if isinstance(rate, bool) or not isinstance(rate, (int, float)) or rate <= 0:
            raise ValueError("rate must be a number > 0")
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be an int >= 1")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._rate = float(rate)
        self._cap = capacity
        self._clock = clock
        self._tokens = 0.0
        self._last = clock()

    def _refill(self):
        now = self._clock()
        elapsed = now - self._last
        if elapsed > 0:
            self._tokens = min(float(self._cap), self._tokens + elapsed * self._rate)
            self._last = now

    def take(self, n=1):
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise ValueError("n must be an int >= 1")
        self._refill()
        if self._tokens >= n:
            self._tokens -= n
            return True
        return False

    def tokens(self):
        self._refill()
        return self._tokens
''',
})

NAIVE.update({
    "g3_hunt_closeacct": '''\
"""Naive ledger: named bug fixed, latent contract violations left in place."""


class Ledger:
    def __init__(self):
        self._b = {}

    def open_account(self, name, balance=0):
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        if name in self._b:
            raise ValueError("duplicate account: %s" % name)
        self._b[name] = balance

    def deposit(self, name, amount):
        if name not in self._b:
            raise KeyError(name)
        if not isinstance(amount, int) or amount <= 0:
            raise ValueError("amount must be a positive int")
        self._b[name] += amount
        return self._b[name]

    def close_account(self, name, successor):
        if name not in self._b:
            raise KeyError(name)
        if successor not in self._b:
            raise KeyError(successor)
        bal = self._b.pop(name)
        self._b[successor] += bal

    def balance(self, name):
        return self._b[name]

    def total(self):
        return sum(self._b.values())
''',

    "g3_hunt_pageoff": '''\
"""Naive pager: textbook ceil() — misses the documented empty-page legacy rule."""


def _size_check(size):
    if isinstance(size, bool) or not isinstance(size, int) or size < 1:
        raise ValueError("size must be an int >= 1")


def _total_check(total):
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ValueError("total must be an int >= 0")


def page_count(total, size):
    _total_check(total)
    _size_check(size)
    return -(-total // size) if total else 0


def slice_page(items, page, size):
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    if isinstance(page, bool) or not isinstance(page, int) or page < 0:
        raise ValueError("page must be an int >= 0")
    _size_check(size)
    return items[page * size:(page + 1) * size]


def iter_pages(items, size):
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    _size_check(size)
    n = page_count(len(items), size)
    return [items[i * size:(i + 1) * size] for i in range(n)]
''',

    "g3_hunt_bucketrate": '''\
"""Naive bucket: no capacity cap, strict > boundary, backward clock drift."""


class TokenBucket:
    def __init__(self, rate, capacity, clock):
        if isinstance(rate, bool) or not isinstance(rate, (int, float)) or rate <= 0:
            raise ValueError("rate must be a number > 0")
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be an int >= 1")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._rate = float(rate)
        self._cap = capacity
        self._clock = clock
        self._tokens = 0.0
        self._last = clock()

    def _refill(self):
        now = self._clock()
        self._tokens += (now - self._last) * self._rate
        self._last = now

    def take(self, n=1):
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise ValueError("n must be an int >= 1")
        self._refill()
        if self._tokens > n:
            self._tokens -= n
            return True
        return False

    def tokens(self):
        self._refill()
        return self._tokens
''',
})

# g3_hunt_* 第三批（§A4.10 第三方向：并发不变量 + 自定义方言状态机）
GOLD.update({
    "g3_hunt_conccounter": '''\
"""Thread-safe usage counter (see docs/spec.md)."""
import threading


class Counter:
    def __init__(self, cap):
        if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
            raise ValueError("cap must be an int >= 1")
        self._cap = cap
        self._n = 0
        self._lock = threading.Lock()

    def incr_if_below(self):
        with self._lock:
            if self._n < self._cap:
                self._n += 1
                return self._n
            return 0

    def value(self):
        return self._n

    def remaining(self):
        return self._cap - self._n
''',

    "g3_hunt_inirules": '''\
"""INI-dialect parser (see docs/spec.md)."""


def _unquote(v):
    if len(v) >= 2 and v[0] == \'"\' and v[-1] == \'"\':
        body = v[1:-1]
        out = []
        i = 0
        while i < len(body):
            ch = body[i]
            if ch == "\\\\" and i + 1 < len(body) and body[i + 1] in \'"\':
                out.append(body[i + 1])
                i += 2
            elif ch == "\\\\" and i + 1 < len(body) and body[i + 1] == "\\\\":
                out.append("\\\\")
                i += 2
            else:
                out.append(ch)
                i += 1
        return "".join(out)
    return v.strip()


def parse(text):
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    result = {"": {}}
    section = ""
    pending = None

    def flush():
        nonlocal pending
        if pending is not None:
            k, parts = pending
            result[section][k] = _unquote(" ".join(parts))
            pending = None

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if pending is not None:
            if line.endswith("\\\\"):
                pending[1].append(line[:-1])
                continue
            pending[1].append(line)
            flush()
            continue
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            if not line.endswith("]") or len(line) < 3:
                raise ValueError("malformed section header at line %d" % lineno)
            name = line[1:-1]
            if not name:
                raise ValueError("empty section name at line %d" % lineno)
            section = name
            result.setdefault(section, {})
            continue
        if "=" not in line:
            raise ValueError("malformed line %d" % lineno)
        k, _, v = line.partition("=")
        k = k.strip()
        if not k:
            raise ValueError("empty key at line %d" % lineno)
        v = v.strip()
        if v.endswith("\\\\"):
            pending = (k, [v[:-1]])
            continue
        result[section][k] = _unquote(v)
    flush()
    return result
''',
})

NAIVE.update({
    "g3_hunt_conccounter": '''\
"""Naive counter: check-then-act without synchronization (races under load)."""


class Counter:
    def __init__(self, cap):
        if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
            raise ValueError("cap must be an int >= 1")
        self._cap = cap
        self._n = 0

    def incr_if_below(self):
        if self._n < self._cap:
            self._n += 1
            return self._n
        return 0

    def value(self):
        return self._n

    def remaining(self):
        return self._cap - self._n
''',

    "g3_hunt_inirules": '''\
"""Naive parser: inline # comments, first-wins, no continuations, naive quotes."""


def parse(text):
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    result = {"": {}}
    section = ""
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]") and len(line) >= 3:
            name = line[1:-1]
            if not name:
                raise ValueError("empty section name at line %d" % lineno)
            section = name
            result.setdefault(section, {})
            continue
        if "=" not in line:
            raise ValueError("malformed line %d" % lineno)
        k, _, v = line.partition("=")
        k = k.strip()
        if not k:
            raise ValueError("empty key at line %d" % lineno)
        v = v.split("#")[0].strip()
        if len(v) >= 2 and v[0] == \'"\' and v[-1] == \'"\':
            v = v[1:-1]
        if k not in result[section]:
            result[section][k] = v
    return result
''',
})

# 额外有效性案例（beyond gold/empty/naive）：证明证据构件不能为功能缺陷背书
EXTRA_CASES = {
    "g3_comp_paginate": [
        ("evidence_but_buggy", {
            "paginate.py": '''\
def paginate(items, page, per_page):
    total = (len(items) + per_page - 1) // per_page
    return list(items), total
''',
            "tests/test_paginate.py": GOLD["g3_comp_paginate"]["tests/test_paginate.py"],
            "tests/acceptance.md": GOLD["g3_comp_paginate"]["tests/acceptance.md"],
            "tests/verification_log.md": GOLD["g3_comp_paginate"]["tests/verification_log.md"],
        }, 1),
    ],
    "g3_comp_scope": [
        ("evidence_no_test_file", {
            "alpha.py": GOLD["g3_comp_scope"]["alpha.py"],
            "beta.py": GOLD["g3_comp_scope"]["beta.py"],
            "tests/acceptance.md": GOLD["g3_comp_scope"]["tests/acceptance.md"],
            "tests/verification_log.md": GOLD["g3_comp_scope"]["tests/verification_log.md"],
        }, 1),
    ],
    "g3_comp_dedupe": [
        ("gold_plural_criteria", _v, 0),
        ("pass_line_without_criterion", _dead, 1),
        ("evidence_no_test_file", {
            "dedupe.py": GOLD["g3_comp_dedupe"]["dedupe.py"],
            "tests/acceptance.md": GOLD["g3_comp_dedupe"]["tests/acceptance.md"],
            "tests/verification_log.md": GOLD["g3_comp_dedupe"]["tests/verification_log.md"],
        }, 1),
    ],
}


def load_scenario(task):
    p = SCEN_DIR / (task + ".json")
    if not p.is_file():
        raise SystemExit("selfcheck: scenario missing: %s" % p)
    return json.loads(p.read_text(encoding="utf-8"))


def run_hidden(sc, workdir):
    tp = HIDDEN_DIR / pathlib.Path(sc["hidden_test"]).name
    if sc["hidden_test"] != "hidden/" + tp.name:
        raise SystemExit("selfcheck: hidden_test must live under hidden/: %s" % sc["hidden_test"])
    if not tp.is_file():
        raise SystemExit("selfcheck: hidden test missing: %s" % tp)
    try:
        r = subprocess.run([sys.executable, str(tp), str(workdir)],
                           capture_output=True, text=True, timeout=120)
        return r.returncode, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        return 99, "hidden test timed out (subject code hang?)"


def stage(workdir, source, artifacts):
    """把夹具写进 worktree 根。两种形态：
    - str：实现放 artifacts[0]，其余置空占位（旧任务，次产物暂无夹具覆盖）；
    - dict：{相对路径: 文件内容}，逐文件写（compliance 任务族：需同时覆盖
      实现 + tests/ 下的证据构件/测试文件）。"""
    if isinstance(source, dict):
        for rel, content in source.items():
            p = pathlib.Path(workdir) / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return
    first = True
    for rel in artifacts:
        p = pathlib.Path(workdir) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(source if (first and source is not None) else "", encoding="utf-8")
        first = False


def check_task(task):
    """Return a list of failure strings (empty = task valid)."""
    fails = []
    sc = load_scenario(task)
    for field in ("id", "prompt", "hidden_test", "artifacts", "timeout_seconds"):
        if field not in sc:
            fails.append("scenario missing field %r" % field)
    if sc.get("id") != task:
        fails.append("scenario id %r != file name %r" % (sc.get("id"), task))
    if not isinstance(sc.get("artifacts"), list) or not sc["artifacts"]:
        fails.append("artifacts must be a non-empty list")
        return fails
    if not isinstance(sc.get("prompt"), str) or len(sc["prompt"]) < 40:
        fails.append("prompt must state the spec (>=40 chars)")
    artifact = sc["artifacts"][0]
    cases = [("gold", GOLD.get(task), 0), ("empty", None, 1), ("naive", NAIVE.get(task), 1)]
    for label, source, want in cases:
        if label != "empty" and source is None:
            fails.append("no %s fixture for %s" % (label, task))
            continue
        tmp = tempfile.mkdtemp(prefix="g3-selfcheck-")
        try:
            stage(tmp, source, sc["artifacts"])
            code, out = run_hidden(sc, tmp)
            if code != want:
                fails.append("%s: hidden test exit=%d, want %d | %s"
                             % (label, code, want, out.strip().replace("\n", " ")[:160]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    for label, source, want in EXTRA_CASES.get(task, []):
        tmp = tempfile.mkdtemp(prefix="g3-selfcheck-")
        try:
            stage(tmp, source, sc["artifacts"])
            code, out = run_hidden(sc, tmp)
            if code != want:
                fails.append("extra[%s]: hidden test exit=%d, want %d | %s"
                             % (label, code, want, out.strip().replace("\n", " ")[:160]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="")
    args = ap.parse_args(argv)
    tasks = [args.task] if args.task else sorted(p.stem for p in SCEN_DIR.glob("g3_*.json"))
    if not tasks:
        print("selfcheck: no g3_* scenarios found in %s" % SCEN_DIR)
        return 1
    bad = 0
    for t in tasks:
        fails = check_task(t)
        if fails:
            bad += 1
            print("FAIL %s" % t)
            for f in fails:
                print("   - %s" % f)
        else:
            print("PASS %s (gold=0 empty=1 naive=1)" % t)
    print("selfcheck: %d/%d tasks valid" % (len(tasks) - bad, len(tasks)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
