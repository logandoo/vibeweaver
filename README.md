# vibeweaver

给 opencode agent 装上工程纪律的 skill：规则文本 + 机械强制（gate/audit 插件）两层，编码任务测试先行、完工要有证据、违规当场拦下。

装好后无需调用动作：提一个编码任务，skill 自动加载，缺证据的写入被门禁拦下，完工必须拿得出验证日志。

## 为什么是两层

只有规则文本的 skill 效果如何，本项目实测过：在同一批「过程契约」任务上，纯文本层的自发合规率很低（数据与口径见 `docs/EVAL_G3_PILOT_REPORT.md` §7，结论层已按用户裁定降级为架构论证）。文本能告诉 agent 该做什么，保证它做了的是插件。这正是 gate 与 audit 插件存在的原因，也是当前产品形态评测（`docs/EVAL_V2_PREREG.md`）要回答的问题。

## 安装

```bash
./install.sh      # macOS / Linux
install.bat       # Windows
```

安装内容写入 `~/.config/opencode/`：12 个 skill md、`scripts/`、以及 `plugins/` 下的两个插件（`vibeweaver-gate.js`、`vibeweaver-audit.js`）。重启 opencode 生效。卸载走同一入口（`scripts/install.py --uninstall`），以 `.installed.json` 清单为所有权记录。

## 功能与可观察行为

- 写代码前，agent 先在项目的 `tests/` 下建立验收标准（acceptance.md）
- 每次 write/edit 之后，gate 插件运行构件断言；证据缺失时工具结果里会带回 GATE-BLOCKED 提示，列出缺什么、怎么补
- 完工输出必须带验证日志（verification_log.md）里的逐条证据，口头声称做完不算数
- 修复循环有上限：cap=5，连续 3 次无进展即停，重试必须携带诊断
- 修改已有项目前先跑通现有测试（Baseline GREEN）；重大变更走独立评审
- audit 插件被动观察会话，对「声称做了但没证据」给出 OK / BAD / UNCERTAIN 裁决；违规锁存并拦截后续写入，跨会话自动释放
- 模型输出退化（行组重复、裸序列、无换行重复流）被 loop-guard 即时打断，每会话限次
- 内容门禁：secret 形态扫描、测试弱化守卫（删断言必须留理由）、高风险路径（auth、payment、crypto）强制评审包

## 使用方法

装好后无需手动调用。在 opencode 里提出编码任务（实现功能、修 bug、写测试、部署），skill 按任务规模自动选择完整契约或精简档（vibeweaver-mini），随后按上节所列方式接管流程。

对项目启用门禁：在项目根创建 `tests/verification_log.md`（或 `.vibeweaver/project.json`）即激活；`tests/project_profile.json` 声明项目类型（library、backend-api、service、web 等），结构性不适用的检查组自动跳过，例如 library 项目不要求服务生命周期脚本。

## 配置

审计配置在 `~/.config/opencode/vibeweaver/audit.json`，位置刻意在模型可写范围之外：

| 键 | 作用 | 默认值 |
|---|---|---|
| `samplingRate` | LLM 升级审查抽样率（%） | 10 |
| `escOnUncertain` | UNCERTAIN 结果是否升级审查 | 开 |
| `escOnHighRisk` | 高风险变更是否升级审查 | 开 |
| `forbiddenRaw` | 禁用的原始命令列表 | 空 |
| `redTtlHours` | RED 锁存的 TTL 兜底（小时） | 24 |

临时关闭（环境变量）：`VIBEWEAVER_GATE=off`、`VIBEWEAVER_AUDIT=off`、`VIBEWEAVER_LOOPGUARD=off`。其余可调项（checker 超时、自定义 checker 等）见 `docs/COMPATIBILITY.md`。

## 兼容性

两个插件以单文件同时支持 opencode v1 与 v2：模块默认导出 `{ id, server, setup }`，v1（≥ 1.18.29）走 `readV1Plugin` 检测，v2（≥ 2.0.0）按 `PluginModule` schema 解码，两版共用同一份逻辑与 `.vibeweaver/` 状态。细节与已知边界见 `docs/COMPATIBILITY.md`。

