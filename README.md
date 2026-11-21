# AI Factory MVP（离线发行包 · 2026-11-21）

> 这是**本地 release 仓库**，尚未上传到 GitHub（当前环境 `gh auth status` 未登录）。不要把它说成已发布。

## 1. 它解决什么

把"名酒商行关系变现 / 破产捡漏"从个人经验转成可复算的公开信息流水线：信源探针 → 分级证据 → 案例卡（V1–V4）→ 回执/审计 → 可调用插件。MVP 只交付**研究与调度能力**，不交付投资决策、自动交易或投资建议。

## 2. 一句话范围

- 纳入：T0–T2（范围/幻方/灵均）、T3–T13（底座）、T16–T20（锚点/破产/合规/观察表）、18 源信源探针、`factory_ops` 四个真实工具、可审计回执。
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
