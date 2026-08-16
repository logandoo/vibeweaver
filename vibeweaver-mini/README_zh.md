# vibeweaver-mini

[vibeweaver](https://github.com/logandoo/vibeweaver) 的删减版，单文件，约 5KB。在指令遵循能力一般、但编程能力还行的小规模 LLM 上有点增益效果。属于不需要的人完全不需要，有需要的人确实可以用的那种 skill。

## 为什么要单独做一个 mini

完整版 vibeweaver 有约 88KB 规则和十条 covenant——对小模型来说这不是规则，是威胁。qwen3.6-27B 的评测里，完整版**16 次任务一次都没加载**；而 mini 被加载了 62.5%，直接干翻强制注入的完整版（62.5% vs 56%）。

原理很朴素：**体积决定触发率，触发率决定一切。** 一套模型愿意读的短规则，胜过一份它永远不打开的巨著。mini 就是把"必须执行的纪律"压到最短，让弱指令遵循的模型也能读进去、跟下来。

## 它保留了哪些核心纪律

- **强制加载声明** — frontmatter 描述直接写"写任何代码前必须先加载本 skill"，是整套家族里最激进的触发描述
- **先拆解、先研究** — 动手前拆任务、上网搜现成方案
- **先读项目** — 存量项目先读配置、脚本、README、git 状态
- **TDD 测试先行** — RED→GREEN，看它失败才算数；回归测试必须走完"还原→必败→恢复"闭环；先写代码再补测试 = 删掉重来
- **前端三层测试标准** — 逻辑测试（抽纯函数）+ 组件测试（渲染与交互）+ E2E 截图（验收标准先写进 `tests/acceptance.md`，Playwright 截图，装了 mm-sensor 就用它评分）
- **NO TEST, NO DONE** — 测试没跑、没在磁盘上留下证据，就不算完工；多接口后端任务还要写一条跨接口 workflow 测试（带状态转移断言）
- **脚本化生命周期** — 构建和启停走 `script/`，裸 `npm run build` / `uvicorn` 禁止
- **修复循环** — 单问题最多 5 次迭代，同一失败连续 3 次必须换方向
- **收尾报告** — `acceptance.md` + `verification_log.md` 必须存在，提交带描述，汇报证据

## 比起 vibeweaver 删掉了什么

| 删掉的内容 | 说明 |
|---|---|
| **项目记忆系统** | `memory/`、`MEMORY.md` 索引、主题文件、信任分级（⛔/✅/⏳/❌）、Final Memory Gate——整套跨会话记忆 |
| **设计文档体系** | FLOW / PAGE / DATABASE / BACKEND_DESIGN.html，以及 Design Gate A/B 审批环节 |
| **新项目脚手架流程** | C1 全流程、`config.toml` 模板、Part B 默认技术栈（FastAPI + React + Vite + PostgreSQL） |
| **完工表格与审计行** | 8 列完成表、`[Verification Gate]` 行、`[Convergence]` 行、Covenant Recall、10 条 covenant 的正式化（COV-1~10） |
| **可执行断言与硬拦截插件** | `assert_artifacts.py` 字节级核对脚本、`vibeweaver-gate` 插件（stop hook） |
| **独立代码评审** | A4.9 子 agent 评审派发（COV-8） |
| **API 文档驱动循环** | A4.7 的"更新 API 文档→doc↔code 审计→从文档写用例"，只保留"调 API 验证 + 一条 workflow 测试" |
| **系统化调试四阶段** | A4.6 根因调查流程，只留了一句极简版（读完整报错 → 诊断根因 → 一次只改一处） |
| **配置/依赖/沟通/Git 章节** | A3、A6、A7、A8、A9 的独立规则 |
| **视频/音频证据** | Playwright 录屏（record_video）和 Web Audio 采集，只保留截图 |
| **mm-sensor 模态检测** | `vision.py --probe` 和 [video+audio]/[video]/[image] 模式，简化为"装了 mm-sensor 就用它评分，没装就直读" |
| **大任务实施计划** | C3 的 Files/Interfaces/Steps 计划模板 |
| **配套参考文件** | `CODING_PRINCIPLES.md` / `ENGINEERING_STD.md` / `REFERENCE.md` / `APPENDIX.md` / `MEMORY_RULES.md` / `MEMORY_TEMPLATES.md`——mini 刻意做成单文件 |

一句话：**mini 只留"必做"的强制项，砍掉所有"加分项"。** 它不陪小模型讨论设计文档，只盯着它写测试、留证据。

## 评测数据

16 题 A/B 评测（10 道 Aider polyglot + 6 道 SWE-bench Lite，隐藏测试评分），与完整版对比，全部出自同一套固定评测架 `vibeweaver-eval`。设置口径：**baseline**（无 skill）、**仅挂载**（skill 在 `available_skills` 里，模型自己决定加载与否——加载了没有就是触发率）、**强制注入**（skill 全文进提示词，没得选）。

看数字之前先看免责声明：16 题是小样本，任务级方差 ±2-3 题，每组每轮只跑一次——qwen3.8 一轮要 40-60 分钟（强制注入的组还要长好几倍），llama.cpp 上的 35b-a3b 一组要 1-3 小时。**请读方向，别读具体分数——也别假设 mini 的增益能平移到你的模型上。** 对本来就规矩的模型，mini 实测增益正好为零（qwen3.8：13/16 = baseline；deepseek：噪声内）。下面的增益是真实的，但都是模型相关的。

### 中小模型（qwen3.6-27B）——mini 诞生的那一轮

| 组 | 通过率 | 触发率 |
|---|---|---|
| 裸模型 | 7/16 (44%) | — |
| 完整版 71KB，强制注入 | 9/16 (56%) | — |
| 完整版 71KB，仅挂载 | 6/16 (38%) | 0/16 |
| **vibeweaver-mini，仅挂载** | **10/16 (62.5%)** | **10/16** |

- 全场最好的成绩：比裸模型 +18.75pp，比强制注入的完整版还高 6.5pp
- SWE-bench 5/6 (83%) vs 裸模型 3/6 (50%)，是全场唯一解出 pytest-6116 的组
- 成本：平均 113s/题 vs 裸模型 69s（+63%）

### 新模型（qwen3.8-27B）——中性

| 组 | 通过率 | 触发率 |
|---|---|---|
| 裸模型 | 13/16 (81%) | — |
| vibeweaver-mini，仅挂载 | 13/16 (81%) | 10/10（polyglot） |
| 完整版，仅挂载 | 15/16 (94%) | 12/16 |
| **完整版，强制注入** | **16/16 (100%)** | — |

mini 与裸模型打平——它提供的那点纪律在新模型上成了原生行为。对已经自带纪律的模型，完整版的额外机制（验收标准、文档驱动测试、验证把关）才是强制注入后多出那 3 题的原因。

### 极弱模型（qwen3.6-35b-a3b）——强制注入的主场

| 组 | 通过率 | 触发率 |
|---|---|---|
| 裸模型 | 6/16 (37.5%) | — |
| vibeweaver-mini，仅挂载 | 6/16 (37.5%) | **0/10** |
| **vibeweaver-mini，强制注入** | **7/16 (43.8%)** | — |
| 完整版，强制注入 | 5/16 (31.3%) | — |

在极弱模型（34.6B MoE，~3B 激活）上，规矩整个反过来了：

- **加载彻底崩塌**：0/10——模型弱到连 available_skills 列表都不读。
- **强制注入 mini 是唯一有效路径**：7/16（本轮最好成绩），bowling 31/31 满分、robot_name 4/4。
- **强制注入完整版是灾难**：5/16，SWE-bench 只剩 1/6，其中 5 次 `no diff produced`——71KB 规则淹没 3B 激活模型的上下文，它直接放弃。
- 成本很肉疼（llama.cpp，均值 700-943s/题，每组 2-9 次超时）——原始数据见 vibeweaver-eval。

所以"别强制注入"不再是一刀切：对中小模型，强灌 mini 是纯开销（qwen3.6-27B 从 62.5% 掉到 50%）；对极弱模型，那是唯一管用的办法。

强模型（deepseek-v4-flash-0731）上 mini 是中性的（68.8% = 裸模型）——强模型自带这套纪律，mini 的价值在弱模型上。

## 安装

```bash
git clone https://github.com/logandoo/vibeweaver && cp -r vibeweaver/vibeweaver-mini ~/.config/opencode/skills/vibeweaver-mini
```

或者复制 `SKILL.md` 到你的 skills 目录：

- 全局（Linux/macOS）：`~/.config/opencode/skills/vibeweaver-mini/`
- 项目级：`.opencode/skills/vibeweaver-mini/`

重启 opencode 即可。可选配件：Playwright（截图采集）、[mm-sensor](https://github.com/logandoo)（截图独立评分，装了更靠谱）。

## 怎么选

- **极弱模型（~3B 激活）** → 用 mini，强制注入（仅挂载在能力阈值之下会彻底失效；完整版约 88KB 会淹没上下文）
- **弱指令遵循模型（中小模型）** → 用 mini，常驻触发
- **强模型** → 用 [vibeweaver](https://github.com/logandoo/vibeweaver) 完整版，配插件注入（或 mini 常驻 + 完整版按需展开）
- 完整版自带的项目记忆、设计文档、硬拦截插件，mini 都没有——需要这些就上完整版

## 相关

- [vibeweaver](https://github.com/logandoo/vibeweaver) — 完整版：记忆系统、设计文档、验证把关、全部配套文件
- [mm-sensor](https://github.com/logandoo) — 图片/视频/音频独立验证器

## 许可证

MIT
