# T0 · 工厂 MVP 范围 / 签收标准 / 同行定位与边界（2026-11-21）

- task_id: T0
- 状态: T0–T2 收束稿；旧版文档保留只读，只增不删
- 一句话: 把"破产场景 + 关系变现"改造成可复用、有数据飞轮的市场业务；MVP 只交付**可验证的研究与调度能力**，不交付投资决策或自动交易。

## 0. 结论先行

1. T0 = MVP 范围/签收/发布卡；T1 = 某量化机构A案例；T2 = 某量化机构B案例。三卡按 V1–V4 并联，旧卡只读。
2. 同行用 AI / 探针的定位：**投研辅助 + 交叉验证 + 补充论据 + 非结构化数据处理 + 风控留痕**，不是独立 alpha 来源；人保留否决权。
3. MVP 的证据必须是插件**真实会话调用**留下的日志，不是演练、不是单测、不是"我觉得能用"。
4. T14/T15 保持 `UNVERIFIED`，不进 MVP 签收范围；0/10 访谈、0/3 付费试点、0/1 律所、0/1 实习生，不以"感兴趣"代替"愿付费"。
5. GitHub 上传目前受认证阻塞；只做本地 release 仓库 + 推送脚本，不写成已上传。

## 1. 事实分级（全工厂统一）

| 级别 | 定义 | 能否作证据 |
|---|---|---|
| A | 官网/监管/交易所/公司公告原文；官方文档 | 可，但只证明"它公开说了什么" |
| B | 独立主流媒体、行业研究、学术、协会报告 | 可交叉，不单独证明因果 |
| C | 百科、社区、二手博客 | 只作线索，不作唯一依据 |
| D | 付费墙、超时、521/412、无快照的转述 | **不可作证据**，标 `UNVERIFIED` |

每条外部事实需带：URL + HTTP 状态码 + 抓取时间 + 关键数字口径。不确定即写 `UNVERIFIED`，不补脑。

## 2. 同行怎么定位和使用 AI / 探针

### 2.1 样本对照（来源见 §7）

| 样本 | 公开事实（A/B） | 对 AI 的定位 | 对我方的可复制性 |
|---|---|---|---|
| 某量化机构A / DeepSeek | 2015 成立；2021 AUM 破千亿；算力从萤火一号到萤火二号（万卡 A100 级）；DeepSeek 2023 成立，无外部融资 | AI 是**主业与基础设施**，不是旁路探针；投研、算力、模型自研闭环 | 低：算力/人才/资本不可复制；只抄"数据→模型→验证"的流程思想，不抄规模 |
| 某量化机构B | 2014-06 成立；2024-02-19 开盘约 1 分钟沪 11.95 亿 + 深 13.72 亿卖出，被限制交易、公开谴责，次日道歉 | ML/程序化是**执行工具**；这次事故说明模型/执行风控失效会被监管直接定性 | 低：不复制交易速度；复制"合规留痕 + 人类否决 + 异常阈值"机制 |
| 量化行业圆桌（2025-11） | AI 把数据边界扩到公告文本/舆情/论坛/图像/音视频；非结构化数据存在污染与时间错误；需清洗、人工校验、结构化；深度模型不一定可解释但更有效；需有经验人类参与和控制 | **投研效率 + 非结构化处理 + 因子/假设生成 + 人工复核** | 高：直接作为我方探针与交叉验证的方法论 |
| AIMA 对冲基金调研 | 多数机构用通用开放版；约 1/3 无限制使用，43% 受内部 AI policy 约束；机构也在自建 GenAI 应用 | **受政策约束的辅助工具**，不是无人值守决策 | 高：抄"AI policy + 留痕 + 人不被替代" |

### 2.2 明确回答用户问题

> 是探针交叉验证和补充论据作用，还是别的？

**是，但不止。** 准确表述为五类用途，按优先级：

1. **交叉验证**：同一事实用 ≥2 个独立信源核对，不一致就降级或标 `UNVERIFIED`；这是当前 18 源信源探针的主用途。
2. **补充论据**：把媒体/公告/处罚等外部事实接入案例卡，补齐"我不能拿到的访谈与试点"之外的公开证据；不替代访谈。
3. **非结构化数据处理**：公告、裁判文书、处罚 PDF、网页抓取后的清洗与结构化（T17/T19/T20 已落）。
4. **假设生成与反证**：用 V1–V4 四版并联主动写"可推翻条件"，由人决定采纳与否。
5. **风控与合规留痕**：五维评分、红线、信源级别、调用日志都进审计链，便于事后复算。

**不是**：独立 alpha 来源、自动下单、投资建议、内幕信息通道、对客户承诺收益。

### 2.3 边界：做什么 / 不做什么

| 做 | 不做 |
|---|---|
| 公开信源抓取、分级、交叉验证 | 内幕/非公开数据、未公开调研、个人信息 |
| 破产场景线索的公开证据整理 | 自动下单 / 无人值守交易 / 代客理财 |
| V1–V4 案例卡、可推翻条件、评分 | 卖 alpha / 发基金 / 提供投资建议 |
| 插件真实调用 + 日志 + 回执 + 审计 | 演练、单测冒充真实调用 |
| 人类逐条否决；留痕可复算 | AI 自动通过投资决策 |

**硬风控（继续有效）**：单笔 ≤5%、单赛道 ≤20%、无退出不投、五维任一 ≤2 不投；触线即否，不因 AI 结论放宽。

## 3. MVP 范围

### 3.1 纳入签收

