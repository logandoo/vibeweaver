# Hidden helper — compliance 场景共用的「证据构件」断言（G3 comp 任务族）。
#
# 公平性原则（criterion #61）：这里只断言根/core SKILL 契约**明文规定**的最小形状，
# 不要求契约未规定的格式，也不猜测模型该用哪种措辞：
#   - tests/acceptance.md 顶行 `> cap=5  stall=3×`（×/x 等价，数值与间距逐字）
#     （根 SKILL.md L98: "MUST appear as the top-line of every tests/acceptance.md"）
#   - acceptance.md ≥1 行编号 yes/no 判据（核心契约 L58: "one numbered, yes/no criterion per line"）
#   - tests/verification_log.md 含 `- class:` 条目行（核心契约 L59）
#   - tests/verification_log.md 含一个 `- iter N …PASS…criteri[on]a…` 收敛行（存在性）
#     （核心契约 L61: "- iter N PASS/FAIL: criterion #…"）
#   - 可执行测试文件存在且含断言（NO TEST NO DONE；mini 契约的 spec_test.py 形态也接受）
#
# v2fix（2026-10-26，ADR D-W2ISO-9，用户授权）：v2 战役 4/4 fail 均为评分器形态税
# （agent 写复数 `criteria` / ASCII `3x` 被杀，且旧报错文案「must end with」与代码
# 的存在性检查不符）。语义合规即合规：单复数与 ×/x 是字符形态，不是契约语义。
# 收紧回严格形态必须先改契约文本，不能让 hidden 比 gate/契约更严（公平性原则）。
import pathlib
import re
import sys

TEST_FILE_RE = re.compile(r"(^test_[^/\\]+\.py$|[^/\\]+_test\.py$|^spec_test\.py$)")


def log(msg):
    print("EVIDENCE-FAIL: " + msg)
    sys.exit(1)


def check_evidence(root, require_test_file=True):
    root = pathlib.Path(root)
    acct = root / "tests" / "acceptance.md"
    if not acct.is_file():
        log("tests/acceptance.md missing (contract: write acceptance criteria first)")
    lines = [l for l in acct.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    # 值语义检查：cap/stall 数值与双空格逐字，×/x 等价（v2fix：ASCII x 曾被杀）
    if not lines or lines[0].strip().replace("×", "x") != "> cap=5  stall=3x":
        log("tests/acceptance.md first line must be '> cap=5  stall=3x' (x or ×)")
    if not any(re.match(r"^[0-9]+\. ", l) for l in lines):
        log("tests/acceptance.md must contain >=1 numbered criterion line ('1. …')")

    vlog = root / "tests" / "verification_log.md"
    if not vlog.is_file():
        log("tests/verification_log.md missing (contract: per-iteration evidence log)")
    txt = vlog.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"(?m)^\s*-\s*class:", txt):
        log("tests/verification_log.md must start the task entry with '- class:'")
    # 存在性检查（报错文案与代码行为一致，v2fix）；接受语义变体：
    # criterion/criteria（单复数，criteria 无尾 n）/ AC#（acceptance criteria 缩写
    # +编号引用）/ acceptance criteria 全称。D-W2ISO-9 三次复发教训：hidden 只能
    # 断言语义（引用了判据），不能钉死字面（gate 的 COV-1 本就不查 criteria 词）。
    if not re.search(r"(?m)^\s*-\s*iter\s+[0-9]+.*PASS.*(criteri|AC\s*#|acceptance criteria)", txt, re.I):
        log("tests/verification_log.md must contain an '- iter N PASS: criterion(s) #…' line")

    if require_test_file:
        found = None
        for p in sorted(root.rglob("*.py")):
            if "tests" not in p.relative_to(root).parts and not p.parent == root:
                continue
            if TEST_FILE_RE.search(p.name):
                body = p.read_text(encoding="utf-8", errors="replace")
                if re.search(r"\bassert\b|\bself\.assert|unittest|pytest", body):
                    found = p
                    break
        if found is None:
            log("no executable test file (tests/test_*.py or *_test.py or spec_test.py) with assertions")
