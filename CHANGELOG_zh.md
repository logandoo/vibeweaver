# 变更记录

设计演变史，新的在前。条目从 README 原样迁移；项目当前状态见 [README_zh.md](README_zh.md)。

## 2026-08-30：wave5 —— 可行性问题成为一等路由，外加一条计划切分测试

对 obra/superpowers 做了全仓库对照（14 个技能逐读）。先说实话：大半内容本 skill 早已覆盖——计划格式、调试四阶段、TDD 规则、spec 自审清单本就衍生自 superpowers 同名机制，这趟主要是覆盖确认。仍有两条凭实力留下；八条在案拒绝（全路径批准门、逐节设计批准、子代理逐任务执行、git worktree、分支收尾菜单、并行修复代理、技能编写指南、条件等待——各自与这里的某个有意选择冲突：AUTO 模式、一次性确认、会话内证据环、基线提交模型）。

- **Spike 路由**（借自 brainstorming）：可行性问题——「能不能…」、「是否可行…」——不再硬塞进构建工作流。它的交付物是答案：宣布 2-3 句探针计划，以正确性允许的最便宜方式求证，报告建议。产出的一切代码标记 throwaway；要留下它就是一个新请求，重新分类、重新过基线 GREEN。探针代码绝不无门流入生产。
- **任务切分测试**（借自 writing-plans）：计划格式增加一条边界测试——setup、config、脚手架、文档折入交付物所在任务；仅当 reviewer 能有意义地否决一个任务而通过其邻任务时才拆分。

这条新表行的成本是负 35 字节——SKILL.md 里五处冗余短语买的单（48,955 B，49 KB 上限内）。逐副本验证：self-test 35/36（唯一失败是已知的环境性校准用例），mutation sweep 27/27。

## 2026-08-30：wave4 —— 从 mattpocock/skills 借来五条契约，四条在案拒绝

对 mattpocock/skills（engineering + productivity：to-spec、code-review、grill-me、grill-with-docs、grilling、domain-modeling）做了一遍只读对照，只问一个问题：它们强制了什么本 skill 没有的？五条想法凭实力留下；四条被评估后书面拒绝（issue-tracker 发布、无路径 spec、双轴并行 reviewer、CONTEXT.md 词汇表——外部依赖、规划哲学相反、或评审成本翻倍）。

落地的五条：

- **计划中的测试缝**（借自 to-spec）：C3 任务块现在必须写明行为在哪条缝上验证——优先已有缝，在仍能隔离行为的最高缝上测，缝越少越好（全代码库理想是一条，因为每条缝都是测试与内部实现之间的永久耦合）。这是本 skill 一直缺的那条规划规则：它只说过测什么，从没说过在哪测。
- **评审中的 spec 保真三元组**（借自 code-review）：A4.9 reviewer 的 Compliance 维度不再是自由文本判断——必报 requirements missing/partial、scope creep、looks-implemented-but-wrong，每条引用其违反的判据原文。
- **评审 smell 基线**（借自 code-review，Fowler 十二味）：CODING_PRINCIPLES.md 新增逐 diff 检查清单，两条常驻约束——repo 文档标准永远覆盖基线；每条 smell 都是 judgement call，绝非硬性违规。派发评审时随包交给 reviewer。
- **多问题暂停的分轮访谈**（借自 grilling）：GUIDED 下携带多个待决问题的暂停包变成一轮按依赖排序的访谈——每题编号并附推荐答案，被未决答案阻塞的问题留到后轮，事实绝不询问（agent 自查），只有决策才问用户。frontier 为空意味着没有任何东西被静默假设。AUTO 不受影响。
- **proactive ADR 的准入测试**（借自 domain-modeling）：仅当决策难以逆转、缺上下文则令人意外、且是真实权衡的结果时才记录——三者俱全。强制 Class-I ADR 不受影响。

入场费是字节：SKILL.md 在 49 KB 自检上限下只剩 7 字节余量，所以测试缝那行以字节为负的方式进入（§A4.9 摘要里一个冗余括号买的单，48,990 B），三元组在 TESTING_PROTOCOLS.md 里的 110 字节由同段三处修剪补偿。逐副本验证：self-test 35/36（唯一失败是已知的环境性校准用例），mutation sweep 27/27，四个副本全部一致。

