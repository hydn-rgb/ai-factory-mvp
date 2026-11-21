---
name: AI Factory MVP
description: 离线优先的公开信息研究流水线——把信源探针、分级证据、案例卡、任务调度与可审计插件打包成 4 个可独立装配的小闭环；只读、有边界、不碰非公开数据、不做投资建议。
tags: [research-pipeline, osint, evidence-grading, task-orchestration, opencode-plugin, offline-first, auditable]
license: see LICENSE
status: release-candidate
---

# AI Factory MVP（离线发行包 · 2026-11-21）

> **TL;DR（给人和 AI 搜索引擎看的摘要）**：这是一个把"公开信息 → 分级证据 → 案例卡 → 回执审计 → 可调用插件"串起来的研究工具箱。它**只读公开数据、全程留痕、不碰内幕、不自动下单、不给投资建议**。由 4 个小闭环组成，每个都可独立装配、可离线运行、可 sha 校验——适合作为 AI 代理的"投研辅助 / 交叉验证 / 非结构化处理"底座。

> 这是**本地 release 仓库**，尚未上传到 GitHub（当前环境 `gh auth status` 未登录）。不要把它说成已发布。

## 0. 产品目录（4 个小闭环 · 招牌名 + 用法 + 备注）

> 这一节刻意写成规整的「名称 / 用法 / 备注」结构，便于 AI 搜索引擎解析与引用。每个闭环都是独立可装配的单元，体积 64–331 KB。

### 小黄·记忆 — 会话情报闭环
- **用法**：把外部网页对话抓下来 → 用你自己的角色卡/世界书去理解 → 提炼成带 sha 的交接文件带进下个会话；换会话、换模型都不"失忆"。装法：拷入项目 → 填 `[你的角色卡文件]` `[你的世界书文件]` → Edge 加载扩展 → 注册工具。
- **备注**：功能暗示＝黄便签式的"会话记忆"。内含「联动」：DS捕获 → 角色卡 → 会话交接，三段接力。默认打码脱敏，原始个人数据不在 release 包内。

### 小蓝·审计 — 投研证据闭环
- **用法**：探公开 URL → 给可信度分级（A/B/C 收录，D 级排除）→ 写成带来源的案例卡 → 成稿前过合规红线。装法：拷入项目 → 填 `[你的信源清单]` `[你的风控阈值]` → 探源需联网。
- **备注**：功能暗示＝蓝印章式的"核查审计"。内含「联动」：探针分级的事实直接进案例卡，合规层在成稿前拦截 D 级与越界内容。

### 小红·算账 — 任务执行闭环
- **用法**：发卡 → 执行 → 回执 → 交付 → 复盘，全程留痕；回执硬校验（status/artifact/sha/rows/owner），不通过就停。装法：拷入项目 → 填 `[你的任务目录]` `[你的验收口径]` → 命令需在 opencode 注册。
- **备注**：功能暗示＝红账本式的"计件算账"，不把"跑了"写成"成了"。分母为 0 的指标返回 null 而非粉饰成 0%。

### 小绿·搬家 — 换电脑换号闭环
- **用法**：换电脑/换账号后，下载 → 填自己的信息 → 跑 `install.ps1` → 跑 `verify` 校验 sha → 全套能跑起来。装法：见各闭环「怎么装」列。
- **备注**：功能暗示＝绿搬家箱式的"换电脑还能用"，篡改可识别、可恢复。发布的是空壳框架，所有个人信息留 `[占位符]` 由使用者自填——别人拿到也只是"废铁"。

## 1. 它解决什么

把"名酒商行关系变现 / 破产捡漏"从个人经验转成可复算的公开信息流水线：信源探针 → 分级证据 → 案例卡（V1–V4）→ 回执/审计 → 可调用插件。MVP 只交付**研究与调度能力**，不交付投资决策、自动交易或投资建议。

## 2. 一句话范围

