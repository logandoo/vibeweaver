# vibeweaver 巨型源文件防控机制审计

日期：2026-11-22  
基线：`d2b3aa5e2b0b3c65f319d71bf42a7f949e71a19a`  
类型：C4 read-only / Class DOC / Lane M  
证据：`tests/audit_giant_file_controls.log`  
独立复核：`tests/review_giant_file_controls.md`

## 0. 结论

**是问题，也应该补机制；但“数万行”本身不是充分的拆分支配方。**

对于手写、持续演进、承担多职责的源文件，数万行已是必须显式治理的高风险状态：它增加理解与导航成本，也增加 coding agent 读取、定位和编辑时的上下文压力。另一方面，行数不直接等于低内聚或高缺陷；生成代码、协议表、词汇数据、锁文件及某些高内聚解析器可能合理地很大。把一个大文件机械切成十个互相紧耦合的小文件，可能只是把本地复杂度变成跨文件跳转与耦合。

因此应增加的是 **“可测量、早预警、阻止无意识地持续膨胀、例外可见且受信任、按职责渐进拆分”** 的组合机制，而不是一条跨语言统一的 `max-lines = N` 硬规则。

本轮只审计与提出后续 C2 任务，**没有修改任何源码、配置或脚本**。

## 1. 范围、方法与证据边界

### 1.1 范围

- 检查当前契约：`SKILL.md`、`REFERENCE.md`、`WORKFLOWS_EXTENDED.md`、`ENGINEERING_STD.md`、`CODING_PRINCIPLES.md` 等。
- 检查可执行控制：`scripts/assert_artifacts.py`、`scripts/contract_lint.py`、根插件与 `scripts/` 的命名搜索。
- 检索一手工具文档、同行评议维护和 agent 上下文资料。
- 对两条 Important 发现和一条 Minor 边界进行 fresh-context 只读复核。

### 1.2 明确不声称的事项

1. 本次未抽样使用 vibeweaver 的外部项目，故“数万行文件的发生率”是 **UNVERIFIED**；用户报告是需求触发场景，不是流行率统计。
2. 本仓库现有大文件只是控制覆盖 PoC，不证明它们内聚低、缺陷多或必须拆分。
3. 外部资料没有给出跨语言、跨项目统一的最佳行数；本报告中的示例阈值只能是待校准政策。
4. 现有资料没有直接证明“拆文件会提高 coding agent 完成任务的质量”；这需要本 skill 自己的行为 A/B 评测。

## 2. 外部研究如何判断

### 2.1 人类维护：规模有用，但机械拆分可能适得其反

