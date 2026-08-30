# Vibeweaver

[![verify](https://github.com/logandoo/vibeweaver/actions/workflows/verify.yml/badge.svg)](https://github.com/logandoo/vibeweaver/actions/workflows/verify.yml)

Vibeweaver 与其说是一个 skill，不如说是一套面向 vibe-coding 的编码纪律，为 opencode 打包。

当模型写码能力不再构成瓶颈，开发者的核心工作就从亲自写代码转向组织和管理开发过程。benchmark 分数一路走高，中大型项目上的实际体验却始终难以令人满意。问题不在模型能力，而在开发过程中没被明确定义的两件事：流程和规范。agent 有能力，缺的是对「完成任务」的定义。Vibeweaver 用一份显式契约约束 coding agent 的开发流程，把模型能力转化为中大型项目上稳定、可信的交付。

目前项目仅针对 opencode 做了优化，另外开源了 DeepSeek Harness 版本的插件 [vibeweaver-dsh](https://github.com/logandoo/vibeweaver-dsh)。至于 Codex 和 Claude Code，没用过，也没打算用，不知道。感兴趣可以自行 fork。

## 它到底在干什么

Vibeweaver 是一份契约，不是一套方法论。它盯住编码 agent 最臭的毛病：没有证据就宣布「done」，然后用规则把它堵死：

- **NO TEST, NO DONE**：每次代码改动之后，必须真的跑过测试，并且留下磁盘上的证据（日志文件、截图、操作录屏、页面音频）。「能编译」不算证据。
- **测试优先，没有例外**：有逻辑的代码一律 RED→GREEN：先写一个注定失败的测试，*亲眼看着它失败*（失败输出要贴进 `tests/verification_log.md`），再写让它通过的最小实现。第一次跑就过的测试说明不了任何问题，它测的可能是完全错误的东西。回归测试必须走完完整的「还原并失败」流程才算数：写测试 → 有修复时跑（过）→ 还原修复 → 跑（必须挂）→ 恢复修复 → 跑（过）。
- **API 文档驱动的后端测试**：纯后端改动走这个循环：更新 API 文档 → 文档与代码一致性核对（只核一次）→ **照着文档写测试用例，不照着实现写** → 用 httpx 跑「测试→修→再测」直到全绿。跨接口的改动还必须写真实 HTTP 的工作流场景，痕迹落盘（`tests/workflows/*.trace.log`）；直接调 service 层不算 E2E，不算数。
- **自动启动的验证循环**：改动一碰到运行时行为，agent 会自动进入 `Act → Capture → Verify → Fix → Log`。截图的评分交给任务开始时探针选定的验证器（三段树，见下文「和 mm-sensor 怎么配合」）：model-native 自读要按 §A4.1.1 协议，装了 [mm-sensor](https://github.com/logandoo/mm-sensor) 则由它独立打分，写代码的不能给自己的作业打分；验证器支持视频/音频就一起录，支持什么模式由能力检测决定，不靠猜。
- **脚本化管理生命周期**：前端构建、服务启停一律走 `script/` 目录下的脚本。裸 `npm run build`、`vite`、`npm start`、`uvicorn` 全部禁止。停服务必须用 `.pid` 文件 + `kill $(cat .pid)`，在共享机器上 `pkill -f "uvicorn"` 会顺带杀掉同事的服务。
- **先研究再动手**：任何任务的第一步都是拆解问题（有不清楚的就停下来问，一次一个问题，别猜）、联网检索现成方案（exa MCP + Context7），评估至少两种方案再写代码。除非没有网络或只是琐碎的 typo/配置修改，这一条都必须执行。背后的哲学很简单：**太阳底下没有新鲜事**。这类问题大概率早有人解过；如果真搜遍全网都找不到先例，那说明这活儿新到不该由我们干。
- **项目记忆**：说它是整套系统里最重要的一块也不过分，因为 opencode **没有原生的记忆系统**：每场会话都是从头开始的新脑子。vibeweaver 用文件和规则硬造了一个：索引 + 主题文件、信任分级（⛔ 禁止 / ❌ 失败 / ✅ 已验证 / ⏳ 未验证）、修 bug 的状态机。完整机制见下文。
- **循环有上限**：每个验证循环都被约束：单个子问题最多 `cap=5` 次迭代，`stall=3×`（同一标准连续失败三次就停下、换方向、把死路记进 memory）。不会陷入无限修复循环。

完整版还覆盖新项目脚手架（先出设计文档：FLOW / PAGE / DATABASE / BACKEND）、配置管理、验收清单，以及一张 8 列的完工表格。

## 安装

```bash
git clone https://github.com/logandoo/vibeweaver && cp -r vibeweaver/vibeweaver ~/.config/opencode/skills/vibeweaver
# 或者，在仓库本地副本里：
./install.sh    # Linux/macOS
install.bat     # Windows
```

重启 opencode。要求构建、修改、调试或部署任何东西时，skill 会自动触发。想连执行层插件一起要（stop hook + 完工审计器，`install.sh`/`install.bat` 本来就会装全）：

```bash
cp ~/.config/opencode/skills/vibeweaver/vibeweaver-gate.js ~/.config/opencode/plugins/
cp ~/.config/opencode/skills/vibeweaver/vibeweaver-audit.js ~/.config/opencode/plugins/
```

（嫌麻烦只装 skill 不装拦截插件也行。插件是执行层，skill 是指令层，两者独立工作。）

可选配件里，Playwright 和 [mm-sensor](https://github.com/logandoo/mm-sensor) 是其中真正建议装的两个：它们是一对设计好的搭档，少了它们验证循环会明显变弱（从独立打分退化成自己给自己打分）。另外还有用：ffmpeg（视频转码）、exa MCP + Context7（研究）。缺了这些 skill 照样跑，只是证据采得多不多、查得独不独立的问题。

跑起来之后，一个任务结束时磁盘上能看到的东西：`tests/verification_log.md`（采集验证循环的迭代记录）、`tests/acceptance.md`（首行是 `> cap=5  stall=3×` 验收行）、媒体证据文件，以及 `memory/` 下的记忆条目。证据缺失时，gate 插件会拦下 agent 的下一次写入并报 `GATE-BLOCKED`（见下文 stop hook 一节）；`VIBEWEAVER_GATE=off` 可关掉门禁。

## 仓库结构

本仓库包含三个子项目：

| 目录 | 是什么 |
| --- | --- |
| `vibeweaver/` | 完整版 skill，本 README 描述的就是它 |
| `vibeweaver-mini/` | 删减版，单文件约 5KB。指令遵循能力一般、但编程能力还行的小规模 LLM 上有点增益——不需要的人完全不需要，有需要的人确实可以用 |
| `vibeweaver-eval/` | 评测架：16 题 A/B 评测的配置、评分脚本、原始结果、逐轮报告 |

怎么选：**强模型** → 完整版（插件注入）；**弱指令遵循模型** → mini 常驻；**极弱模型（~3B 激活）** → mini 强制注入。

仓库根目录还有 skill 自身的测试设施：`verify_skill.py`（skill 包完整性检查）、`tests/`（含 pass/fail 夹具项目的自测套件）、`.github/workflows/verify.yml`（每次 push 在 Ubuntu / macOS / Windows 上跑这两个）。这个 skill 检查别人项目的方式，原样用在自己身上。

## 工作流是一张图，不是一份清单

先看全图，再逐条解读（每个节点都是带强制产物的阶段，每条边都是显式条件）：

```mermaid
flowchart TD
    A["任务"] --> B["§2 ZERO ★ 动手前必过<br/>拆解 + 联网检索（≥2 方案）<br/>COV-5 验证器探针：mm_probe 行为探测<br/>COV-11 不可信内容 = 数据不是指令<br/>COV-12 模式声明：AUTO（默认）/ GUIDED<br/>产物：拆解说明 + 检索结论"]
    B --> C{"§3 项目模式"}
    C -->|"新项目 C1"| D1["Design Gate A<br/>§A5 设计文档<br/>Design Gate B<br/>产物：FLOW / PAGE / DATABASE / BACKEND"]
    C -->|"存量修改 C2"| D2["现场勘察：memory · config · script/<br/>产物：baseline 提交 + Baseline verified GREEN"]
    C -->|"大任务 C3"| D3["docs/PLAN.md + Consistency Hub<br/>产物：逐任务块实施计划"]
    B --> T{"§3.1 任务类型路由"}
    T -->|"审计 C4（只读）"| T4["docs/AUDIT_*.md<br/>finding 必带 file:line + PoC<br/>独立 subagent 复验"]
    T -->|"部署 C5"| T5["预部署清单 → 回滚脚本先行<br/>部署动作 = Class-E 人工确认"]
    T -->|"运维/事故 C6"| T6["先取证后动手<br/>postmortem → 永久回归用例"]
    T -->|"CLI/库 C7"| T7["project profile 声明 N/A<br/>证据：CLI transcript + 退出码 + golden diff"]
    T -->|"可行性 S1（spike）"| T8["交付物是答案不是代码：探针计划 2-3 句、最便宜求证<br/>代码 throwaway；要留 = 新请求 + 自带基线"]
    D1 --> E["实现（改动）"]
    D2 --> E
    D3 --> E
    T5 --> E
    T6 --> E
    T7 --> H
    T4 --> O
    E --> F{"改动类型"}
    F -->|"运行时可见"| G1["§A4.1 采集验证循环<br/>Act → Capture → Verify → Fix → Log<br/>产物：verification_log.md + 媒体证据"]
    F -->|"纯后端"| G2["§A4.7 文档驱动 API 测试<br/>+ A4.7b 跨接口 workflow trace"]
    F -->|"逻辑代码"| G3["§A4.8 TDD<br/>先 RED 证据，再 GREEN 实现"]
    G1 --> H{"验收全绿？"}
    G2 --> H
    G3 --> H
    H -->|"否 · cap=5 内"| E
    H -->|"stall=3× / cap=5"| I["§A4.10 参数化逃生<br/>换方向 · fresh-brain 重试"]
    I --> E
    H -->|"是"| J{"COV-8 大改动？"}
    J -->|"是"| K["§A4.9 独立评审派发<br/>产物：评审记录 + 裁定"]
    K --> L["§A4.4 完工门<br/>收敛行 + 8 列表格<br/>assert_artifacts.py exit 0"]
    J -->|"否"| L
    L --> M["Memory Gate<br/>A7.9 记忆写入 + A7.10 通过"]
    M --> N{"插件审计 Tier 0/1/2"}
    N -->|"BAD → GATE-BLOCKED / RED 锁存"| E
    N -->|"OK"| O["交付（C4 审计报告在此汇合）"]
```

- **节点 = 带强制产物的阶段。** ZERO（拆解 + 联网检索）→ 项目模式判定 → 设计门 → 实现 → 验证循环 → 独立评审派发 → 完工表格。「模型说完了」不算一个阶段完成；它要求的产物真的落在磁盘上，才算完。
- **边 = 显式条件，不是模型心情。** 新项目走一条流程，存量修改走另一条；验证器能力探测把采集/评分集分支成四种模态；纯后端改动把浏览器循环替换成文档驱动的 API 测试循环。
- **环路天生有界。** 每个循环共用同一份终止契约（`cap=5` 次迭代/子问题，`stall=3×`），而且停止条件由用户*最先*写下来，所以这张图保证有出口。
- **遍历是软的，卡点是硬的。** 模型靠解释自然语言来走图，这部分依然是软的。但每个卡点的条件都可以机器校验：最终回答里的字面 token、被 `tests/assert_artifacts.py` 逐字节核对的磁盘证据，以及（装了插件时）一个工具级钩子：任何一个卡点没转过，agent 自己的写入就会被拦住，想走也走不动。

这就是它为什么是状态机：当前阶段永远可以从文件里验证出来，而且没有证据就不允许声明任何状态转移。下面的 stop hook 是同一个思路往下一层：图的最后一个卡点，由 opencode 本身执行，而不是由模型执行。

## Stop Hook：词不管用，就上工具层的门禁

提示词只是建议。一个刚被告知「NO TEST, NO DONE」的模型，依然有可能一个测试都不写就宣布完工。为了解决这种情况，我专门添加了一个 stop hook 插件。

vibeweaver 附带的配套插件 `vibeweaver-gate`，在**工具层**机械地强制执行证据规则：

- 它挂在 opencode 的 `tool.execute.after` 钩子上，拦截每一次 `write`/`edit`。如果项目处于 vibeweaver 激活态（有 `tests/verification_log.md`），插件就运行项目的 `tests/assert_artifacts.py`（四种 flag 组合全试一遍）。
- 如果验证证据缺失或造假：日志里没有迭代记录、`acceptance.md` 首行没有 `> cap=5  stall=3×`、被引用的截图/媒体文件不存在或零字节，插件会**向工具调用结果里抛一个 `GATE-BLOCKED` 错误**。agent 走不动了，它自己的工具调用会报错返回。这就是 stop hook 的全部意义：它会阻止模型自顾自完工。
- 结构性缺失（`memory/`、设计文档、README）只追加 `GATE-WARNING`，不阻塞。
- 还有个 `session.idle` 兜底：会话在证据还欠着的时候就安静下来，插件会往 opencode 日志写一条 `warn`。
- 实在不喜欢这个机制：`VIBEWEAVER_GATE=off` 关掉它。

这个拦截刻意做成可复查而非死停：把证据补齐，下一次 `write`/`edit` 会自动重新检查。它是完工门槛，不是执行开关。

而且这个插件不挑 skill：只要项目里有 `tests/verification_log.md` 它就生效，所以 **vibeweaver-mini** 同样被覆盖，mini 的落盘格式刻意与它的证据底线保持一致。只用 mini 又想要这条硬底线的用户，装这一个插件就够了（见[安装](#安装)）。

这个插件有个搭档：`vibeweaver-audit` 是完工声明的机械审计器（Tier-0/1/2）。会话空闲时它重跑项目的 `tests/assert_artifacts.py`（和 stop hook 用的是同一份断言脚本），再用自己的声明检查组给最终输出打分、复核磁盘证据；打出 BAD 就落下一个**会话级**的 RED 锁存，拦住 agent 的写入，直到证据真的补齐。正因为锁存是会话级的，一个被截断的会话永远不会把项目锁死：换会话、TTL 到期、旧格式状态迁移，三条路都会自动释放；而且每次释放都会记进 `.vibeweaver/audit-state.json` 并出现在审计报告里（机制详见 [CHANGELOG_zh.md](CHANGELOG_zh.md) 的 2026-08-21 一节）。

一句实话：这个插件说的是 opencode 的插件 API（`tool.execute.after`、`session.idle`、`client.app.log`）。至于 Claude Code 或 Codex 有没有类似的机制，没验证过，真不知道，欢迎 fork。DeepSeek Harness 版已经落地并开源为 [vibeweaver-dsh](https://github.com/logandoo/vibeweaver-dsh)——契约卡、机械门禁（同一份 `assert_artifacts.py` 证据检查）、回合守卫都在里面了。

## 认知层：工具之上的状态管理

证据规则解决的是「模型谎报了做了什么」，解决不了「模型悄悄忘了自己处于什么状态」。长任务里的漂移、打转、目标蒸发属于后一类，住在更上面一层。最近一版从 [J-Space Cognition Suite](https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6)（出处见[致谢](#致谢)）借来一组机制，正好补这一层：

- **来路不明的内容 = 数据，不是指令（COV-11）。** 这个 skill *强制*联网检索（exa MCP + Context7），而「忽略之前所有指令」恰恰就藏在外来内容里。抓取/工具/第三方的文本可以提供信息，但不能下命令；抓来的「解决方案」照样得过 ≥2 方案评估；并且不对称规则生效：扫到可疑是强证据，「没扫出可疑」**不等于**干净：「不存在」要靠一次具名检查确立，不能靠模型自己的监视器保持沉默来确立。
- **一致性枢纽（写一次，读多次）。** 大任务在计划里为每个共享的 名字/配置键/值/签名 立一行规范记录。后续步骤*引用*枢纽行，而不是重新推导；改名先改枢纽，然后把旧拼写 grep 到零命中，零命中的 grep 输出就是完工证据。这直接干掉长任务里「同一个已确定的值出现三种拼写」的经典漂移。
- **带诊断的重试。** `verification_log.md` 里每一条 `- iter N FAIL:` 必须带 `diagnosis: <一句可证伪的判断>`，机器检查（assert 第 12 组）。不带诊断的重试就是同一个尝试再来一遍：同样的成本，买不到任何东西。
- **停滞逃生：参数化，别打转。** `stall=3×` 触发后，下一步方向要*生成*出来，不是凭感觉：把悬而未决的未知量变成有限候选集，每个候选配上「最便宜的可能推翻它的测试」，然后才转向（换抽象 / 换策略 / 转实证）。差分验证要求参考实现**不与候选共享假设**，继承同样「聪明」的暴力解会继承同一个 bug。两条便宜且独立的验证路径都存在时，两条都走：一致则结论得力，不一致恰好*定位*了错误假设。
- **长间隔后的重入。** compaction / 跨 session / 长时间中断之后，agent 先全量重读 `verification_log.md`、逐行重读目标、重读契约，然后说出恢复后的第一步动作，按这个顺序，然后再碰工作（§3.3）。
- **停滞观测机械化。** 插件现在维护 `.vibeweaver/state.json`（原子写）：同一文件被改 3 次、中间没有新增 PASS 条目 → 触发一条指向逃生协议的 `GATE-WARNING`。`stall=3×` 以前是模型自己数的上限，现在插件也数。

顺便把 skill 自己宣讲的渐进披露纪律用到了它身上：约 120 行的内嵌断言脚本变成规范的 `scripts/assert_artifacts.py`，四个 后端/TDD/评审 协议移入 `TESTING_PROTOCOLS.md`；那次入口文件瘦身约 180 行，后续几轮拆分把入口进一步做到今天的约 813 行；上面每条新规则的成本是一行紧凑契约 + 一个指针。

## 记忆系统：opencode 会忘，文件不会

opencode 原生没有记忆。开一个新会话就是一颗新脑。它完全不记得三场会话前被否掉的那个 JWT 重构方案，也不记得上一个工程师为了登录的 bug 追了两天最后发现是 session TTL 不匹配。每场会话它都重新撞同一堵墙、重新提交同一个被否掉的方案。vibeweaver 用文件和规则自己造了一个：

- **索引 + 主题文件。** `memory/MEMORY.md` 是目录而不是内容本体（加载上限 200 行 / 25KB）。每条记忆单独放一个 `memory/*.md`，带 YAML frontmatter：类型（`user` / `feedback` / `project` / `reference` / `fix`）、状态、对应的 commit 哈希、引用的文件位置。
- **选择性召回，不是全量背诵。** 会话开始时先加载索引，再按请求里的关键词 grep 主题文件，只加载最相关的 3-5 条。记忆在动手前被检索，但绝不盲信：每条文件/行号引用都要对照当前代码验证，超过 14 天的条目会挂上「可能已过期」的警告。连 ✅ 已验证的条目也会自动过期：14 天没复核、或者引用的代码变了，就先降级回 ⏳ 待验证。
- **信任分级，因为记忆不等于事实。** ⛔ 禁止 = 被证明必失败的方法，不许再试。✅ 已验证 = 用户亲口确认过。⏳ 未验证 = agent 自己修的、测试通过了但没人确认，仅供参考，不是事实。❌ 失败 = 后来被证伪的 ⏳，跟 ⛔ 一样「不许再试」。
- **修 bug 的状态机。** agent 修完、测试过了 → 记成 ⏳（永远不许直接写 ✅，只有用户能验证）。同样的症状在下一个会话再出现 → 这条自动降级为 ❌，agent 必须换一个真正不同的方向。用户确认有效 → 升 ✅。同一问题失败三次以上 → 全部升级进 ⛔ 禁止文件，这个方向硬停。
- **每次会话必写，收尾必检。** 记忆写入是会话结束时的强制动作，完工表格之前还要过一道 Final Memory Gate。修复条目必须带上它所描述改动的 commit 哈希，以及考虑过但没走通的路和否掉的备选方案。以后的会话看一眼记忆、看一眼当时的代码，就省得再撞一次南墙。
- **两个作用域，合并加载。** 用户全局记忆（`~/.config/opencode/vibeweaver/memory/`）存跨项目的偏好和约定；项目本地记忆存一切项目专属的东西。会话开始时两个都加载，冲突时项目本地优先。
- **家务活。** 索引有整理触发线（150 行 / 20KB，或超过 15 个主题文件）：整理时 ⛔、✅、用户与反馈条目原样保留，过期的 ⏳ 被清掉；`.session-scratchpad.md` 用来跟踪难缠的多轮修复过程，写完正式记忆后删除。

一句话：这是个项目级的外挂持久记忆，算是个丐版记忆系统：用文件系统和规则，硬给没有记忆层的模型补上跨会话的「记得住」。

## 和 mm-sensor 怎么配合：搭档，不是对手

vibeweaver 和 [mm-sensor](https://github.com/logandoo/mm-sensor) 建议一起用。skill 中也专门做了 mm-sensor 的检测和调用。当然，真不想用也无所谓，不过效果会打点折扣，毕竟两个 skill 本来就是按一对设计的。分工如下：

- **验证器三段树（COV-5，行为探测，不靠自宣称）。** 任务开始时 vibeweaver 先跑自多模态行为探针 `scripts/mm_probe.py`：生成一张带 token 和颜色的探针图（`tests/probe_vision.png`），模型用 Read 读它并报告看到的 token+颜色，再 `--check` 校验：**PASS** → 宣布 `Verifier: model-native [image]`，模型按 §A4.1.1 视觉验证协议自读截图（观察前置 · 逐标准引证 · DOM/日志交叉核验 · UNCERTAIN=FAIL）；**FAIL** 且装了 mm-sensor → 宣布 `Verifier: mm-sensor [video+audio|video|image]`，独立打分；两者都没有 → `Verifier: direct read`（以 DOM/日志核验为主）。
- **vibeweaver 负责让证据存在。** 它的规则逼着 agent 真的把应用跑起来、用 Playwright 驱动、把截图/操作录屏/页面音频留在磁盘上。
- **mm-sensor 负责独立打分。** 写代码的和打分的是两个角色：mm-sensor 是验证器时，写代码的模型被明令禁止给自己的截图打分（自评即违规，没有例外）。只装 vibeweaver 时，模型过不了自多模态探针就退回「直接读图」的自评模式，弱一截，还得额外拿 DOM 和日志交叉核对。
- **能力检测决定采多少证据。** 任务开始时 vibeweaver 跑一次 `vision.py --probe`，问清楚 mm-sensor 背后的模型到底能感知什么。全模态模型拿到 [video+audio] 模式：Playwright 录下全流程视频、用 Web Audio 抓页面音频，外加一张终态截图。只认图的模型降级到 [video] 或 [image] 模式：跳过视频，或者回到纯截图循环。模式每任务固定一次，每份采集的文件都用 `vision.py --detail high` 评分。
- **如果系统环境不充分，也会降级运行。** 没有 ffmpeg → 直接用原始 webm 帧采样评分。模型听不了音频 → mm-sensor 明确报告跳过，循环继续用视频加截图跑。音频永远只是加分项，本身不构成验收标准。

一句话：vibeweaver 决定*该采什么、而且必须采*；验证器（model-native 或 mm-sensor）决定*证据到底说了什么*。

## 到底有没有用？

下面每张表都用同一种设置方式：

- **baseline**：完全不用 skill。
- **仅挂载**：skill 装好了、出现在 `available_skills` 里，模型自己决定要不要加载。它到底加载了没有，就是表里单列的**触发率**。
- **强制注入**：skill 全文塞进系统提示词，模型没得选。

### 评测是怎么设计的

下面的数字来自同一套固定、可复现的评测架（`vibeweaver-eval`）：

- **固定任务集**：每轮都是同样的 16 题：10 道 Aider polyglot + 6 道 SWE-bench Lite 真实仓库修 bug。同样的提示词、同样的评分，一轮接一轮。
- **隐藏测试评分**：polyglot 是 Exercism 风格，SWE-bench 带 FAIL_TO_PASS + P2P 回归保护。
- **隔离的组**：每组跑在独立的 XDG 配置目录里，组与组之间唯一的差别就是 skill（或者没有）。裸模型组就是**对照组**，其余各组是**实验组**。
- **入组前先过 gold 验证**：每个 SWE-bench 实例必须先通过「base 必挂、gold 必过」的验证，才有资格进评测集。
- **全程无人值守、脚本化**：`opencode run --auto`，评测架、配置、gold 校验、原始运行记录、评分脚本全部公开。

### 用前 / 用后：qwen3.6-35b-a3b（目前最弱的模型）

34.6B MoE / ~3B 激活，GGUF Q5 量化，llama.cpp 后端。这个模型在能力最低的一端把「体积→触发率」的规律砸碎了：

| 组 | 通过率（16 题） | 触发率 |
| --- | --- | --- |
| 裸模型（baseline） | 6/16 (37.5%) | — |
| mini，仅挂载 | 6/16 (37.5%) | 0/10 |
| 完整版，仅挂载 | 7/16 (43.8%) | 0/10 |
| **mini，强制注入** | **7/16 (43.8%)** | — |
| 完整版，强制注入 | 5/16 (31.3%) | — |

- 能力低于阈值后什么都不加载：mini 和完整版都是 0/10。
- 强制注入 mini 也没有任何提升：7/16 ≈ baseline。
- 强制注入完整版反而更糟了：5/16，SWE-bench 只剩 1/6，其中 5 次 `no diff produced`，71KB 规则淹没 3B 激活模型的上下文，它直接放弃。

### 用前 / 用后：qwen3.6-27B

| 组 | 通过率（16 题） | 触发率 |
| --- | --- | --- |
| 裸模型（baseline） | 7/16 (44%) | — |
| 完整版（71KB），仅挂载 | 6/16 (38%) | 0/16 |
| 完整版（改进描述），仅挂载 | 9/16 (56%) | 2/16 |
| 完整版，强制注入 | 9/16 (56%) | — |
| **mini，仅挂载** | **10/16 (62.5%)** | **10/16** |

这一轮就是 mini 版存在的全部理由：

- mini 干翻了强制注入的完整版（62.5% vs 56%），赢在它真的被*加载了*：一套模型愿意读且能记住的短规则，胜过一份它永远不打开的 71KB 巨著。
- 体积决定触发。 71KB → 0/16，mini → 10/16。

### 用前 / 用后：deepseek-v4-flash-0731

| 组 | 通过率（16 题） | 触发率 |
| --- | --- | --- |
| 裸模型（baseline） | 11/16 (68.8%) | — |
| 完整版，仅挂载 | 11/16 (68.8%) | 0/16 |
| mini，仅挂载 | 11/16 (68.8%) | 12/16 |
| **完整版，强制注入** | **14/16 (87.5%)** | — |

强模型自带这套纪律，mini 从这个档次的模型开始变得毫无增益。完整版的增益开始明显，但是模型自己永远不会去加载（仅挂载时 0/16），需要**强制注入**上下文。优势全在 polyglot：8/10 vs 5/10。

### 用前 / 用后：qwen3.8-27B

| 组 | 通过率（16 题） | 触发率 |
| --- | --- | --- |
| 裸模型（baseline） | 13/16 (81%) | — |
| mini，仅挂载 | 13/16 (81%) | 10/10（polyglot） |
| 完整版，仅挂载 | 15/16 (94%) | 12/16 |
| **完整版，强制注入** | **16/16 (100%)** | — |

两个发现：裸模型自己就变强了（vs qwen3.6 从 44% → 81%）；而且 3.8-27b 的主动加载能力强了很多：qwen3.8 有 12/16 次主动加载完整版，刷出这套评测的历史最高分。强制注入完整版后直接登顶：**16/16 满分，评测史上第一个满分轮**（polyglot 10/10 全部满分、SWE-bench 6/6）。但是这个满分的代价不小：均值 1820s/题 vs 自主的 518s（+251%），这就是「每道题都走完整验证循环」的价格。mini 和在 deepseek-v4-flash-0731 上一样没有价值。

### 四模型，一张表

| | qwen3.6-35b-a3b | qwen3.6-27B | deepseek-v4-flash-0731 | qwen3.8-27B |
| --- | --- | --- | --- | --- |
| 裸模型 | 6/16 (37.5%) | 7/16 (44%) | 11/16 (69%) | 13/16 (81%) |
| 完整版，仅挂载 | 7/16 (43.8%) | 9/16 (56%)† | 11/16 (69%) | 15/16 (94%) |
| 完整版，强制注入 | 5/16 (31.3%) | 9/16 (56%) | 14/16 (87.5%) | **16/16 (100%)** |
| mini，仅挂载 | 6/16 (37.5%) | 8-10/16（最好 62.5%） | 13/16 (81%)* | 13/16 (81%) |
| mini，强制注入 | 7/16 (43.8%) | 8/16 (50%) | — | — |
| 最优形态 | mini 强制 | mini 仅挂载 | 完整版强制 | **完整版强制** |

\* deepseek 的 mini：首跑 11/16，干净环境重跑 13/16，都在它 11/16 baseline 的噪声内。
† qwen3.6 的完整版：原版 6/16（从不加载）；9/16 是改进描述变体。

### Well, To be Honest

- 因为是 TDD 导向的 skill，所以会**疯狂消耗 token**。如果手头真有想要解决的问题，还是很建议试试；如果只是玩一玩 vibe-coding，这个 skill 倒也不显得那么重要。
- 模型换代还是比 skill 本身重要的多：qwen3.6 → qwen3.8 在没上任何 skill 的情况下就把裸模型从 44% 抬到 81%；**skill 的角色随模型翻转**：在 qwen3.6 上它*补上*缺失的纪律（mini 赢），在 qwen3.8 上它*强制*执行纪律（强制注入直接满分 16/16），在 deepseek 上只有强制使用完整版才有效，在 35b-a3b 这类模型上只有强制 mini 才有效。
- 16 题确实是小样本。 虽然每个任务都挺复杂，但不能完全排除某一题「恰好可以搞定」或「恰好搞不定」、刚好碰上模型擅长点和不擅长点的情况。
- 每组每轮只跑了一次。 qwen3.8 一组要 40-60 分钟；llama.cpp 上的 35b-a3b 一组要 1-3 小时；强制注入的组还要长好几倍。其实应该多跑几轮的，**毕竟模型有随机性**，然而跑一轮时间太长了，暂时没有足够的耐心去跑那么多轮。
- mini 其实是个很鸡肋的 skill，但对于恰好需要用到的人，就恰好有用。 qwen3.8 和 35b-a3b 上，mini 毫无增益。这是最有意思的一点：面向指令遵循能力很强和指令遵循能力很弱的模型，mini 都没什么太大的意义；但是像 qwen3.6-27B 这种能力不错、但长上下文指令遵循欠佳的模型，这是个不错的选择。

## 技术栈兼容

vibeweaver 与技术栈无关，从不假设语言、框架或数据库：

- **新项目**：报上技术栈，或者它会在开工前问一次。然后围绕这个技术栈生成设计文档、`config.toml` 布局、`script/` 生命周期脚本和依赖清单。
- **存量项目**：它先读现场（记忆、配置、脚本、目录结构），再让每条规则去适配现状。它不会「好心」往 Vue 项目里塞 React。
- **Windows**：放心，`install.bat` 和 `script/windows/` 都在。

### 默认技术栈，以及怎么改

新项目脚手架内置了一个默认栈（SKILL.md 的 Part B1）：**FastAPI + React + Vite + PostgreSQL**：Python/FastAPI 后端，所有接口挂 OAuth2 认证，前端挂在 `/static` 下并带 history 路由回退，React + Vite 响应式前端（桌面 / 平板 / 手机）。说「开个新项目」然后什么都不说，出来的就是这套。

想要别的技术栈，两条路：

1. **按项目来，完全不用动 skill。** 开口就报清楚（「新 Go + Vue + MySQL 项目」），skill 就围绕报的栈来搭。默认栈只在没挑的时候生效。核心规则（Part A）与技术栈无关；skill 读声明的栈，填上真实的构建命令，再把 `[database]` 配置块改成实际用的数据库。
2. **永久改，改 skill 的 Part B。** 想换个*默认值*焊死进去，就改 `SKILL.md` §B1（"Default New Project Stack" 那节）里的栈描述，同时把 `APPENDIX.md` 里对应的两处一起改掉：

   - §A5：`config.toml` 完整模板（改成实际的后端 / 数据库形态）
   - §A6：脚本模板（`script/linux/project_build.sh`、`start.sh`、`stop.sh`、`restart.sh` 和 Windows 的 `.bat` 兄弟），让它们生成的是这个栈的真实构建/启停命令，而不是 npm/uvicorn 那套

   适配时的准则（Part B2）：Part A 的核心原则全部照搬（放之四海皆准），脚本模板换成自家的构建工具，配置模板对准实际的数据库，`script/` 目录纪律不能丢，机制比里面的命令更重要。

## vibeweaver vs superpowers

[Superpowers](https://github.com/obra/superpowers) 是最接近的知名同类：一个基于 skill 的 coding agent 开发方法论。两边都是 MIT，都是 skill 生态，但押注的方向不同：

| 维度 | vibeweaver | superpowers |
| --- | --- | --- |
| 工作流 | 拆解 → **联网检索（几乎强制）** → 设计文档/实施计划（新项目/大任务时）→ 测试先行 → 证据门槛 | 头脑风暴 → 规格 → 详细计划 → 子 agent 执行 |
| 核心赌注 | **搜索先行 + 证据门槛式完工**——动手前几乎强制联网检索（太阳底下没有新鲜事），完工必须测试跑完并留下产物，还有工具级插件拦截兜底 | **计划先行**——头脑风暴 → 规格 → 详细计划 → 子 agent 执行 |
| 验证 | 自动启动的采集循环，独立多模态验证器评分，`assert_artifacts.py` 逐字节核对证据 | 宣布完工前人工/自查 |
| 项目记忆 | 内置记忆子系统，带信任分级 | 非核心功能 |
| 模型要求 | 也为小模型优化（mini 版，实测到 ~3B 激活档） | 默认强模型——长规格、长计划、子 agent 委派 |
| 工具支持 | opencode（带插件拦截；DeepSeek Harness 版已开源为 [vibeweaver-dsh](https://github.com/logandoo/vibeweaver-dsh)；Claude Code / Codex 有无类似机制未知，欢迎 fork） | Claude Code、Codex、Cursor、Gemini CLI、Copilot、opencode 等 |
| 公开评测 | 与裸模型对照的 A/B 数据，多模型多轮 | 无公开基线数据 |

**2026-08-30 全仓库重读**（superpowers 全部 14 个技能逐读）：大半内容本 skill 早已覆盖——计划格式、调试四阶段、TDD 规则、spec 自审清单同源，这趟主要是覆盖确认。两条想法被采纳——**spike 路由**（可行性问题的交付物是答案不是代码；产出标记 throwaway，要留 = 新请求并自带基线）和**任务切分测试**（仅当 reviewer 能否决一个任务而通过其邻任务时才拆分）。八条在案拒绝（子代理逐任务执行、全路径批准门、逐节设计批准、git worktree 等——与 AUTO 模式、一次性确认、会话内证据环冲突）。完整裁决清单见 [CHANGELOG_zh.md](CHANGELOG_zh.md)。

两者开头一样，先拆解再计划。重心不同：superpowers 把投入放在规划上，vibeweaver 把「先搜索」提到几乎强制的级别（太阳底下没有新鲜事），完工则卡在证据上。两者并不互斥；token 预算管够的话，一起上也没问题。

当然，一起上之后 agent 会不会因为上下文爆炸而彻底不干了，没试过不知道，欢迎测试反馈。

## 文件清单

| 文件 | 用途 |
| --- | --- |
| `SKILL.md` | 绑定操作契约 + 路由器（813 行，<49KB，有体积守卫） |
| `COMPLETION_GATE.md` | 完成输出规格 · 构件门禁 · §AUDIT 审计协议 · 预输出清单 |
| `CODING_PRINCIPLES.md` | 四条铁律 + Karpathy 的六条纪律 + 评审 smell 基线 |
| `ENGINEERING_STD.md` | 工程标准细则 |
| `REFERENCE.md` / `APPENDIX.md` | 流程参考 / 可执行模板（含 §A9 事故复盘模板） |
| `TESTING_PROTOCOLS.md` | §A4.1 循环 + §A4.6 调试 + §A4.7–§A4.11 规范文本（§A4.11 模式/暂停协议） |
| `WORKFLOWS_EXTENDED.md` | §M 双模式 + Class-E 清单 + ADR/PAUSED 格式 · C4 审计 / C5 部署 / C6 运维 / C7 非Web / S1 spike · 项目画像参照 |
| `MEMORY_RULES.md` / `MEMORY_TEMPLATES.md` | 项目记忆子系统 |
| `scripts/assert_artifacts.py` | 17 标记断言的规范脚本，项目复制进 `tests/` 使用（含 secret scan 配对 / test-change guard / risk-tier / 项目画像） |
| `scripts/mm_probe.py` | 行为化多模态自探针（COV-5 验证器选择） |
| `vibeweaver-gate.js` | stop hook 插件（opencode）+ 机械化停滞观测 |
| `vibeweaver-audit.js` | 三层机械审计器（Tier 0/1/2）——会话级 RED 锁存、带留痕的自动释放、陈旧锁存自愈 |
| `scripts/vibeweaver-audit-core.js` | 纯裁决核心（可无头测试） |
| `scripts/audit_selftest.mjs` / `mutation_sweep.mjs` | 36 项 fixture 检查 / 27 项变异检查——含锁存释放回归 |
| `install.sh` / `install.bat` | 安装脚本（skill 文件 + 两个插件） |

## 相关项目

- [mm-sensor](https://github.com/logandoo/mm-sensor)：独立媒体验证器（图片 / 视频 / 音频）
- [J-Space Cognition Suite V3.6](https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6)：推理时认知控制套件，「认知层」各机制的出处（见[致谢](#致谢)）

## 致谢

`CODING_PRINCIPLES.md` 改编自 [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)（"Karpathy-Inspired Claude Code Guidelines"，MIT 协议，作者 multica-ai / forrestchang），其源头是 [Andrej Karpathy 对 LLM 写码翻车模式的观察](https://x.com/karpathy)。

**认知层**各机制的出处是 [Tiger3807861189](https://github.com/Tiger3807861189) 的 [J-Space Cognition Suite V3.6](https://github.com/Tiger3807861189/J-Space-Cognition-Suite-V3.6)：「无覆盖范围的验证声明」检查（assert 第 13 组）仿照其 `ship` 检查而来；停滞参数化、独立参考实现的差分验证、双路对账、写一次读多次的一致性枢纽、不可信内容不对称规则、长间隔重入协议，以及插件里的机械化停滞观测，都可追溯到该项目的模块与控制器；其「单入口 + 按需加载模块」的结构也影响了本 skill 的渐进披露组织方式。致谢落在思想层面，此处的实现均为本项目原创。

2026-08-30 两波（wave4/5）借鉴了 [mattpocock/skills](https://github.com/mattpocock/skills)（测试缝、spec 保真三元组、评审 smell 基线、grilling 分轮访谈、ADR 准入三判据）与 [obra/superpowers](https://github.com/obra/superpowers)（spike 路由、任务切分测试）的想法——两者均为 MIT；采纳与拒绝的完整清单见 [CHANGELOG_zh.md](CHANGELOG_zh.md) 各波次条目。

评测方法与原始数据：`vibeweaver-eval`。

## 变更记录

按波次的设计演变史在 [CHANGELOG_zh.md](CHANGELOG_zh.md)（英文：[CHANGELOG.md](CHANGELOG.md)）。

## 许可证

MIT。随便 fork，随便折腾。