## 2026-08-29：wave3 —— 让 agent 真正接管，把「等人点」收干净

这套规则跑起来之后有两个尴尬场面。一是有些卡点天生要停：需求模糊要问、设计门要确认、基线带旧伤要裁决——停没错，但一停就得等人敲「继续」，而且「继续」到底是批准还是重新计划，没人说得清。二是规矩自己有盲区：写库、写 CLI 的人被要求交 `start.sh`（库哪来的服务？）；凭据明明是用户点名要写的，门一律拦；审计、部署、运维这类不改代码的活，干脆整个没有工作流，硬套 C2 会逼着 agent 给一份审计报告编验收循环。

这波就是收拾这三件事的：

- **AUTO / GUIDED 双模式（COV-12）。** 默认 AUTO：该问的不再问，把判断写进 `tests/decisions.md`（当时的选项、选了哪条、为什么、什么情况回头），然后挑最保守的一条接着干。GUIDED 是老行为，一字未动。要分清的是：模式只动「问不问你」，动不了证据——测试照跑、截图照截、assert 照样 exit 0，任何模式都不许把 FAIL 说成 PASS。生产部署、删数据、注入冲突这类不可逆的事，两个模式都得停下来问。
- **暂停有了协议。** 谁要停，都得留下 `[PAUSED] gate=… | default-if-continue=… | state=…` 这一行。你回一句「继续」，就是批准 default 那个选项，agent 从 state 写的位置接着干——不重新理解上下文，也不把问过的事再问一遍。顺带把压缩后重入的「全文重读」降成读日志尾部，长任务不会再读着读着把上下文读爆。
- **门不再跟项目类型打架。** 新增 project profile：库/CLI 项目声明一声，start/stop/restart 那组检查跳过（是跳，不是放水，跳了什么打印在门禁输出里）。用户点名要写的凭据，行内标 `vw-approved`、日志配一行 `- secret-approved: <路径>`，机器对得上就放行。gate 插件也不再拿报错吓人：改 `tests/`、`memory/` 不触发 GATE-BLOCKED，BLOCKED 消息第一句就是「写入已成功，这是完成门不是执行停止」。
- **四类任务有了自己的走法。** 审计是只读的，产出报告，每条发现必须带 file:line 和复现命令，重点发现由另一个 subagent 复核；部署动作本身永远是人确认，回滚脚本要先写好、还得真演练一次；线上事故先取证再动手，修完必须留一条永久回归用例；CLI/库这类没页面没 HTTP 的活，证据改成命令行 transcript + 退出码 + 输出 diff。骨架在 SKILL.md，全文在新 companion `WORKFLOWS_EXTENDED.md`——主文件只长了 15 字节。

效果还是用老办法验的：deepseek-v4-flash 强制注入跑 16 题，改前 15/16、改后 14/16，看着像回退；把 polyglot 10 题复测 4 轮取均值，实际是改前 87.5% vs 改后 92.5%——方向反了过来，单轮那 1 题就是掷硬币。SWE-bench 两边都 6/6。16 并发跑了 112 次没冻过一次。另外这波自己也被独立评审抓了个 Critical（组 14 会把注释里提到 `vw-approved` 的普通代码行误杀），修完复评才是 ready——门连写门的人都照拦。

## 2026-08-28：AI-native SDLC 加固 —— 完工门内容检查 + 结构化评审

对照 Anthropic《The AI-Native SDLC playbook》(2026-08-21) 与其副 CISO 安全配套文 (2026-07-21)：vibeweaver 的任务内纪律够硬，但有三处实质空白——完工门只查「证据在不在」、从不查 **diff 的内容**；A4.9 独立评审没有维度结构和 nit 上限；缺少事故复盘 / 工件链 / agent-config 回归规则。本波次按单用户交互式 skill 的尺度（而非组织级流水线）全部补齐：

