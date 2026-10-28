#!/usr/bin/env python3
"""vibeweaver-eval/harness/cross_model_matrix.py — 跨模型 × 逐题成败矩阵 + 共同失败分解。

从 workspace/iteration-1/graded/*.json 聚合 f2p_pass，按模型 × 裸/最优臂输出 markdown
矩阵，并分解三类任务（共同失败 = 全部裸臂挂 → 题集共同难点；判别 = 各模型成败不同；
共同成功 = 全部裸臂过 → 天花板）。回答审计 F-C/外部分析 §三的「失败性质分解」要求。
用法：python3 harness/cross_model_matrix.py > matrix.md
"""
import json
import pathlib
import sys

GRADED = pathlib.Path(__file__).resolve().parent.parent / "workspace" / "iteration-1" / "graded"

# 模型 × (裸臂, 参考臂)：参考臂 = 该模型的最优配置（REPORT.md 各轮结论）
MODELS = [
    ("qwen3.6-27b", "baseline", "with_skill_mini"),
    ("deepseek-v4-flash", "ds_baseline", "ds_full_forced"),
    ("qwen3.8-27b", "q38_baseline", "q38_v2"),
    ("qwen3.6-35b-a3b", "a3b_baseline", "a3b_mini_new"),
]

POLY = ["polyglot_bowling", "polyglot_grade_school", "polyglot_list_ops",
        "polyglot_phone_number", "polyglot_simple_linked_list", "polyglot_pig_latin",
        "polyglot_robot_name", "polyglot_transpose", "polyglot_two_bucket",
        "polyglot_variable_length_quantity"]
SWE = ["swebench_pallets_flask_4045", "swebench_pallets_flask_4992",
       "swebench_psf_requests_3362", "swebench_pytest_dev_pytest_6116",
       "swebench_pytest_dev_pytest_9359", "swebench_sympy_sympy_21627"]


def load():
    """(task, arm) -> bool | None"""
    out = {}
    for p in GRADED.glob("grade_*.json"):
        stem = p.name[len("grade_"):-len(".json")]
        if "__" not in stem:
            continue
        task, arm = stem.split("__", 1)
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        v = d.get("f2p_pass")
        if not isinstance(v, bool):
            v = d.get("passed")  # polyglot 轮的判定键
        out[(task, arm)] = bool(v) if isinstance(v, bool) else None
    return out


def cell(data, task, arm):
    v = data.get((task, arm))
    return "—" if v is None else ("✅" if v else "❌")


def short(task):
    return task.replace("polyglot_", "").replace("swebench_", "")


def main():
    data = load()
    rows = POLY + SWE
    print("| task | " + " | ".join("%s bare / ref" % m for m, _, _ in MODELS) + " | class |")
    print("|---|---|---|---|")
    counts = {"common-fail": [], "common-pass": [], "discriminative": []}
    for task in rows:
        marks, bare = [], []
        for _m, b, ref in MODELS:
            bv, rv = data.get((task, b)), data.get((task, ref))
            marks.append("%s / %s" % (cell(data, task, b), cell(data, task, ref)))
            if bv is not None:
                bare.append(bv)
        if bare and not any(bare):
            kind = "common-fail"
        elif bare and all(bare):
            kind = "common-pass"
        else:
            kind = "discriminative"
        counts[kind].append(task)
        print("| %s | %s | %s |" % (task, " | ".join(marks), kind))
    print()
    print("## 共同失败分解（bare 臂）")
    print()
    for k, label in [("common-fail", "共同失败（全部模型裸臂挂 —— 题集共同难点，非模型差异）"),
                     ("discriminative", "判别题（裸臂成败不同 —— 模型差异真实存在的位置）"),
                     ("common-pass", "共同成功（全部模型裸臂过 —— 天花板）")]:
        print("- **%s** (%d): %s" % (label, len(counts[k]),
                                     ", ".join(short(x) for x in counts[k]) or "无"))
    print()
    print("_生成：`python3 harness/cross_model_matrix.py`（数据源 workspace/iteration-1/graded/）_")


if __name__ == "__main__":
    sys.exit(main())
