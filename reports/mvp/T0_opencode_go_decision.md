# T0 · OpenCode Go 订阅决策（2026-11-21）

- task_id: T0
- 结论: **暂不订阅**。Go 对个人是可选 provider，不是 OpenCode 的前置条件；当前会话已在免费 `hy4-flash-free` 上，工厂另有本地 `factory-proxy` 0 成本模型，MVP 没有用尽额度。
- 决策级别: 工厂运营决策（非投资建议）；事实来自官方文档 A 级，引用见下表。

## 1. 它是什么（A 级事实）

| 项 | 内容 | 来源 |
|---|---|---|
| 定位 | 固定月费的模型订阅，作为 OpenCode 的一个 provider；官方写明 completely optional | S1 |
| 价格 | Go $10/月；Go Plus $40/月；Go Teams $20/人/月（最少 2 人） | S1 |
| 计量 | 不是按"请求数"无限用：每个模型有月度美元额度；5 小时窗口最多用月额度的 20%，周窗口 50%，周一 00:00 UTC 重置 | S1 |
| 额度差异 | 不同模型月额度不同（官方举例：DeepSeek V4.1 Flash $100、Kimi K3.1 Pro $15）；同账号各模型共享一份 allowance | S1 |
| 超限 | 可切回免费模型，或开启 Extra Usage 用 Console 余额按量付费；Go Teams 默认开 Extra Usage | S1 |
| 客户端 | 需 `/connect` 选 OpenCode Go 并填 API key，再用 `/models` 选 `opencode-go/<model-id>` | S1 |
| 区域/隐私 | 默认允许地区为 Europe & US；付费训练端点默认禁用；中国请求在无保存隐私设置时允许 Global；部分模型需手动开 Global 或训练开关 | S1 |
| 留存 | 多数国产/开放模型标 0 days；Grok/GPT/Claude 30 days、Gemini 55 days；Contributor 类以数据训练换低价 | S1 |
| 无锁定 | 官方目标明确：可与任意其他 provider 并用，no lock-in | S1 |

## 2. 价值（对工厂）与边界

- 价值：
  1. **可预测的单价**——把零散按量付费换成固定月费，适合稳定、高频、可分散到多个模型的编码 agent 流量。
  2. **经过测试的开放权重模型**——官方筛选并基准测试，减少自己挑 provider/量化/可用性的工作量。
  3. **跨工具复用**——同一订阅可在 OpenCode、Claude Code、Codex、Pi 等使用（官方控制台页；S2）。
  4. **超额度有退路**——免费模型或余额兜底，不会直接停摆。
- 边界：
  1. **不是"无限 GPT"**：月度美元额度按模型不同，5 小时/周窗口先触顶；官方估算的请求数是典型场景，不等于我方真实负载。
  2. **不是质量升级保证**：模型清单"may change"，且低价来自批量折扣/预留算力，不是模型本身更高配。
  3. **不是隐私豁免**：区域与数据训练策略需自己在 Settings › Privacy 配置；Contributor 类明确允许用提示词训练。
  4. **不替代本地/免费路线**：免费模型有日限但可继续用；本地 `factory-proxy` 为 0 成本，不消耗订阅。
  5. **不是投资能力**：更便宜的 token 不会把 AI 从"交叉验证/补充论据"变成独立 alpha，见 `T0_MVP_SCOPE.md`。
  6. **有支付与合规面**：需 Console 账号、账单信息、API key；密钥不进任何产物，不写入本仓库。

## 3. 我方决策规则（触发才重审）

| 触发条件 | 动作 |
|---|---|
| 连续 2 周免费 + 本地模型不够用，且真实账单 > $10/月 | 买 Go 一个月做 A/B，按 `opencode.allowance` 记账 |
| 需要跨 Claude Code / Codex 的稳定开放模型访问 | 评估 Go；仍不买 Teams（当前单窗口，无 2 人刚需） |
| 月度账单稳定 > $30 且多模型都撞 5 小时窗 | 评估 Go Plus；先算 $30 差价买到的额度是否大于 $30 按量额度 |
| 涉及非公开投研材料/个人信息 | 无论是否订阅，都不走任何云端付费端点（工厂红线） |
| 仅为"支持项目"或担心错过 | 不订阅 |

## 4. 来源

- S1 A：`https://opencode.ai/docs/console/go/`，HTTP 200，抓取 2026-11-21T13:54+08:00（官方文档，含价格/限额/隐私表）。
- S2 A：`https://opencode.ai/console/go`，检索快照 2026-11-21，含"works in OpenCode, Claude Code, Codex and Pi"与 $10/$40 定价；未逐字存档全文，标 A-（官方营销页）。
- S3 B：`https://www.toolcolumn.com/learn/opencode-go-usage-limits-by-plan`，检索快照 2026-11-21，用于交叉核对 20%/50% 窗口与额度表；B 级仅作补充，不单独作决策依据。

> 不确定项：模型清单与限额官方声明会变化；具体某模型在某日的可用性与价格标 `UNVERIFIED`，订阅前以 Console 实时页为准。
