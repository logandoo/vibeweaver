# vibeweaver-mini

[vibeweaver](https://github.com/logandoo/vibeweaver) 的小模型版：**确定性循环 + checker**。为强制注入场景设计——弱指令遵循的模型不会主动加载 skill，也不会执行长规则；它只会执行具体的、能立刻看到结果的机械动作。

## 它是什么

一套两件套：

- `SKILL.md`（约 2KB）——只讲一个循环：运行 checker → 修第一个失败 → 重复，直到打印 `ALL CHECKS PASS`。不要求模型记住任何工程原则。
- `scripts/vw_check.py`——确定性 checker：跑 pytest、打印失败清单与"观察值 ≠ 期望值"修复包、**测试集变化即拒绝运行**（哈希守卫，纪律工具而非安全边界）。

## 为什么有效（G1 探针，2026-09，qwen3.6-35B-A3B 强制注入）

四道所有 prompt 路线都修不好的题（grade_school / list_ops / phone_number / transpose）：

| 配置 | 通过 |
|---|---|
| mini 旧版（纯规则 prose） | 1/4 |
| mini-v2 + checker + **自写测试** | 1/4（phone_number 反而从 13/21 掉到 5/21——自写测试会自欺） |
| mini-v2 + checker + **生成测试（未资格验证）** | 1/4（假绿：冻结套件全过、真测试 10 failed） |
| mini-v2 + checker + **项目真测试** | **4/4 全满分** |

结论：**循环不是瓶颈，oracle 才是。** 小模型乐意跑 12-36 次 checker；缺的是可信反馈。用项目自己的测试当 oracle，弱模型能修好它此前修不好的题。

## 安装

```bash
bash install.sh                 # macOS / Linux
install.bat                     # Windows
```

然后在要跑循环的项目里：

```bash
bash ~/.config/opencode/skills/vibeweaver-mini/scripts/setup_project.sh
# 或：sh setup_project.sh /path/to/project
# Windows：%USERPROFILE%\.config\opencode\skills\vibeweaver-mini\scripts\setup_project.bat
```

它会把 `vw_check.py` 和 `script/check.sh` 放进项目——也就是 gate 识别 mini 的标记。之后强制注入或手动要求模型："运行 `python3 vw_check.py`，直到它打印 ALL CHECKS PASS。" Windows 上用 `python vw_check.py`；`script/check.sh` 回退需要 bash，所以项目里要保留 `vw_check.py`。

## Checker gate

`install.sh` 还会把 `vibeweaver-mini-gate.js` 装进
`~/.config/opencode/plugins/`。会话项目里有 `vw_check.py`（或没有
`vw_check.py` 时的 mini `script/check.sh`）时激活；每次 write/edit 后跑
checker，失败就把修复包作为阻断消息返回，成功则追加 checker 自己的输出
（含 `ALL CHECKS PASS`）。gate 激活期间 checker、它的状态文件和
`tests/verification_log.md` 都是只读的。

session idle 时如果模型声称完成而 checker 没绿，会追加纠正提示（预算 2 次/
会话，不重置）。完整版项目（根目录有 `tests/verification_log.md`）不归它管，
由完整版 gate 接管。没有 prompt API 的宿主（当前 v2 上下文）只有写入 gate。

关闭：`VIBEWEAVER_MINI_GATE=off`；checker 超时：`VIBEWEAVER_MINI_TIMEOUT_MS`
（默认 900000，与 `vw_check.py` 一致）。`write`/`edit` 直接覆盖；bash 对
checker/状态的常见重定向会被启发式拦截，其他 shell 改动不在钩子范围内。

## 硬规则（skill 内已写）

- **项目自己的测试是唯一能认证的 oracle**；自写测试是弱证据，必须在报告里说明。
- 不许改测试让它们变绿；checker 检测到测试集变化会拒绝运行。
- 不发明接口：规格里看不见的函数/方法 = 待确认问题，不是猜测对象。
- 同一检查失败 3 次 → 先重读规格再动手。

## 与完整版的关系

完整版 vibeweaver 是给能力足够模型的完整工程契约（证据门禁、记忆、设计门、审计）。mini 不是它的压缩版，而是**另一条路线**：把"验证"从提示词里搬到确定性程序里。两者可以共存——完整版管流程可信度，mini 管弱模型的执行闭环。

mini 不用完整版的 gate/auditor 组合：它们以 `tests/verification_log.md` 为激活条件，而 mini 不创建这个文件。mini 自带一个更小的守卫 `vibeweaver-mini-gate.js`，直接以 checker 的 `ALL CHECKS PASS` 为契约。
