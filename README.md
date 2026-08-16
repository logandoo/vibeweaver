# Vibeweaver

一个面向 vibe-coding 的编码规范家族：把"相信我，能跑"变成"测试跑过了，证据在磁盘上"。

## 目录结构

| 目录 | 是什么 |
|---|---|
| [`vibeweaver/`](vibeweaver/) | 完整版 skill：研究先行、测试先行、验证循环、项目记忆、stop hook 插件，全套配套文件 |
| [`vibeweaver-mini/`](vibeweaver-mini/) | 删减版，单文件约 5KB。在指令遵循能力一般、但编程能力还行的小规模 LLM 上有点增益效果。不需要的人完全不需要，有需要的人确实可以用 |
| [`vibeweaver-eval/`](vibeweaver-eval/) | 完整评测架：16 题 A/B 评测的配置、评分脚本、原始运行结果、逐轮评测报告 |

## 快速安装

```bash
git clone https://github.com/logandoo/vibeweaver
# 完整版
cp -r vibeweaver/vibeweaver ~/.config/opencode/skills/vibeweaver
# 或删减版
cp -r vibeweaver/vibeweaver-mini ~/.config/opencode/skills/vibeweaver-mini
# 重启 opencode 生效
```

## 怎么选

- **强模型** → 完整版，插件注入
- **弱指令遵循模型（中小模型）** → mini 版，常驻
- **极弱模型（~3B 激活）** → mini 版，强制注入
- 细节见各子目录的 README

## 相关项目

- mm-sensor —— 独立媒体验证器（图片 / 视频 / 音频），vibeweaver 验证循环的搭档

## License

MIT
