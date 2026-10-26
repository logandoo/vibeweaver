#!/usr/bin/env python3
"""scripts/gate_events.py — 从 eval run 的 trajectory.json 解析 gate 插件的拦截事件。

产品形态 eval（v2）的「插件体检表」：gate 插件在 vibeweaver-active 项目里对
write/edit/bash 输出 GATE-BLOCKED 反馈（write-succeeded-completion-gate 形），
subject 的每一次被拦截都会出现在 opencode 的 JSON 事件流里（trajectory.json 的
agent.stdout）。本模块把它机械地数出来：次数、类型分布、首次拦截位置。

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
# Only the plugin's own message shape counts as an interception: "GATE-BLOCKED"
# followed by a parenthesised label. Prose mentions (the SKILL docs explain the
# mechanism and quote the token, v2-smoke2 showed 6 such false hits) never count.
MESSAGE_RE = re.compile(r"GATE-BLOCKED\s*\(")

# 顺序敏感：physical-gate 消息体内也会提到 evidence lock 等词，先匹配最外层标签。
TYPE_PATTERNS = [
    ("destructive", re.compile(r"GATE-BLOCKED \(destructive guard\)")),
    ("secret", re.compile(r"GATE-BLOCKED \((?:vibeweaver )?secret", re.I)),
    ("stall", re.compile(r"STALL observed")),
    ("evidence-lock", re.compile(r"GATE-BLOCKED \(vibeweaver evidence lock\)")),
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
    """trajectory dict -> {gate_blocked_events, by_type, first_blocked_at, events}."""
    total = 0
    by_type = {}
    first = None
    events = []
    for idx, text in _iter_texts(traj):
        if PREFIX not in text:
            continue
        for line in text.splitlines():
            n = len(MESSAGE_RE.findall(line))
            if not n:
                continue
            total += n
            typ = classify(line)
            by_type[typ] = by_type.get(typ, 0) + n
            if first is None:
                first = idx
            events.append({"event_index": idx, "type": typ,
                           "excerpt": line.strip()[:160]})
    return {"gate_blocked_events": total, "by_type": by_type,
            "first_blocked_at": first, "events": events[:50]}


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