- **调度台**：`ops/bus/` 状态卡、回执、审计器、完整性校验、接管文档、库存清单（已 18 项）。
- **信源探针**：`ops/probes/source_ledger.py`，18 源实测，14 可作证据、4 个 `UNVERIFIED`。
- **合规地图**：`reports/compliance/T19_source_compliance_map.md`，G/Y/R 三层 + 5 类不碰。
- **案例库**：T1 机构A、T2 机构B、T16 大厂锚点、T17 破产 10 案、T18 开发者墓志铭、T20 顾问观察表。
- **插件能力**：`plugins/factory_ops` 暴露 `factory_status` / `factory_audit` / `factory_case` / `factory_probe`，在真实会话调用并留下带时间戳的 JSONL 日志。
- **发行包**：`dist/ai-factory-mvp/`，含 README、单命令自检、bus、probe、plugin、案例、接管说明。
- **三卡收束**：T0/T1/T2 回执 ACCEPT(PASS)，`state.json` 三卡 done。

### 3.2 明确不纳入

- T14（10 访谈）/ T15（3 付费试点 + 律所 + 实习生）：全部 `UNVERIFIED`，不伪造、不进 done。
- 任何真实投资动作、下单 API、客户资金、收益承诺。
- 对 DSH / WorkBuddy 配置的修改；密钥/凭证的读取或写入。
- 把模型输出直接当事实：所有 AI 结论仍标来源级别与不确定性。

## 4. 签收标准（逐条可复算）

| # | 检查 | 通过条件 | 命令 / 证据 |
|---|---|---|---|
| 1 | 卡片 | T0–T20 全 PASS ≤32 行 | `python ops/bus/check_card.py` |
| 2 | 回执 | T0/T1/T2 三份 ACCEPT 且 status=PASS | `python ops/bus/audit.py`（只看三张） |
| 3 | 接管 | 17→20 份回执扫描，只认 `T<数字>.json` | `python ops/bus/check_handoff.py` |
| 4 | 状态 | open=2（仅 T14/T15）done=18 cancelled=1（T10） | `python ops/bus/status.py` |
| 5 | 工具 | 4 个工具各 ≥1 次真实调用，日志含 ts/输入/摘要/sha | `reports/mvp/plugin_calls/*.jsonl` |
| 6 | 案例 | V1–V4 齐全，三问三红线，证据 A/B/C/D 齐全 | `reports/cases/highflyer_v4.md`、`lingjun_v4.md` |
| 7 | 探针 | 18 源 probe 报告 + 4 个 `UNVERIFIED` 明示 | `reports/sources/probe_20261121_125528.md` |
| 8 | 发行 | dist 可单命令自检；git 已 commit；未认证不伪造 push | `dist/ai-factory-mvp/README.md` |
| 9 | 风控 | 无自动下单、无投资建议、T14/T15 未标完成 | 人工核对 + Constitution 98 条 |

## 5. 发布清单

- 仓库名建议：`ai-factory-mvp`；分支 `main`；本地路径 `dist/ai-factory-mvp/`。
- 内容：`README.md`、`ops/bus/`、`ops/probes/`、`plugins/factory_ops/`、`reports/{cases,compliance,mvp,sources}/`、`constitution.json`、`.opencode/command/`、`push.ps1`、`selftest.ps1`。
- 排除：`.git`、密钥/凭证、`*.bak-*`、`__pycache__`、本机绝对路径依赖（README 用相对路径）。
- 上传状态：**本地 release 已组装并 commit；GitHub 未认证，未 push**。`push.ps1` 输出要求先 `gh auth login` 或配置 remote 后执行。

## 6. OpenCode Go

详见 `T0_opencode_go_decision.md`。结论：暂不订阅；当前免费 `hy4-flash-free` + 本地 `factory-proxy` 已覆盖 MVP；官方明确 optional，限额按模型美元额度且 5h/周窗口受限，区域与隐私需自配。

## 7. 来源

| ID | 级别 | URL / 说明 | 状态 / 时间 |
|---|---|---|---|
| S1 | A | `https://www.sse.com.cn/disclosure/credibility/regulatory/news/c/c_20240220_5735603.shtml`（上交所处罚通报） | 200，2026-11-21T13:45+08:00 |
| S2 | A | `http://dataclouds.cninfo.com.cn/sjother/regulatory_announcement/szse/93d63b3ae2ac11ee89b1fa163ebe0297.pdf`（深交所公开谴责决定） | 206，同上 |
| S3 | A | `https://www.high-flyer.cn/`、`https://www.deepseek.com/`、`https://www.lingjuninvest.com/`（官网存在性） | 206/206/200，同上 |
| S4 | B | `https://wallstreetcn.com/articles/3737003`（机构A规模/算力） | 200，同上 |
| S5 | B | `https://www.21jingji.com/article/20260114/herald/c28662157ae4f0d9f2c7c944101a35ad.html`（2025 收益） | 206，同上 |
| S6 | B | `https://epaper.cs.com.cn/zgzqb/html/2025-11/29/nw.D110000zgzqb_20251129_1-A05.htm`（量化行业 AI 圆桌） | 检索快照 2026-11-21 |
| S7 | B | `https://www.aima.org/static/a4f9bc40-8c32-42e6-87f52bd89f6e1a82/How-hedge-funds-are-leveraging-Gen-AI-to-get-ahead.pdf` | 检索快照 2026-11-21 |
| S8 | A | `https://opencode.ai/docs/console/go/` | 200，2026-11-21T13:54+08:00 |
| S9 | D | `https://www.lingjun.com.cn/` | 超时，未作证据 |

> 注：以上 URL 的 sha256 与字节数见 `reports/cases/T1T2_sources_probe.json`；本表的"检索快照"项未逐字存档全文，标 A-/B-。
