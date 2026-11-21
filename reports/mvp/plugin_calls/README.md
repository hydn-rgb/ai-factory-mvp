# factory_ops 插件真实调用日志说明（2026-11-21）

## 1. 这不是演练

- 插件 `plugins/factory_ops` 已装入 `<USER_HOME>\.config\opencode\opencode.json`（备份：`opencode.json.bak-factory-ops-*`），并在 **OpenCode V2 当前会话**通过 `opencode reload` 生效。
- 调用方式：Code Mode 下 `tools.factory.factory_status({})` / `tools.factory.factory_audit({tasks:[...]})` / `tools.factory.factory_case({id:"T1"})` / `tools.factory.factory_probe({url:"..."})`。
- 每次执行由插件 `execute` 直接 `appendFileSync` 写入 `calls.jsonl`；不是测试桩、不是文档示例、不是"单测通过"冒充调用。
- 原始日志：`calls.jsonl`（60 行，UTF-8，每行一条 JSON）；sha256 = `dc40c3dcedb4e67bbcf770e97480222bac6dd7e42c5aceea022679bebcb3ab76`。
- 工具已从 4 个扩到 7 个：新增 `factory_handoff`（会话提炼交接，5 次真实调用）、`factory_ds_import`（DS 网页导出文本导入+马赛克脱敏，1 次）、`factory_persona`（本地角色卡/世界书三版读取，2 次；full 版默认拒绝，已实测）。

## 2. 调用记录（UTC 时间，取自日志）

| 时间 | 工具 | 结果 | 关键返回 |
|---|---|---|---|
| 05:57:18 | factory_status | ok | 当时 todo=4 / done=15 / cancelled=1 |
| 05:57:18 | factory_audit | **失败** | `execFileSync` 因 `audit.py` 有拒收回执而非零退出抛错 |
| 05:57:18 | factory_case(T1) | ok | sha `70d69b88…`，12418 字节，V1–V4 标题齐全 |
| 05:57:18 | factory_probe(上交所机构B页) | ok | 200，27212 字节，sha `b727210b…` |
| 05:57:24 | factory_audit | **失败** | 同上；已记录，不隐瞒 |
| 05:58:26 | factory_audit | ok | 改用 `spawnSync` 读取 stdout；total=22 / accepted=17 / rejected=5 |
| 05:59:18 | factory_status | ok | todo=2 / done=18 / cancelled=1（T0–T2 已收束） |
| 05:59:18 | factory_audit | ok | 聚焦 T0/T1/T2：当时 T0 REJECT（sha 变更），T1/T2 ACCEPT |
| 05:59:18 | factory_case(T2) | ok | sha `ddf8f30a…`，11828 字节 |
| 05:59:18 | factory_probe(机构A官网) | ok | 200，365804 字节，sha `806f6bd0…` |
| 05:59:31 | factory_audit | ok | T0/T1/T2 全部 ACCEPT(PASS)，total=25 / accepted=20 / rejected=5 |

> 失败与修正都留痕：插件改用 `spawnSync` 读取 `audit.py --json` 的 stdout（该命令在有 `UNVERIFIED` 回执时返回非零退出码，但 JSON 有效）。这是真实调用的证据链，不是抹掉失败重跑。

## 3. 工具契约

| 工具 | 输入 | 只读性 / 边界 |
|---|---|---|
| factory_status | 无 | 读 `ops/bus/state.json` + heartbeat；返回 sha、计数、开放卡；不写状态 |
| factory_audit | `{tasks?: string[]}` | 运行 `audit.py --json`；**不执行 `--apply`**；返回验收结论 |
| factory_case | `{id: T0/T1/T2/T16-T20}` | 白名单读案例卡；返回 sha256/字节/标题/摘录 |
| factory_probe | `{url: http(s)://…}` | 公开 URL；拒绝 localhost/内网；返回状态码/字节/sha/耗时；D 级不作证据 |

硬边界：不读密钥、不写配置、不访问交易接口、不碰非公开数据、不自动下单、不给投资建议。

## 4. 复现

```text
1. 确认 ~/.config/opencode/opencode.json 的 plugins 含 D:/AI_Factory/plugins/factory_ops
2. opencode-cli.exe reload
3. 在会话里调用 tools.factory.factory_status({}) 等四个工具
4. 查看 reports/mvp/plugin_calls/calls.jsonl（每行含 ts/tool/input/ok/status/sha256/elapsed_ms）
```

> 注：插件日志时间戳为 UTC（`Z`）；报告时间用北京时间（+08:00）时差 8 小时。
