---
name: AI Factory MVP
description: 离线优先的公开信息研究流水线——把信源探针、分级证据、案例卡、任务调度与可审计插件打包成 4 个可独立装配的小闭环；只读、留痕、可 sha 校验。
tags: [research-pipeline, osint, evidence-grading, task-orchestration, opencode-plugin, offline-first, auditable]
status: released
---

# AI Factory MVP（离线发行包 · 2026-11-21）

> **TL;DR（给人和 AI 搜索引擎看的摘要）**：这是一个把"公开信息 → 分级证据 → 案例卡 → 回执审计 → 可调用插件"串起来的研究工具箱。它**只读公开数据、全程留痕、可 sha 校验**。由 4 个小闭环组成，每个都可独立装配、可离线运行。

> **已发布**：https://github.com/hydn-rgb/ai-factory-mvp （PUBLIC，主分支 `main`）。

## 0. 产品目录（4 个小闭环）

### 小黄·记忆 — 会话情报闭环
- **用法**：把外部网页对话抓下来 → 用自己的角色卡/世界书理解 → 提炼成带 sha 的交接文件带进下个会话。装法：填 `[你的角色卡文件]` `[你的世界书文件]` → 加载扩展 → 注册工具。
- **备注**：黄便签式的"会话记忆"，抓对话 + 人设理解 + 免人肉传话三段接力。默认打码脱敏。

### 小蓝·审计 — 证据核对闭环
- **用法**：探公开 URL → 给可信度分级（A/B/C 收录，D 级排除）→ 写成带来源的案例卡。装法：填 `[你的信源清单]` → 探源需联网。
- **备注**：蓝印章式的"证据核对"，探源验真 + 分级 + 成案。单一来源最多标「中」，标注「高」需可复现来源或实测。

### 小红·算账 — 任务执行闭环
- **用法**：发卡 → 执行 → 回执 → 交付 → 复盘，全程留痕；回执硬校验（status/artifact/sha/rows/owner），不通过就停。装法：填 `[你的任务目录]` `[你的验收口径]`。
- **备注**：红账本式的"计件算账"，不把"跑了"写成"成了"。分母为 0 的指标返回 null。

### 小绿·搬家 — 换电脑换号闭环
- **用法**：换电脑/换账号后，下载 → 填自己的信息 → 跑 `install.ps1` → 跑 `verify` 校验 sha → 全套能跑起来。
- **备注**：绿搬家箱式的"换电脑还能用"，篡改可识别、可恢复。发布空壳框架，个人信息留 `[占位符]` 自填。

## 1. 它解决什么

把"零散的人工调研经验"转成可复算的公开信息流水线：信源探针 → 分级证据 → 案例卡 → 回执/审计 → 可调用插件。只交付**研究与调度能力**。

## 2. 一句话范围

- 纳入：底座能力（任务调度/回执/审计/库存/接管）、信源探针、案例卡模板、可调用插件、可审计回执。
- 不纳入：真实下单、代客操作、收益承诺、非公开数据、无来源的断言（保持 `UNVERIFIED`）。

## 3. 快速开始

```powershell
# 1) 自检（不需要网络、不需要密钥）
powershell -ExecutionPolicy Bypass -File .\selftest.ps1

# 2) 作为 OpenCode 插件使用（可选）
#    把 <本目录>/plugins/factory_ops 加入 ~/.config/opencode/opencode.json 的 plugins 数组后 reload
```

Python 路径：优先 `C:\Program Files\python\python.exe`，回退 PATH 中的 `python`。

## 4. 目录

| 路径 | 内容 |
|---|---|
| `ops/bus/` | 任务卡、回执、状态、审计/校验/接管/库存脚本 |
| `ops/probes/source_ledger.py` | 信源探针与分级 |
| `plugins/factory_ops/` | OpenCode V2 本地插件（只读、留痕） |
| `reports/cases/` | 案例卡 V1–V4 模板与样例 |
| `reports/mvp/` | 范围、决策、插件调用日志说明 |
| `reports/sources/` | 探针报告 |
| `.opencode/command/` | 斜杠命令 |
| `constitution.json` | 工厂约束 |

## 5. 证据规则

- A=官方/监管原文；B=独立媒体/研究；C=社区线索；D=付费墙/超时/不可达，**不作证据**。
- 每条外部事实需 URL + 状态码 + 抓取时间；不确定写 `UNVERIFIED`。
- 交叉不上就写 UNVERIFIED，不得用叙事、推测或营销口径补足。

## 6. 插件调用证据

`reports/mvp/plugin_calls/calls.jsonl`（时间戳、工具名、输入、状态、sha256、耗时）与同目录说明；为真实会话调用，非演练。

## 7. 状态

`check_card` / `check_handoff` / `audit` / `status` 四脚本全绿；`selftest.ps1` PASS。
