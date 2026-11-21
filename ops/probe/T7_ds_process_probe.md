# T7 · DS 团队流程探针（可抄清单）

- task_id: T7 ｜ owner: W7 ｜ date: 2026-11-21 ｜ scope: 只读公开仓库 / 论文 / 官方文档
- 结论: 10 条可抄，10 条均可在**一人环境**起步；0 条需要 DS 内部权限。
- 探针成本: ¥0（公开网页与公开仓库，无付费 API）；落地工时另计。
- 证据级别: **A**=官方一手且有代码/正式规范，可本地复核；**B**=官方一手设计文档/原型，关键实现未完整公开；**C**=官方单源叙述，无代码/规范；**D**=传闻或推断（本清单 0 条）。

## 一、可抄清单

| # | 做法（最小可抄动作） | 证据级别与来源 | 成本 | 门槛 | 一人 MVP 形态与验收 |
|---|---|---|---|---|---|
| 1 | **模型可见即已记录**：凡是进入模型请求的内容，必须能从 append-only 会话日志重建；新增模型可见输入必须新增事件。 | **A** · DeepSeek Harness `AGENTS.md` / `docs/architecture.md`（“Model-visible means logged”） | ¥0 / 1–2 人日 | 会写 JSONL 事件与 replay | `events.jsonl` + `replay.py` 派生消息；删掉派生缓存后重放，prompt 字节一致即 PASS |
| 2 | **一切皆插件 + 能力缝**：行为挂在文档化扩展点；一个能力必须同时有 Service Definition / Provider / Consumer 三角；注册即 effect，返回 disposer。 | **A** · DSH `README`（everything-is-a-plugin）、`docs/architecture.md`（Capability seams） | ¥0 / 2–4 人日 | TypeScript/Node 或等价 DI | `plugin.json` + registry（register 返回 dispose）+ 同一接口两个 provider；卸载后无残留 handler 即 PASS |
| 3 | **编号文档链 + 注意力预算**：文档按 000→008 顺序读，每篇只依赖前一篇；每条消息/通知/设置都必须“让人行动或给出可用结果”，否则删除。 | **B** · `dsh-superagent` `docs/000-philosophy.md`、README 文档目录 | ¥0 / 1 人日 | 写作纪律 | `docs/000-philosophy.md`…`005-operations.md` 各 ≤1 页；新人仅按文档可从零跑通即 PASS |
| 4 | **工单状态机 + 人类接管点**：每个工单只处于一个阶段；`person/*` 表示必须人介入；后台工作有上限，超时杀掉并留下恢复说明。 | **B** · `dsh-superagent` `docs/003-execution.md`（Ticket stages / Failure and recovery） | ¥0 / 2–3 人日 | 会写状态机与持久化 | 状态：`queued/working/idle/person-answer/person-review/person-blocked/person-failed`；杀进程重启后工单状态与未读消息不丢即 PASS |
| 5 | **授权前置 + 只记录模式**：只在被直接请求、或团队书面规则允许时行动；主动工作先 `record-only` 跑一段，确认“本来会做什么”后再放开。 | **B** · `dsh-superagent` `docs/002-authorization.md`、`000-philosophy.md` | ¥0 / 1 人日 | 一张 allowlist + 规则表 | `allowlist.yaml` + `rules.yaml` + `dry_run: record_only`；未授权请求只写审计不执行即 PASS |
| 6 | **一命令门禁 + 破坏性变更单**：交付前只跑一条 `check`（typecheck + test + build + 文档链接）；每个外部可感知的破坏性变更立刻写升级说明。 | **A** · DSH `AGENTS.md`（`test:coverage`/`build`/`doc-sync`/pre-push）、`dsh-superagent` README（`pnpm check`） | ¥0 / 0.5 人日 | 会写 Makefile/CI | `make check` 一条命令；故意断一个文档链接或类型错误必须 FAIL；`UPGRADE.md` 有本次变更即 PASS |
| 7 | **公开失败尝试 + 可推翻声明**：交付物固定写“失败/未采用方案、成本、可推翻条件”；不把“跑了”写成“成了”。 | **A** · DeepSeek-R1 论文 G.2 “Unsuccessful Attempts”（PRM/MCTS）；V3 技术报告（2.788M H800 GPU 小时、无不可恢复 loss spike/rollback） | ¥0 / 0（模板） | 诚实披露 | 每份报告含 `failed_attempts`、`unverified`、`falsifiable` 三栏；缺一栏即拒收 |
| 8 | **每日一个可运行组件 + 生产验证门槛 + 先拆依赖**：连续 5 天每天发 1 个小组件；只发“有文档、已部署、生产验证过”的东西；整库开不动时先拆独立模块再贡献。 | **A** · `open-infra-index` 202502 Open Source Week（5 repos, one daily drop；“documented, deployed, battle-tested… No vaporware”）；`OpenSourcing_DeepSeek_Inference_Engine/README.md`（拆分而非硬开源整库） | ¥0 / 5 人日 | 5 天连续交付 | 5 个目录，各自 README + benchmark + test + LICENSE；每个都能从干净环境一条命令跑通即 PASS |
| 9 | **协议转换层 + 黄金样例**：用统一 Conversation IR 解耦“请求格式 / prompt 渲染 / tokenizer / 输出解析”，每层可用 mock 后端单测。 | **A** · `deepseek-recipe` README（Messages / Chat Completions / Responses → Conversation → prompt → tokens） | ¥0 / 2–3 人日 | Python 或 Rust | `Conversation` IR + 3 个适配器 + 20 条 golden prompt/response 快照；改一处渲染只挂对应快照即 PASS |
| 10 | **证据型交付：trace / 配置 / 数据管道**：性能声明必须附原始 trace 与完整并行配置；数据处理用 DuckDB + 对象存储，不养长驻服务。 | **A** · `profile-data` README（train/prefill/decode trace）；`smallpond` README（DuckDB + 3FS，PB 级、无长驻服务） | ¥0 / 1–2 人日 | 会用 PyTorch Profiler / DuckDB | 每个性能数字附 `.json` trace + 复现命令；数据侧 10GB parquet 分区聚合可复跑即 PASS |