## 测试

```bash
node scripts/audit_selftest.mjs     # 审计核心 fixture 测试
node scripts/mutation_sweep.mjs     # 变异扫描：逐项破坏检查点，验证审计能捕获
node tests/plugin_compat_test.mjs   # 双 loader 兼容 harness
python3 -m unittest discover -s tests -p 'test_*.py'
bash script/linux/project_build.sh  # 全量构建回归
```

真实输出示例：

```
fixture checks: 571, failures: 0, skipped: 1
=== MUTATION SWEEP: 44 passed, 0 failed ===
=== COMPAT HARNESS: 82/82 passed, 0 failed ===
```

## 评测

skill 的效果用独立 lab 测量，不靠自述（模型 `biklimax/qwen3.8_27b`，compliance 任务族）：

```
arm              pass   Wilson 95% CI      mean wall
bare             0/9    [0.00, 0.30]       ~3 min
full_forced      3/9    [0.12, 0.65]       ~41 min   （仅文本注入，无插件）
full_deployed    9/9    [0.70, 1.00]       ~23 min   （产品形态：文本 + gate/audit 插件）
```

部署形态在 9/9 运行中被 gate 插件实际拦截并驱动改正（28 次拦截，插件体检表见 `tests/eval/g3/v2fix_summary.json` 的 `gate_ledger`）。样本量小，以上为方向性结果（directional），不构成显著性宣称。首版战役曾得 50%，复核确认 4 个失败全部是评分器形态税（复数 criteria / ASCII 乘号），修复口径与复跑数据见报告 §8/§9。

设计与口径：

- `docs/EVAL_V2_PREREG.md`：产品形态评测（规则加插件）的预注册设计
- `docs/EVAL_G3_PILOT_REPORT.md`：全部战役结果与失效分析（§7 文本层、§8 产品层，含事故记录）
- `docs/EVAL_VALIDITY.md`：测量有效性（隐藏测试三向门、反伪造）
- `docs/REPLICATION.md`：复现条件；当前为单操作者，无独立复现

## 文件结构

```
vibeweaver/
├── SKILL.md                      # 绑定契约与路由器
├── COMPLETION_GATE.md            # 完工输出与证据门禁协议
├── TESTING_PROTOCOLS.md          # 修复循环、调试、覆盖纪律
├── REFERENCE.md                  # 工作流全文与反模式
├── WORKFLOWS_EXTENDED.md         # 审计、部署、运维工作流
├── ENGINEERING_STD.md            # 工程标准
├── VERIFICATION_UPGRADES.md      # 验证升级条款（COV 系列）
├── bootstrap.md                  # 会话入口指针（1–2 KB）
├── APPENDIX.md / MEMORY_RULES.md / MEMORY_TEMPLATES.md / CODING_PRINCIPLES.md
├── vibeweaver-gate.js            # 门禁插件
├── vibeweaver-audit.js           # 审计插件
├── scripts/                      # assert_artifacts.py、install.py、评测 harness 等
├── profiles/core/                # 精简档（仅 SKILL.md）
├── docs/                         # 设计文档、评测报告、QUICKSTART 等
├── tests/                        # 回归测试与验证日志
└── install.sh / install.bat
```

## 文档

- 上手与排障：`docs/QUICKSTART.md`、`docs/TROUBLESHOOTING.md`
- 迁移：`docs/MIGRATION.md`
- 安全与治理：`docs/SECURITY.md`、`docs/GOVERNANCE.md`
- 信任模型与 TCB 边界：`docs/TRUST_MODEL.md`
- 贡献：`docs/CONTRIBUTING.md`

## 贡献

开发环境、测试要求与评审流程见 `docs/CONTRIBUTING.md`。

## 变更记录

完整历史见 [CHANGELOG.md](CHANGELOG.md)。

## 许可

MIT，全文见 [LICENSE](LICENSE)。