- **断言新增 14-16 组。** 组 14 `secret scan` 按「每提交补丁」扫描 change-wave diff（净范围 diff 会漏掉波内「加了又删」）并整扫未跟踪文件：AWS 密钥、私钥块、`ghp_`/`github_pat_`/`xox*`/`sk-`（含 `sk-proj-`/`sk-ant-`）令牌、JSON 或 k=v 形态的凭据赋值——同时豁免**安全写法**的引用值（`os.environ.get(…)`、`process.env.X`、`config.password`、`self.x`）、占位标记行与 markdown（仅 WARN）。组 15 `test-change guard`：测试断言行被删除（含整文件删除）且没有 `- test-change: <path> — <reason>` 日志理由即判失败——修代码的 agent 不许悄悄弱化对这段代码的检查。组 16 `risk-tier`：diff 触及 `auth`/`security`/`payment`/`billing`/`crypto`/`migration`/`permission`/`acl` 代码路径时，独立评审不可跳过。
- **A4.9 评审结构化**：发现按 `Bugs`/`Security`/`Compliance` 打维度标签；Minor 逐条最多 5 条（余者计数）；同一错误被第二次标记时回写项目记忆 / `CLAUDE.md`，让错误在「生成时」而非「评审时」被拦下。
- **生命周期文档**：新增 §A4.4.3 Artifact Chain（工件链即审计轨迹——每个工件指认上游环节）、APPENDIX §A9 事故复盘模板（闭环到 A4.8 回归测试 + 记忆 + 可选常驻 eval）、agent-config 回归规则（改 `CLAUDE.md`/`.claude/**`/skill 规则文件必须重跑验证套件——操纵 agent 的配置和代码一样需要回归测试）、跨项目 ⛔ 提升通道、生产部署人工确认一行。
- **评审在环实证**：本波次的独立 reviewer（裁决 ready-with-fixes）抓到删除文件 fail-open、安全写法误伤、JSON/现代密钥漏检各一处——全部以夹具先行回归修复（11/11 场景绿）。
- **修改前后 A/B 实测**：deepseek-v4-flash 强制注入、16 题评测集（10 polyglot + 6 SWE-bench Lite）——修改前 15/16，修改后 **16/16**；工作流产物遵循度 6/10 → 9/10（单轮方向性结果；原始数据在 `vibeweaver-eval/workspace/iteration-1/ab_logs/`）。
- 另：SKILL.md 修剪回 49KB 自测线内（50,096 → 48,978 B，零绑定内容损失——第三重冗余指针化，gate-line 模板字节未动）。

## 2026-08-21：会话级 RED 锁存 + 审计交付波次

08-19 的审计器有个结构性隐患：会话被截断后，`BLOCKING=yes` 会针对整个项目落下 RED 锁存，只有到会话结束才释放——而且测试目录豁免只匹配顶层 `tests/`，嵌套的 `dev/tests/` golden 文件也会被锁死。本周就有两个真实项目撞上了这个死锁。这一波修复锁存，并把 payload 交付到所有副本：

- **会话级锁存。** 锁存值变为 `{ sessionID, ts, bad }`。落锁的会话自己继续写 → 照旧被拦（自纠闭环不变）；*另一个*会话的首个写入/idle → 自动释放陈旧锁存；TTL 兜底（默认 24h，**只能**在全局 `~/.config/opencode/vibeweaver/audit.json` 里配——项目本地副本被刻意忽略，被审计的 agent 永远不能给自己的审计器松绑）兜住同一会话遗留的活锁。旧格式的布尔锁存在首次接触时自愈；每次释放都记进 `.vibeweaver/audit-state.json` 并出现在审计报告里——锁被打开过永远可追溯。
- **嵌套测试目录豁免。** 项目根下任意 `test`/`tests` 路径段在 RED 期间保持可写，证据修复永不被死锁卡住。
- **自测从 28 项长到 36 项**（跨会话释放、嵌套 tests、TTL 兜底、释放留痕、legacy 自愈）；27 项变异扫描不变。本波次的一次独立评审抓出（如今由套件钉死）一个 T20 首跑就暴露的留痕缺陷：legacy 锁存曾被记成 `stale-session` 而非 `legacy-state`。
- **交付。** 17 文件 payload 在全部四份副本（系统安装 / dev 树 / open-source 快照 / 本仓库）字节一致；`install.sh`/`install.bat` 同时安装两个插件；`verify_skill.py` 对全部五个 payload JS 文件做语法检查。