## 二、抄得动设计、抄不动运行（不计入 10 条）

- **DeepEP / DeepGEMM / DualPipe / 3FS / DeepInfer**：证据均为 **A**（公开代码与文档），但运行门槛是 Hopper/SM100、NVLink/RDMA、数百节点存储，**一人环境不可复现**。只抄三个设计点：计算-通信重叠、专家负载均衡、推理/训练解耦；不抄“我们也能跑”的结论。
- **组织流程**（如“小团队、自然分工”）：本次未采用访谈类单源材料，避免把“听说”写成事实；故本清单 **0 条 C/D**。

## 三、验收自检

| 验收项 | 结果 | 证据 |
|---|---|---|
| ≥3 条可在一人环境落地 | **PASS，10/10** | 第一节 #1–#10 的“一人 MVP 形态与验收” |
| 每条有来源 | **PASS，10/10** | 下表来源清单，均为官方 GitHub / arXiv |
| 0 条需要内部权限 | **PASS，0 条** | 全部为公开仓库、公开论文、公开文档；未访问 DS 内部系统 |
| 不编造流程 | **PASS** | 每条只写公开材料可核对的动作；推断处标“设计点”而非“事实” |
| 预算 ¥10 / 3h | **PASS（探针本身）** | 付费调用 ¥0；公开抓取与整理约 2h；落地工时不计入探针预算 |

## 四、来源清单（访问日 2026-11-21）

1. https://github.com/deepseek-ai/deepseek-harness — README（everything-is-a-plugin）、`AGENTS.md`、`docs/architecture.md`、`CONTRIBUTING.md`
2. https://github.com/deepseek-ai/dsh-superagent-prototype — `docs/000-philosophy.md`、`002-authorization.md`、`003-execution.md`、README（`pnpm check`）
3. https://github.com/deepseek-ai/open-infra-index — 202502 Open Source Week；`OpenSourcing_DeepSeek_Inference_Engine/README.md`
4. https://arxiv.org/abs/2501.12948 — DeepSeek-R1，G.2 Unsuccessful Attempts（PRM / MCTS）
5. https://arxiv.org/abs/2412.19437 — DeepSeek-V3 Technical Report（2.788M H800 GPU hours；无不可恢复 loss spike / rollback；DualPipe / FP8 / MTP）
6. https://github.com/deepseek-ai/deepseek-recipe — 协议转换、prompt 渲染、tokenizer、输出解析
7. https://github.com/deepseek-ai/profile-data — 训练/预填/解码 profiling trace 与并行配置
8. https://github.com/deepseek-ai/smallpond — DuckDB + 3FS 数据管道
9. https://github.com/deepseek-ai/DeepEP 、`DeepGEMM`、`DualPipe`、`3FS`、`DeepInfer` — 仅用于“抄不动运行”的边界说明

## 五、未验证 / 可推翻

- 未逐条执行 DS 仓库代码；A 级表示“公开可复核”，不等于“本窗口已复现”。
- “公开失败尝试/稳定性披露”是从论文写作事实提取的**披露模板**，不推断 DS 内部必有同名流程。
- 成本仅为公开资料整理成本；若要把 #1–#10 全部落地，按表内工时另计，不包含 GPU/存储费用。
- 可推翻条件：任一来源链接失效、或公开仓库删除对应规范/代码，则对应行降级或作废。
