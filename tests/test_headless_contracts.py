#!/usr/bin/env python3
"""tests/test_headless_contracts.py — F7 headless 降级条款的回归门（判据 #73）。

v2 战役 F7 实锤：subject 按 trust-tier 规则停在「等用户确认」结束会话，无头
环境无人应答 → CLI exit 1，run 报废。修复 = 契约明文「无人值守降级」：
等待改为记账（`- awaiting decision:` + 保持 ⏳）。两面都必须钉住：
  ① 降级条款存在（MEMORY_RULES §A7.7.1 + COMPLETION_GATE 预输出清单）；
  ② 反伪造不放松——⏳→✅ 仍然只能由用户确认，永不自升（放宽只覆盖「等待」，
     不覆盖「验证」）。
"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class HeadlessClause(unittest.TestCase):
    def test_memory_rules_degradation_clause(self):
        txt = (ROOT / "vibeweaver" / "MEMORY_RULES.md").read_text(encoding="utf-8")
        self.assertIn("A7.7.1", txt, "headless 降级节缺失")
        self.assertIn("awaiting decision", txt, "待确认项必须记账为 awaiting decision")
        self.assertIn("never stop work or end the session waiting for confirmation",
                      txt, "无人值守不得等待确认（F7 死锁条款）")

    def test_completion_gate_preoutput_item(self):
        txt = (ROOT / "vibeweaver" / "COMPLETION_GATE.md").read_text(encoding="utf-8")
        self.assertIn("Headless close", txt, "预输出清单缺 headless 条")
        self.assertIn("awaiting decision", txt)

    def test_anti_forgery_unchanged(self):
        """降级不得夹带 ⏳ 自升 ✅——反伪造条款必须原样在位。"""
        txt = (ROOT / "vibeweaver" / "MEMORY_RULES.md").read_text(encoding="utf-8")
        self.assertIn("Never write `status: ✅`", txt, "反伪造条款被改——⏳→✅ 只能由用户确认")
        self.assertIn("only user confirmation can verify a fix", txt)


if __name__ == "__main__":
    unittest.main()