Sjøberg 等在 IEEE TSE 2013 的受控工业研究中，让 6 名开发者维护 4 个功能等价 Java 系统，记录 298 个文件的维护时间。摘要报告：调整文件规模和变更次数后，所查 12 种 code smells 不再显著增加 effort；**文件规模与变更次数共同**解释了模型中几乎所有变异。[IEEE 记录](https://ieeexplore.ieee.org/document/6392174) · [作者稿](https://web-backend.simula.no/sites/default/files/publications/Simula.simula.1460.pdf)

这支持“把规模作为便宜、持续可用的风险信号”，但不支持两个过度推断：

- 不是“所有大文件都必然难维护”；
- 不是“拆小必然减少总维护成本”。

作者稿 §5.4 反而警告：更多文件带来的系统级风险和零散 effort 可能抵消拆分收益，其比较中甚至出现过“更少但更大的文件更省力”的情形。

### 2.2 工具政策：成千上万行的风险被承认，但阈值没有客观统一值

- [ESLint `max-lines`](https://eslint.org/docs/latest/rules/max-lines) 明确写道：没有客观的可接受最大行数，但多数人认同不应达到数千行；文中提到的常见建议为 100–500，规则默认 300。
- [Pylint `too-many-lines`](https://pylint.readthedocs.io/en/latest/user_guide/messages/convention/too-many-lines.html) 将行数称为 cyclomatic complexity 的粗代理，并指出复杂度指标更细；稳定配置中的 [`max-module-lines = 1000`](https://pylint.readthedocs.io/en/stable/user_guide/configuration/all-options.html) 是 Python 工具政策，不是跨语言科学常数。

**结论：** 阈值可用于预警和预算，但不能冒充普适真理；还应结合职责、复杂度、耦合和变更热点。

### 2.3 Coding agent：长文件有直接上下文成本，但超窗不是必然

[GitHub Copilot 上下文文档](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/context-management) 明确说明：读取长文件会产生很大的 tool result，工具结果会累积进固定上下文窗口；Copilot CLI 默认把大于 20 KiB 的工具输出转存为临时文件，只给模型路径与预览。

这里的 20 KiB 是**工具输出转存阈值**，不是模型上下文上限，也不是推荐文件上限。agent 可以通过搜索、分段读取降低负担，所以不能说“大文件必然超窗”；可以确认的是，整文件读取与跨位置依赖会增加上下文和定位成本。

[Anthropic 长时运行 agent 报告](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents) 观察到 one-shot 做太多会耗尽上下文并留下半成品，改进包括一次一个 feature、干净增量提交和结构化进度。这为增量工作提供间接支持，**不是拆源文件收益的直接实验**。

### 2.4 存量项目：优先控制新增和恶化，而非一次性清零

[Sonar Clean as You Code](https://docs.sonarsource.com/sonarqube-server/10.8/core-concepts/clean-as-you-code/introduction) 强调新增/修改代码满足标准，并在触碰旧代码时渐进改善，适用于难以全量清理的 legacy 项目。这与 vibeweaver 已有的 shrink-only ratchet 思路一致；它是方法论支持，不是对本方案有效性的实验验证。

## 3. 当前 vibeweaver 的发现

### F1 — Important · Compliance：可执行门禁没有源文件规模/增长控制

**证据**

- `scripts/contract_lint.py:91-100` 的 49,000/45,000/2,048 字节帽只保护 skill 自身 Markdown payload。
- `scripts/assert_artifacts.py:42-45` 定义 reachable blob 的 10 MiB WARN / 40 MiB FAIL。
- `scripts/assert_artifacts.py:1099-1118` 的 `largest_blob()` 只计算 Git 对象字节；`1453-1503` 的 hold/shrink/grow 棘轮也只围绕该值。
- `tests/debt_baseline.json:1-8` 唯一指标是 `largest-blob`。
- 命名搜索 E3 覆盖 `scripts/`、两个根插件和 canonical checker，未找到 per-file LOC、NCLOC/SLOC、cyclomatic、source/file budget 控制。

**PoC**

当前 tracked executable 最大者 `scripts/audit_selftest.mjs` 为 4,863 行、335,783 B；仅为 10 MiB WARN 的 3.202%。`vibeweaver-audit.js` 为 3,483 行，`vibeweaver-gate.js` 为 2,909 行。它们可以远低于 blob 阈值而持续增长。

**影响**

现有门禁能发现仓库历史里的大对象，却不能在目标项目的源文件从 800 行逐步长到 8,000/20,000 行时给出任何规模信号。

**独立裁决：CONFIRMED。**

### F2 — Important · Compliance：任务切分和生成流程不感知文件增长

**已有覆盖，不能说“完全没有架构指导”**

- `ENGINEERING_STD.md:51-55` 有 “Pay attention to module separation”。
- `CODING_PRINCIPLES.md:80-81` 有 Divergent Change：一个模块因多个不相关原因变化，应按变化原因拆分。
- A4.9 对 new feature、≥3 files、行为语义变化等会触发独立评审；不能误称 new feature 没有 review。

**缺口**

- `CODING_PRINCIPLES.md:54-64` 明确 smell baseline 是 judgement call，不是规模测量或硬违规。
- `REFERENCE.md:564-567` 允许 single-file fix 跳过 C3 书面计划；`583-586` 的 right-sizing 只看可独立测试交付物。
- `WORKFLOWS_EXTENDED.md:367-376` 把 C8 item 限定为 Lane S；Lane S 的“≤2 files”并不限制同一个文件最终多大。
- 没有一个生成期/变更期步骤要求回答：“这个文件当前多少行，本次增加多少，是否跨越预算，是否正在承担第二类职责？”

**影响**

任务粒度很小并不等于代码单元很小。连续多个合规的 Lane-S item 仍可能把全部代码追加到同一文件；reviewer 若没有量化信号，也容易只审当前 diff 而看不到长期积累。

**独立裁决：CONFIRMED。**

### F3 — Minor · Compliance：PoC 和外部发生率必须保持边界

本仓库的 4,863/3,483/2,909 行文件只证明“现有 byte cap 不覆盖源码行数”，不证明必须拆分。本次没有外部项目样本，不能推断“经常出现”或数万行文件比例。

**独立裁决：CONFIRMED。**

## 4. 方案比较

| 方案 | 优点 | 主要问题 | 裁决 |
|---|---|---|---|
| A. 全局统一硬行数上限 | 简单、确定、易 CI 执行 | 语言/生成代码差异大；会诱发 one-liner、删注释、机械碎拆；没有解决职责与耦合 | **不单独采用** |
| B. 只加“注意模块分离/避免大文件”散文 | 成本最低 | 当前已有类似指导，缺少信号、状态与闭环；易于完成后遗忘 | **不足以解决问题** |
| C. 完全委托各语言 linter | 能复用 NCLOC/complexity 等成熟指标 | stack-specific，配置和默认不统一；通常没有跨 wave 的存量棘轮与可信豁免 | **作为可选适配层** |
| D. 测量 + 软/硬预算 + 存量策略 + 职责评审 + 测试 | 能早期发现、约束增长，又保留架构判断和例外 | 需要信任边界、反绕过与校准，实施成本高于 A/B | **推荐** |

## 5. 推荐设计：`Source File Budget`（SFB）

### 5.1 第一原则：规模触发问题，不自动决定答案

超过软阈值时必须产生可审计问题：

1. 文件能否用一句话说明单一职责？
2. 是否存在不相关的变化原因、明显独立 symbol cluster、高 fan-out 或高变更频率？
3. 保持单文件是否有明确收益（例如高内聚状态机、生成表、局部算法）？
4. 若拆分，抽取边界和稳定 public API 是什么？哪些 characterization/regression tests 保证行为不变？

**规模 + 至少一个结构/演进信号**才支持优先拆分。没有第二信号时，可以保留并记录理由；超过非 grandfathered 绝对上限则必须缩小、按职责重构或取得可信例外，而不是自动乱拆。

### 5.2 确定性测量口径

核心检查保持 stdlib-only、语言无关：

- 范围：tracked + staged + untracked/non-ignored 的 in-scope 工作树源码；不能只看 tracked，否则新文件在执行期消失于检查之外。
- `physical_lines = len(raw_bytes.splitlines())`：空文件为 0，CRLF/LF 均按一行，保留无末尾换行的最后一行；不要直接把 `wc -l` 当完整规范。
- bytes 同时报告原始工作树字节和明确规范化的字节口径（如 CRLF/CR→LF）；BOM、空文件、非 UTF-8、二进制、symlink、submodule 的处置必须固定并测试。
- 核心层只称 `physical lines`，不把粗糙文本计数冒称 NCLOC。Python/JS 等可接入现有 linter，补充 NCLOC、cyclomatic complexity、function length 等。
- 输出 top-N、本 wave delta、阈值状态和豁免原因到 `tests/source_budget.log`；执行期按 changed files 增量，final 做完整 in-scope 对账，避免大型仓库性能税。

### 5.3 阈值是政策，不是自然定律

可用 Pylint 的 1000 行作为 **shadow-mode 初始观察点**，例如观察 `warn=1000 / hard=2000` physical lines；ESLint 的 300 默认说明某些生态会选择更严格值。1000/2000 在这里只是校准起点，不能写进契约宣称“最佳”。

按项目已有的 `config.toml` 管理阈值和 scope；测试、手写运行时代码、生成代码可采用不同预算。先在真实项目分布上 shadow 运行，再决定默认值。

### 5.4 每次 final 都约束非 grandfathered 文件

不能只检查“文件新建的那一刻”。否则先创建 1,990 行、下一 wave 再追加即可绕过。

| 状态 | 结果 |
|---|---|
| 非 grandfathered，低于软阈值 | PASS |
| 非 grandfathered，跨软阈值 | WARN + 职责问题进入 review |
| 非 grandfathered，任何一次 final 超过硬阈值 | FAIL；缩小、按职责重构或取得可信例外 |
| 采用门禁时登记的 grandfathered 存量巨文件，保持/缩小 | WARN `held at baseline`；缩小可在受信任流程中下移棘轮 |
| grandfathered 文件增长 | 初版 WARN + 强制独立评审；若启用了外部受控 no-growth，则按受控策略处理 |
| 合法豁免 | PASS，但仍进入汇总；豁免身份与授权必须可验证 |

Baseline 在采用时由受信任流程建立，之后的 agent 不得新增 grandfathered key、提高记录值、删除重建或通过 rename/copy 获得新身份。路径不在 baseline 的新文件永远是 non-grandfathered；即使第一波低于阈值，后续 final 仍受通用硬上限约束。

### 5.5 存量巨文件：为什么初版不应“一律零净增长 hard fail”

独立复核给出关键反例：一个 5,000 行高内聚解析器增加三行边界保护和回归测试，可能是风险最小的修复。若强制同时删三行或抽模块，会违反 `ENGINEERING_STD.md:15-17` / `CODING_PRINCIPLES.md:22-35` 的 Surgical Changes，甚至诱导压缩语句、删注释和无关重构。

因此：

- **新项目/非 grandfathered 文件**：用通用硬上限阻止形成巨文件。
- **存量 grandfathered 文件**：初版增长为 advisory + 必须 A4.9 独立评审 + 债务摘要，不假装已经彻底阻止增长。
- **可选外部 no-growth 模式**：只有可信 waiver 机制完成后才 hard enforce。

未来 waiver 必须绑定 path、base/final blob SHA、issue、最大行/字节增量、到期日和累计债务；只批准精确结果、不修改 baseline、不自动继承。agent 不能同时创建和批准。紧急 break-glass 需外部受信任主体授权并限时 post-review；没有能力建立此边界时，宁可保持 legacy advisory。

### 5.6 豁免需要信任边界，不是自写理由

`committed + review-visible` 不等于可信批准。同一 agent 若能提交 `src/** = generated` 并自行 review，整个机制会失效。

- 阈值、baseline、豁免配置的变更必须由 protected CI/CODEOWNERS/人类或其他明确外部信任主体批准；普通 AUTO ADR 或同一 wave 的 A4.9 不自动获得此权限。
- 优先精确路径；确需目录 glob 时必须限制在受保护配置。记录 generator、owner、reason、内容哈希或可信 regeneration check、review_after。
- 新增加豁免、把已有手写文件标为 generated、提高 baseline、删除重建均默认拒绝。
- 无外部批准通道时，agent 可提出豁免但不得让其生效；正常运行不需要豁免即可继续。

### 5.7 防止“碎片化洗绿”和计数游戏

- rename/copy/delete-recreate 的身份不明时 fail-closed；无内容变化的精确 rename 可由受信任流程迁移记录，copy 不继承 grandfathered 身份。
- 除 per-file 结果外，输出 wave 级总源码增长、文件数变化和阈值跨越摘要；一波拆出多个文件不能自动证明设计更好。
- 大比例搬移/拆分必须触发职责评审和真实测试证据，不能只填写“已拆分”。
- 同时观察 bytes、复杂度和可读性，避免 one-liner/minification/删注释把 physical-lines 洗绿。

## 6. 接入 vibeweaver 的位置

1. **C1 新项目**：设计阶段给 module map/职责边界和预算 scope；脚手架生成后跑 shadow report。
2. **C2 修改项目**：survey 阶段读取预算报告；touch 到接近阈值文件时，在实现前决定保持/抽取，而不是完成后补救。
3. **C3 / C8**：任务除了 Files/Interfaces/Test seam，还要写预算 delta；Lane-S 的 ≤2 files 继续保留，但新增“final file budget”。
4. **A4.9**：跨软阈值、legacy 增长、大比例搬移/拆分成为明确 review 触发器；reviewer 使用职责/复杂度/变化原因，不只看 LOC。
5. **门禁节奏**：执行期增量 WARN、去重；`--final` 对非 grandfathered 硬上限执行 FAIL，沿用 W19 的降噪经验。
6. **拆分任务**：作为独立、边界明确的 C2 refactor；COV-9 baseline GREEN，先补 characterization/regression tests，小步抽取并保持 API，禁止 drive-by big-bang。

实现上应使用独立的小型 checker，不要继续膨胀已经 2,499 行的 `scripts/assert_artifacts.py`；root `SKILL.md` 也有字节预算，完整规范应落在合适 companion/现有工程标准中，主契约只保留可执行入口。任何真实实施都属于 new feature/多文件改动，走 Lane L、C3、独立评审与 FCV。

## 7. 后续 C2 路线（按依赖排序）

### R1 / P0 — Shadow 测量器与口径夹具

交付独立 `source_budget` checker、config scope、确定性报告，不先硬阻断。覆盖 CRLF/LF、无末尾换行、BOM、二进制、symlink、submodule、untracked、rename/copy、monorepo。先在本仓库和代表性目标项目观察分布、噪音、耗时。

### R2 / P1 — 反绕过与职责评审

加 protected baseline/exemption 信任边界、非 grandfathered 每次 final 全量上限、wave 汇总和 A4.9 职责问题。mutation tests 必须杀死：自批准豁免、提高 baseline、删除重录、untracked 漏检、rename/copy 洗白、1,990 行后续增长、拆成十个文件、one-liner 规避。

### R3 / P2 — 新项目默认启用，存量先 advisory

在新项目或非 grandfathered 文件上默认硬门；legacy 只 Warn+Review。任何示例阈值先在 shadow 校准，不强行清理现有巨文件。

### R4 / P3 — 行为 A/B 后再扩大硬门

按 `VERIFICATION_UPGRADES.md §V8` 做 fresh isolated paired eval：同一增量多 feature fixture，比较旧/新 skill 的 hidden functional tests、最终文件预算、无意义拆分、review/门禁噪音、token/墙钟成本。N<5 只能报 directional；若功能相同但跳转/耦合/成本变差，应调整机制而非宣布成功。

### R5 / P4 — 可选可信 legacy waiver

只有外部授权、精确 SHA 绑定、累计债务和 post-review 都实现后，才把 grandfathered no-growth 从 advisory 升为可配置 hard gate。

## 8. 最少测试集合

- 小文件通过；跨软阈值 Warn；非 grandfathered 超硬阈值在每次 final 失败。
- 存量 grandfathered 保持/缩小/增长三条路径；小 bugfix 不被初版无条件硬阻断。
- staged/untracked/non-ignored 新源码均纳入；二进制、生成代码、vendor 等按明确规则处理。
- 自批准豁免、baseline 上升、删除重建、路径迁移、复制、拆波、碎片化均不能洗白。
- CRLF/LF/无末尾换行跨平台计数一致；空文件/BOM/非法 UTF-8 有定义。
- 合法重构：原项目测试与 characterization tests 在拆分前后均绿，public API 兼容，最终不是单纯“文件更多”。
- checker 扫描有界、报告可读、重复 Warn 去重；无法枚举 scope 时 fail-closed。

## 9. 未覆盖项

1. 未测量外部 vibeweaver 项目的实际文件分布、缺陷率或数万行发生率。
2. 未对本仓库列出的 4,863/3,483/2,909 行文件做内聚、依赖图、变更热点或应当拆分的架构评审。
3. 未实现 checker、baseline、豁免或 waiver；所有阈值和最终收益仍待 shadow/A/B 验证。
4. 未比较所有语言 linter，也未选定具体 NCLOC/complexity 工具；核心建议不依赖新增第三方包。
5. 未评估多 agent RunContext 下 waiver 审批身份的全部实现细节；实施时必须把该信任边界纳入威胁模型。

## 10. 独立复核及修正闭环

Fresh-context reviewer `ses_dfc16f539ffeFsLJ4Y4lC27X95` 对 F1/F2/F3 全部 **CONFIRMED**，外部证据边界未被推翻。初版建议为 `ready-with-fixes`，提出：

- R1：自提交豁免仍可洗白 → §5.6 增加外部信任边界。
- R2：只查新建留下增长窗口 → §5.4 改为非 grandfathered 每次 final 都查，并补 untracked/rename/copy。
- R3：存量零净增长误伤 bugfix → §5.5 改为初版 advisory+review，可信 waiver 后才可硬化。
- R4：行数字节口径不清 → §5.2 固定 splitlines、规范化与特殊文件测试。

这些修正属于报告设计闭环，不表示机制已经实现或实测有效。

Scoped re-review 已逐项裁定 R1/R2/R3/R4 全部 **ADDRESSED**，未发现新的 Critical/Important/Minor 逻辑矛盾，Assessment 为 **ready（仅报告设计闭环）**。