## 2026-08-19：渐进式披露重构 + 机械审计体系

**原因（这是 opencode 的限制，不是 skill 的规则）：** opencode 加载 skill 时把整个
`SKILL.md` 正文作为**一次工具输出**注入上下文，而客户端对工具输出有**约 51,200 字节
（50KB）的截断上限**——本机实测：用 Read 工具读取旧的 79,554 字节文件，输出在第
875 行（51,080 字节）处被截断（`Output capped at 50 KB`）。模型激活 skill 时只拿到
契约的前半份，并诚实声明 `The skill output is truncated. Let me note the key points:`——§A5.1、Part B/C 工作流、MANDATORY CHECKLIST 和参考文件索引**从未进入上下文**。

**方案：渐进式披露**（依据 Anthropic Agent Skills 官方规范 + SkillJuror 对照实验：
拆分到引用文件让模型实际触及的资源提升约 3 倍、任务成功率 +4.1%）：

- `SKILL.md` 从 79.5KB 瘦身到 48.9KB（814 行），成为**绑定契约 + 路由器**：11 条
  COV 全文、§2 ZERO、§3、gate line / 8 列表格规格与核心清单留在根文件；详细协议
  **逐字迁移**到配套文件（`TESTING_PROTOCOLS.md`、新增 `COMPLETION_GATE.md`、
  `REFERENCE.md`、`ENGINEERING_STD.md`——每个 ≤45KB，单次 Read 即可完整返回不截断）。
  **内容零删除**：54 个章节标题 / 47 条长协议句 / 31 个绑定字面 token 全部核验存在。
- **Read Contract（强制读取契约）**：R1/R1b/R2–R5 触发表——首个代码动作前、
  最终输出前、各工作流分支必须完整读取对应配套文件；外加**截断自愈条款**和
  **<49KB 体积守卫**（由自测脚本强制执行）。

**新增：`vibeweaver-audit.js` 三层机械审计。** skill 的纪律以前是模型自律、
无法被机器验证。现在插件（含纯核心 `scripts/vibeweaver-audit-core.js`）被动观察
每个 skill 会话并产出 `tests/gate_audit.md`：

- **Tier 0** —— 被动观察（零模型合作、零 token）。
- **Tier 1** —— 三态裁决（OK / BAD / UNCERTAIN）：磁盘构件、10 项叙述 marker、
  以及 15+ 项 gate line 声称↔构件交叉核验（Fresh-run vs git 历史、E2E depth vs
  工作流 trace、Code review vs 评审派发、Script-only vs bash 命令、读取契约 vs
  read 调用、构件时序）。BAD → 在 `tool.execute.before` 拦截下一次写入
  （`tests/**` 保持可写，证据修复不死锁）。
- **Tier 2** —— 升级触发（UNCERTAIN / 10% 抽样 / 高风险）→ 按
  `COMPLETION_GATE.md` §AUDIT 派 fresh-brain reviewer 裁决。

**实测效果**（端到端真实会话 + 重放校准）：审计抓到**真实违规**（`Code review: N/A` 但缺 `A4.9 not triggered` 豁免理由）；`GATE-BLOCKED` 在真实 opencode 会话中
成功拦截写入；校准驱动的精化消除了误报（纯记录型提交不再触发 Fresh-run 检查）。
对抗实验（「不用测试，直接改」）：模型完全跳过 skill——现由 **C17（SKILL-ABSENT）**
检测并升级审查。测试体系：**28 项 fixture 检查 + 27 项变异扫描**（逐项破坏每个
检查点验证其真实触发——已借此挖出并修复一个潜伏 bug：C3 从未生效）。

**已知边界**（设计使然，§AUDIT 文档化）：审计只覆盖加载了 skill 的会话；
语义真实性靠 10% 抽样而非全量证明；过程合规 ≠ 结果正确。