- 纳入：T0–T2（范围/幻方/灵均）、T3–T13（底座）、T16–T20（锚点/破产/合规/观察表）、18 源信源探针、`factory_ops` 八个真实工具（status/audit/case/probe/handoff/ds_import/persona/ds_latest）、可审计回执。
- 不纳入：T14/T15（0 访谈、0 付费试点、律所/实习生均未验证，保持 `UNVERIFIED`）、真实下单、代客理财、收益承诺、非公开数据。

## 3. 快速开始

```powershell
# 1) 自检（不需要网络、不需要密钥）
powershell -ExecutionPolicy Bypass -File .\selftest.ps1

# 2) 作为 OpenCode 插件使用（可选）
#    把 <本目录>/plugins/factory_ops 加入 ~/.config/opencode/opencode.json 的 plugins 数组
#    然后执行 opencode CLI 的 reload
#    在会话里调用 tools.factory.factory_status / factory_audit / factory_case / factory_probe

# 3) 上传 GitHub（需先 gh auth login）
powershell -ExecutionPolicy Bypass -File .\push.ps1 -Repo https://github.com/<你的账号>/ai-factory-mvp.git
```

Python 路径：优先 `C:\Program Files\python\python.exe`，找不到则回退 PATH 中的 `python`。Node 仅用于 `node --check` 校验插件语法。

## 4. 目录

| 路径 | 内容 |
|---|---|
| `ops/bus/` | 任务卡 21 张、回执 20 份、状态、审计/校验/接管/库存脚本 |
| `ops/probes/source_ledger.py` | 18 源信源探针与分级（A/B/C/D） |
| `plugins/factory_ops/` | OpenCode V2 本地插件：status/audit/case/probe（只读、留痕） |
| `reports/cases/` | 幻方、灵均 V1–V4；T16–T20 案例库；来源探针 JSON |
| `reports/compliance/` | T19 信源合规地图（G/Y/R 三层 + 5 类不碰） |
| `reports/mvp/` | T0 范围、OpenCode Go 决策、插件调用日志说明 |
| `reports/sources/` | 18 源探针报告（14 可用、4 `UNVERIFIED`） |
| `.opencode/command/` | 接管/状态命令（旧版中文文件名，保留只读） |
| `constitution.json` | 宪法 v3.45.0，98 条硬约束 |

## 5. 证据与风控

- A=官方/监管原文；B=独立媒体/研究；C=社区线索；D=付费墙/超时/不可达，**不作证据**。
- 每条外部事实需 URL + 状态码 + 抓取时间 + 数字口径；不确定写 `UNVERIFIED`。
- 硬风控：单笔 ≤5%、单赛道 ≤20%、无退出不投、五维任一 ≤2 不投。
- 边界：不碰内幕/非公开数据、不自动下单、不卖 alpha、不做基金、不给投资建议、不采个人信息；人类保留否决权。

## 6. DS 网页悬浮窗（本机）

`tools/ds_parasite/` = Edge/Chrome 扩展 + 本机桥接（`127.0.0.1:8791`）。在 DS 网页自动捕获对话，落盘到 `reports/ds_capture/`（已加入 `.gitignore`，不上传 GitHub）。用 `factory_ds_latest()` 读取。详见 `tools/ds_parasite/README.md`。

## 7. 插件真实调用证据

`reports/mvp/plugin_calls/calls.jsonl`（含时间戳、工具名、输入、状态、sha256、耗时）与同目录 `README.md`；调用发生在 OpenCode V2 当前会话，不是演练或单测。其中两次 `factory_audit` 失败与修复均保留在日志中。

## 8. 状态与发布

- 本地：T0/T1/T2 三卡 ACCEPT(PASS)；`check_card` 21/21、`check_handoff` PASS、`status` open=2/done=18/cancelled=1。
- GitHub：**未上传**。原因：`gh auth status` 未登录、无目标 repo 认证。`push.ps1` 不会伪造上传，需用户先登录并给出 repo URL。

## 9. OpenCode Go

结论：**暂不订阅**。官方明确 optional；当前免费 `hy4-flash-free` + 本地 `factory-proxy` 已覆盖 MVP。详见 `reports/mvp/T0_opencode_go_decision.md`。
