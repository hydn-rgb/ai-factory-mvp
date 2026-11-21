# ops/bus · 一窗口一任务总线

## 启动
1. 共享查看：`opencode web --port 4096`，另一个窗口 `opencode attach http://localhost:4096`
2. 一任务一会话（推荐）：每个窗口新开 session，只读自己的 `tasks/Tn.md`

## 规则
- 只传指针（路径 + sha），不传摘要
- 回执六段：task_id / owner / status / artifact / sha / rows（缺一即 REJECT）
- `status=UNVERIFIED` 有效，但不进 done
- 一任务一窗口；同一任务不得两个 owner
- 写前校验 mtime/sha，不一致就停

## 校验
- `python ops\bus\status.py` → open/心跳/回执一屏
- `python ops\bus\audit.py --apply` → 验收并推进状态
- `python ops\bus\check_card.py` → 卡片完整性
- `python ops\bus\check_handoff.py` → 回执完整性
- 接管先读 `HANDOFF.md`

## 目录
- `tasks/T*.md` 任务卡（≤20 行）
- `out/T*.json` 回执
- `state.json` 谁在做什么
