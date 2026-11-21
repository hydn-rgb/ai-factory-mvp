# model_router · OpenCode 会话+任务模型路由

零依赖 OpenCode V2 本地插件。按**会话 + 任务类型**在 DeepSeek flash / pro / 本地 Ollama 之间切换，降低无效花费。

- 插件目录：`D:\AI_Factory\plugins\model_router\`
- 实测环境：OpenCode `v2.2.5`（Desktop 自带 `opencode-cli.exe`）
- 依赖：无。只用 Node 内置模块和 OpenCode 自带插件运行时。
- 不改 DSH / WorkBuddy 配置；不写任何 key。

## 三类能力

1. **任务分类**（可解释）：`code` / `research` / `doc` / `audit`
   - 关键词命中计分，同分按 `audit > research > doc > code` 取。
   - 规则全在 `policy.json`，改 JSON 即可，不用改代码。
2. **模型策略**
   - 默认 `deepseek/deepseek-flash`
   - 重任务升级 `deepseek/deepseek-v4-pro`（长文本 ≥1500 字符，或命中“架构/重构/根因/并发/多文件/迁移…”）
   - 审计类默认 pro
   - 隐私/离线任务走本地 `ollama/qwen2.5:3b-instruct-q4_K_M`
3. **会话覆盖**
   - 手动 `/model` 或 `opencode run --model` 优先，插件不再覆盖该会话。
   - 判定方式：当前会话模型 ≠ 插件上次设置值；新会话模型 ≠ 全局默认模型。
   - 未指定模型时，插件才按任务切换。

## 文件

| 文件 | 作用 |
| --- | --- |
| `index.js` | 插件入口，注册 `prompt` hook；所有异常吞掉并回退默认模型 |
| `router.mjs` | 纯分类/选模逻辑，无 I/O，可单测 |
| `policy.json` | 关键词、任务到模型映射、隐私/重任务规则 |
| `package.json` | 本地插件包声明（`exports.` → `index.js`） |
| `test_router.mjs` | 零依赖机器测试（覆盖验收 1–3 + 策略） |
| `install.ps1` | 写配置前先备份，再把插件加入 `plugins` 数组 |
| `rollback.ps1` | 备份后移除插件；可选 `-DeletePluginDir` |
| `test_log.jsonl` | 每次决策：session / task_type / model / reason |

## 安装

```powershell
# 1) 备份 + 写入全局配置（脚本内部会再备份一次）
powershell -NoProfile -ExecutionPolicy Bypass -File D:\AI_Factory\plugins\model_router\install.ps1

# 2) 重启 OpenCode，或
opencode reload
```

只给某个项目用，不写全局配置：在项目根目录的 `opencode.json` 加

```json
{
  "plugins": ["D:/AI_Factory/plugins/model_router"]
}
```

> 注意：V2 字段是 `plugins`（复数）。本地路径必须是**目录**，单文件会被跳过。旧的 `plugin`（单数）是 V1 弃用字段。

## 回滚

```powershell
# 只移出配置（推荐；代码留着方便再装）
powershell -NoProfile -ExecutionPolicy Bypass -File D:\AI_Factory\plugins\model_router\rollback.ps1

# 或连目录一起删（任务卡要求的最彻底回滚）
powershell -NoProfile -ExecutionPolicy Bypass -File D:\AI_Factory\plugins\model_router\rollback.ps1 -DeletePluginDir
```

然后重启 OpenCode。删除插件目录 + 重启后，OpenCode 会话恢复原生模型选择，行为与装前一致。

## 验证

```powershell
cd D:\AI_Factory\plugins\model_router
node test_router.mjs
```

期望最后输出 `ALL PASS`，并生成 `test_log.jsonl`。

真实 OpenCode 端到端（临时项目配置，不动全局）：

```powershell
# 普通对话：应出现 task_type=doc / model=deepseek/deepseek-flash
opencode run --standalone --auto --format json "请写一个 README 文档标题，只回复一句话"

# 手动指定：应出现 manual_skip，模型保持 pro
opencode run --standalone --auto --format json --model deepseek/deepseek-v4-pro "请写一个 README 文档标题，只回复一句话"
```

## 验收对照

| 卡上验收 | 证据 |
| --- | --- |
| 新建会话 → 日志出现 `task_type` 与 `model` | 真实会话 `ses_e040be...`：`event=switch, task_type=doc, model=deepseek/deepseek-flash` |
| 手动 `/model` 指定 → 插件不覆盖 | 真实会话 `ses_e040bc...`：`event=manual_skip, model=deepseek/deepseek-v4-pro` |
| 插件异常 → 回退默认模型，不阻塞对话 | `test_router.mjs` 的 `switch-error-falls-back-default` / `hook-error-does-not-block` |
| 回滚：删插件目录 + 重启，行为恢复 | 已实测：删除插件副本目录后新建会话仍正常对话，`test_log.jsonl` 不再新增行；`rollback.ps1` 支持 `-DeletePluginDir` |

## 日志字段

```json
{"ts":"2026-11-21T02:34:09.447Z","plugin":"model_router","event":"manual_skip","session":"ses_...","task_type":null,"model":"deepseek/deepseek-v4-pro","reason":"explicit model differs from global default"}
```

`event` 取值：`switch`（实际切换）、`noop`（目标已一致）、`manual_skip`（尊重手动）、`fallback`（切换失败回退）、`error`（异常但未阻塞）。

日志可用环境变量改路径：`MODEL_ROUTER_LOG=D:\path\to\router.jsonl`。

## 边界

- 新会话首次发言前就手动选模型，插件能识别（与全局默认不同即让行）。
- 如果某个 agent 在配置里写死了模型，也会按“已指定”处理，插件不覆盖。
- 本地模型要求本机 Ollama 已启动且存在 `qwen2.5:3b-instruct-q4_K_M`；否则切换失败会自动回退 DeepSeek flash，不会阻塞。
- 分类是关键词规则，不是语义模型；宁可解释清楚，也不暗中调贵模型。需要更准就扩 `policy.json` 的关键词。
