#!/usr/bin/env python3
"""scripts/gate_events.py — 从 eval run 的 trajectory.json 解析 gate 插件的拦截事件。

产品形态 eval（v2）的「插件体检表」：gate 插件在 vibeweaver-active 项目里对
write/edit/bash 输出硬 `GATE-BLOCKED`、`GATE-CHECK-UNAVAILABLE` 或
`COMPLETION-NOT-READY` 提示；这些事件都会出现在 opencode 的 JSON 事件流里
（trajectory.json 的 agent.stdout）。本模块把它们机械地数出来：次数、类型分布、
首次事件位置。

口径（诚实性）：
  * 只统计 JSON 事件流里 tool_result 文本中的命中——非 JSON 的裸文本永不计事件
    （宁缺勿造）；
  * 一条输出里的多次命中分别计（gate 每条消息一行一个前缀）；
  * 解析失败逐行跳过，不抛异常（trajectory 是证据，不是输入校验对象）。

用法：python3 scripts/gate_events.py <trajectory.json> [--json]
"""
import json
import re
import sys

PREFIX = "GATE-BLOCKED"
COMPLETION_PREFIX = "[VIBEWEAVER COMPLETION-NOT-READY]"
UNAVAILABLE_PREFIX = "GATE-CHECK-UNAVAILABLE"
# Only the plugin's own message shape counts as an interception: a token
# followed by a parenthesised label / canonical completion prefix. Prose
# mentions (the SKILL docs explain the mechanism and quote the token,
# v2-smoke2 showed 6 such false hits) never count.
MESSAGE_RE = re.compile(r"GATE-BLOCKED\s*\(")
# Anchor the W23 markers to the plugin's message shape; docs/review text quotes
# the bare token and must never inflate the event metric.
COMPLETION_RE = re.compile(
    r"^" + re.escape(COMPLETION_PREFIX) + r"\s+WRITE SUCCEEDED\s+—\s+scope=")
UNAVAILABLE_RE = re.compile(
    r"^GATE-CHECK-UNAVAILABLE\s*\([^)]*\)\s*:\s*WRITE SUCCEEDED")
STALL_RE = re.compile(r"\[GATE-WARNING \(vibeweaver-stall\)\]\s*STALL observed")

# 顺序敏感：physical-gate 消息体内也会提到 evidence lock 等词，先匹配最外层标签。
TYPE_PATTERNS = [
    ("destructive", re.compile(r"GATE-BLOCKED \(destructive guard\)")),
    ("secret", re.compile(r"GATE-BLOCKED \((?:vibeweaver )?secret", re.I)),
    ("stall", re.compile(r"\[GATE-WARNING \(vibeweaver-stall\)\]|STALL observed")),
    ("evidence-lock", re.compile(r"GATE-BLOCKED \(vibeweaver evidence lock\)")),
    ("unavailable", re.compile(r"GATE-CHECK-UNAVAILABLE")),
    ("integrity", re.compile(r"GATE-BLOCKED \(vibeweaver integrity\)")),
    ("completion", re.compile(re.escape(COMPLETION_PREFIX))),
    ("completion", re.compile(r"GATE-BLOCKED \((?:vibeweaver )?(?:physical )?gate\)")),
]


def classify(line):
    for name, pat in TYPE_PATTERNS:
        if pat.search(line):
            return name
    return "other"


def _iter_texts(traj):
    """yield (event_index, text) for every tool-result-ish text chunk."""
    agent = traj.get("agent") or {}
    stdout = agent.get("stdout") or ""
    for idx, raw in enumerate(stdout.splitlines()):
        raw = raw.strip()
        if not raw.startswith("{"):
            continue
        try:
            ev = json.loads(raw)
        except ValueError:
            continue
        seen = set()

        def emit(obj):
            if isinstance(obj, str) and obj and obj not in seen:
                seen.add(obj)
                yield_texts.append(obj)

        yield_texts = []
        part = ev.get("part") or {}
        state = part.get("state") or {}
        emit(state.get("output"))
        emit(state.get("error"))
        emit(part.get("text"))
        emit(ev.get("text"))
        for t in yield_texts:
            yield idx, t


def summarize(traj):
    """trajectory dict -> gate event counts.

    Keeps `gate_blocked_events` as the HARD block count (backward compatible)
    and adds `completion_not_ready_events` for the W23 non-throwing debt note.
    `gate_events` is the total plugin-intervention count used by health checks.
    """
    hard = 0
    completion = 0
    stalls = 0
    by_type = {}
    first = None
    events = []
    last = None
    for idx, text in _iter_texts(traj):
        if (PREFIX not in text and COMPLETION_PREFIX not in text
                and UNAVAILABLE_PREFIX not in text and STALL_RE.search(text) is None):
            continue
        last = None  # detail attribution never crosses a result/text boundary
        for line in text.splitlines():
            n_hard = len(MESSAGE_RE.findall(line)) + len(UNAVAILABLE_RE.findall(line))
            n_completion = len(COMPLETION_RE.findall(line))
            n_stall = len(STALL_RE.findall(line))
            n = n_hard + n_completion + n_stall
            if not n:
                # Attribute a secret detail line back to the multiline hard
                # banner it belongs to (the wrapper label is `integrity`).
                if last and last.get("type") == "integrity" and re.match(r"^\s*-\s*secret scan:", line):
                    by_type["integrity"] = max(0, by_type.get("integrity", 0) - 1)
                    if by_type["integrity"] == 0:
                        by_type.pop("integrity", None)
                    by_type["secret"] = by_type.get("secret", 0) + 1
                    last["type"] = "secret"
                continue
            hard += n_hard
            completion += n_completion
            stalls += n_stall
            typ = classify(line)
            by_type[typ] = by_type.get(typ, 0) + n
            if first is None:
                first = idx
            last = {"event_index": idx, "type": typ,
                    "excerpt": line.strip()[:160]}
            events.append(last)
    return {"gate_blocked_events": hard, "completion_not_ready_events": completion,
            "stall_events": stalls, "gate_events": hard + completion + stalls,
            "by_type": by_type, "first_blocked_at": first, "events": events[:50]}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    traj = json.loads(open(argv[0], encoding="utf-8").read())
    s = summarize(traj)
    if "--json" in argv:
        print(json.dumps(s, indent=2, ensure_ascii=False))
    else:
        print("gate_blocked_events: %s | by_type: %s | first: %s"
              % (s["gate_blocked_events"], s["by_type"], s["first_blocked_at"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
