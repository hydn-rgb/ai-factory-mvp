# factory_handoff · 会话交接（免人肉传话）

- 工具：`tools.factory.factory_handoff({ summarize?: boolean })`
- 已真实调用；样例：`handoff_2026-11-21T06-19-56-619Z.md`（session `ses_e4ab…`，messages 116，tools 14，paths 62，sha256 见文件头）
- 产物：`reports/mvp/handoff/handoff_<UTC时间>.md`，含六节：用户目标 / 关键结论 / 已完成与工具调用 / 未完成风险 / 文件指针 / 模型提炼（可选）。

## 用法

1. 在当前会话调用 `factory_handoff()` → 得到路径与 sha。
2. 新开会话时只发一句：`读 <路径>，sha 校验后按里面的文件指针继续，不要人肉传话。`
3. 需要更紧凑的总结时调用 `factory_handoff({summarize:true})`：会用当前 provider 压缩上下文（**会把上下文发给该 provider**）；默认 false，只做本地确定性提炼。

## 边界

- 提炼是摘要，不是原文；原文仍以 session id 为准。
- 默认过滤英文内部推理行，但仍可能夹带计划性条目；关键决策请人工复核。
- 不含密钥；若会话里出现过敏感信息，分享 handoff 文件前先自行检查。
