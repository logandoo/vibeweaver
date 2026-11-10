#!/usr/bin/env python3
"""scripts/eval_tokens.py — 从 opencode `--format json` 事件流里汇总 token 用量。

eval_run.py 的 cost.json 一直有 `tokens` 字段，但值取自 `agent.get("tokens")`，
从未被填写（lab 现存 cost.json 全部为 null）。而每个 trajectory.json 的
agent.stdout 里，opencode 在每一步结束时都会输出一条 `step_finish` 事件：

  {"type":"step_finish", ..., "part": {"type":"step-finish", "cost": 0,
     "tokens": {"input": N, "output": N, "reasoning": N,
                "cache": {"read": N, "write": N}}}}

本模块把这些事件机械地加总。口径（与 gate_events.py 一致）：
  * 只认 JSON 事件流里 type == "step_finish" 的事件——裸文本/正文里提到
    step_finish 永不计数；
  * 解析失败逐行跳过，不抛异常；
  * 没有任何 step_finish 事件 → 返回 None（"未知"），绝不返回 0：超时被杀的
    run 没有事件流，0 会把它伪装成"零成本"。

total = input + output + reasoning + cache_read + cache_write（模型实际处理的
全部 token；有 prompt cache 的供应商上 cache_read 计价远低于 input，报告里
分列，不在此处折算美元）。

用法：python3 scripts/eval_tokens.py <trajectory.json>
"""
import json
import sys

FIELDS = ("input", "output", "reasoning", "cache_read", "cache_write")


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0


def summarize_tokens(stdout):
    """Sum opencode step_finish token counts; None when no event is present."""
    if not stdout:
        return None
    acc = {k: 0 for k in FIELDS}
    cost = 0.0
    steps = 0
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{") or "step_finish" not in line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if not isinstance(ev, dict) or ev.get("type") != "step_finish":
            continue
        part = ev.get("part")
        tok = part.get("tokens") if isinstance(part, dict) else None
        if not isinstance(tok, dict):
            continue
        cache = tok.get("cache") if isinstance(tok.get("cache"), dict) else {}
        acc["input"] += _num(tok.get("input"))
        acc["output"] += _num(tok.get("output"))
        acc["reasoning"] += _num(tok.get("reasoning"))
        acc["cache_read"] += _num(cache.get("read"))
        acc["cache_write"] += _num(cache.get("write"))
        cost += _num(part.get("cost"))
        steps += 1
    if steps == 0:
        return None
    acc["total"] = sum(acc[k] for k in FIELDS)
    acc["cost"] = cost
    acc["steps"] = steps
    return acc


def main(argv):
    if len(argv) != 2:
        print("usage: eval_tokens.py <trajectory.json>", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        traj = json.load(fh)
    stdout = (traj.get("agent") or {}).get("stdout", "")
    print(json.dumps(summarize_tokens(stdout), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
