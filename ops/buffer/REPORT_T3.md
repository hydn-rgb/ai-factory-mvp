# T3 · DSH 缓冲层 校验报告

- 生成时间: 2026-11-21T10:33:05
- 生成器: `<AI_FACTORY_ROOT>\ops\buffer\dsh_buffer.py`
- 产物: `<AI_FACTORY_ROOT>\ops\buffer\dsh_buffer.py`
- 产物 sha256: `d3916e03f542c4b3b6918fd57e1723a01e5be6fb6056168befc58d0769debec9`
- 自检: **21/21 PASS**

## 一、结论

四条链路已落地，21 项自检全绿（级别 **L1 本地冒烟**）。四条验收均表现为“拒收”，不是“观察通过”。

| 对象 | 值 |
|---|---|
| 任务卡 | `<AI_FACTORY_ROOT>\ops\bus\tasks\T3.md`（21 行 / 上限 20，输入缓冲 REJECT） |
| state.json | `<AI_FACTORY_ROOT>\ops\bus\state.json`（本任务 status=todo） |

> 回执核验结果见 `ops/buffer/verify_T3.json` 与 `ops/bus/out/T3.json`。回执要绑定本报告 sha，故不能把回执结论写进本报告（避免自指）。

## 二、四条链路

| 链路 | 实现 | 触发的拒收码 |
|---|---|---|
| 1 输入缓冲 | `read_task_card()` / `handoff_to_dsh()` | `CARD_TOO_LONG`、`CARD_CARRIES_HISTORY`、`CARD_MISSING` |
| 2 输出缓冲 | `validate_receipt()` | `field:*`、`sha:*`、`claim:*`、`artifact:*` |
| 3 状态缓冲 | `validate_receipt()` + `owner_duplicates()` | `state:owner_unique`、`state:owner_match`、`state:status_match` |
| 4 安全缓冲 | `guard_write()` / `propose_change()` | `PROTECTED_FOR_DSH`、`safe:no_protected_write` |

关键设计：`status` 只表示“本次产物可验”，不表示“任务已入账”。对 state.json 的声明必须单列 `state_claim` 并接受比对——避免“自述完成”直接冒充当板状态（NEG-A11 / NEG-J01）。

## 三、验收四条（机器可判）

| 验收 | 结果 | 自检项 |
|---|---|---|
| 验收① 伪造“已完成” → 拒收 | **PASS** | 1 项 |
| 验收② sha 不符 → 拒收 | **PASS** | 3 项 |
| 验收③ 同一任务两个 owner → 拒收 | **PASS** | 2 项 |
| 验收④ DSH 直写宪法/审批 → 拒收并记事件 | **PASS** | 5 项 |

## 四、自检明细

| # | 检查 | 结果 | 证据 |
|---|---|---|---|
| 1 | 输入缓冲: 20 行卡放行 | PASS | `[]` |
| 2 | 输入缓冲: 21 行卡拒收 | PASS | `['CARD_TOO_LONG:21>20']` |
| 3 | 输入缓冲: 夹带全史拒收 | PASS | `['CARD_CARRIES_HISTORY:## 全史']` |
| 4 | 输入缓冲: 只传卡不传全史 | PASS | `['card', 'lines', 'ok', 'reasons', 'sha', 'task_id']` |
| 5 | 输出缓冲: 六字段 + 五要素齐全 → 放行 | PASS | `[]` |
| 6 | 验收① 伪造已完成 → 拒收 | PASS | `['claim:level', 'claim:command', 'claim:exit_code:None', 'claim:evidence:None', 'claim:request']` |
| 7 | 输出缓冲: 退出码非 0 的 PASS → 拒收 | PASS | `['claim:exit_code:1']` |
| 8 | 输出缓冲: 缺 rows → 拒收 | PASS | `['field:rows:None']` |
| 9 | 验收② sha 不符 → 拒收 | PASS | `['sha:full_match:3bbe88d931e0b200229b2c6b6b3c8c148d15273060c87199697f1743337a1b23']` |
| 10 | 验收② 截断 sha 未声明 → 拒收（NEG-E5） | PASS | `['sha:truncation_declared:sha_len=None len=16']` |
| 11 | 验收② 截断 sha 已声明 → 放行 | PASS | `[]` |
| 12 | 验收③ 同一 owner 领两个任务 → 拒收 | PASS | `['state:owner_unique:W20 <- T20,T21']` |
| 13 | 验收③ 回执 owner ≠ state.json owner → 拒收 | PASS | `['state:owner_match:state=W99 receipt=W20']` |
| 14 | 状态缓冲: 声称 PASS 而 state.json 仍 todo → 拒收 | PASS | `['state:status_match:claim=PASS state=todo']` |
| 15 | 验收④ 回执声明写宪法 → 拒收 | PASS | `['safe:no_protected_write:D:\\AI_Factory\\ops\\buffer\\test_tmp\\20261121_103305_204036\\constitution.json -> constituti` |
| 16 | 验收④ DSH 直写宪法 → 拒收 | PASS | `{'allowed': False, 'reason': 'PROTECTED_FOR_DSH', 'rule': 'constitution.json', 'event': 'DSH_PROTECTED_WRITE_REJECTED'}` |
| 17 | 验收④ DSH 直写审批 → 拒收 | PASS | `{'allowed': False, 'reason': 'PROTECTED_FOR_DSH', 'rule': 'progress/approvals.jsonl', 'event': 'DSH_PROTECTED_WRITE_REJE` |
| 18 | 验收④ DSH 直写任务卡 → 拒收 | PASS | `{'allowed': False, 'reason': 'PROTECTED_FOR_DSH', 'rule': 'ops/bus/tasks/*', 'event': 'DSH_PROTECTED_WRITE_REJECTED'}` |
| 19 | 验收④ 拒收事件已落盘 | PASS | `events=4` |
| 20 | 安全缓冲: 非保护路径放行 | PASS | `{'allowed': True, 'reason': 'NOT_PROTECTED', 'rule': ''}` |
| 21 | 安全缓冲: 只能提案且不写目标 | PASS | `<AI_FACTORY_ROOT>\ops\buffer\test_tmp\20261121_103305_204036\proposals\prop-20261121T103305240926.json` |

## 五、未验证 / 开放项

1. **state.json 未改动**：本窗口不写 `ops/bus/state.json`（那是 W0 的账）。T3 仍为 `todo`，推进提案已落 `ops/buffer/proposals/`，需 W0 或人写入。
2. **T3 任务卡 21 行 > 20 行**：输入缓冲按卡会拒收（本卡自身超限）。已作为输入侧缺陷记录，未改卡；请 W0 修剪到 ≤20 行。
3. **未接真实 DSH 会话**：本层是库+CLI，DSH 侧尚未强制走 `handoff_to_dsh()`。接入点与拒绝码已固定，联调属 UNVERIFIED。
4. **未改 DSH 配置**：按卡禁止，只提供调用入口。

## 六、可推翻条件

- `python ops\bus\check_handoff.py` 非 0；
- `python ops\buffer\dsh_buffer.py --self-test` 非 21/21；
- 任一验收用例被放行（伪造完成 / sha 不符 / 双 owner / 直写受保护对象）；
- 产物 sha256 与回执不一致。

## 七、复现

```bat
python ops\buffer\dsh_buffer.py --self-test
python ops\buffer\dsh_buffer.py --report
python ops\buffer\dsh_buffer.py --verify T3 --out ops\buffer\verify_T3.json
python ops\bus\check_handoff.py
```
