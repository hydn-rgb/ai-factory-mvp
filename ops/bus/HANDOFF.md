# HANDOFF · AI 工厂调度台接管说明

- 更新: 2026-11-21 14:05（T0–T2 已收束）
- 适用: 任何新窗口/新人/新 agent 接手 `<AI_FACTORY_ROOT>`
- 原则: **先保命，再推进；状态只认 `ops/bus/state.json`；没有回执的“完成”一律不算。**

## 一、30 秒判断系统是否活着

```powershell
cd <AI_FACTORY_ROOT>
& 'C:\Program Files\python\python.exe' -X utf8 ops\bus\status.py
```

看三行：

1. `open=N/12` —— 开放卡不能超过 12；超过就先关/撤，不新建。
2. `heartbeat=...` —— 超过 24 小时没更新，说明调度台没在跑；跑一次 `audit.py --apply` 会重写。
3. `latest_receipt=...` —— 比 `state=` 旧很多，说明有回执没验收。

当前快照（2026-11-21 14:05）：

- `open=2/12 done=18 cancelled=1`
- 开放卡：仅 T14、T15（T0/T1/T2 已 done）
- `heartbeat=2026-11-21T13:59:26`
- T14/T15 回执有效但 `status=UNVERIFIED`，**不进 done**，卡仍是 `todo`

## 二、恢复顺序（按顺序跑，别跳）

| # | 命令 | 通过标准 |
|---|---|---|
| 1 | `python ops\bus\status.py` | 打印 20 行任务表，不报错 |
| 2 | `python ops\bus\check_handoff.py` | 无 FAIL；回执字段/sha/owner 一致 |
| 3 | `python ops\bus\check_card.py` | 21/21 PASS |
| 4 | `python ops\bus\audit.py --apply` | 打印 ACCEPT/STATE，不崩 |
| 5 | `python ops\bus\next_round.py --self-test` | 12/12 PASS |
| 6 | `python ops\probes\source_ledger.py --self-test` | 5/5 PASS |
| 7 | `node plugins\model_router\test_router.mjs` | ALL PASS |
| 8 | `python ops\context\watch.py --check --dry-run` | 出巡检 JSON，不写文件 |

> 第 4 步会改 `state.json`；跑之前先复制一份 `state.json.bak-manual-<时间>`。

## 三、系统地图（先看这 6 个）

| 模块 | 入口 | 作用 | 坏了会怎样 |
|---|---|---|---|
| 调度台 | `ops/bus/state.json` | 唯一事实源：谁在做、预算、回执 | 全部状态失真 |
| 回执验收 | `ops/bus/audit.py` | 6 字段校验 + heartbeat + 状态推进 | 假完成混进 done |
| 发卡 | `ops/bus/next_round.py` | 裂变、限深 3、开放 12、预算继承 | 卡爆炸/预算透支 |
| 卡片校验 | `ops/bus/check_card.py` | 必填字段 + 下一步四段 | 占位卡混入 |
| 信源探针 | `ops/probes/source_ledger.py` | 可达性 + Admiralty 评分 | 把 D 级线索当证据 |
| 资产清单 | `reports/inventory/ACTIVE_INVENTORY.md` | 在用系统/路径/sha | 接手找不到东西 |

## 四、当前在做的事（按优先级）

1. **T0（done）**：MVP 范围/签收/边界/发布；同行定位 = 交叉验证 + 补充论据，非独立 alpha；Go 决策 = 暂不订阅。
2. **T1/T2（done）**：某量化机构A、某量化机构B V1–V4 四版并联，产物 `reports/cases/highflyer_v4.md` / `lingjun_v4.md`；旧版只读、只增不删。
3. **T14（todo，UNVERIFIED）**：非标需求探针。只推进真人访谈：0/10 访谈、0/3 付费试点；**不把“感兴趣”写成“愿付费”**。
4. **T15（todo，UNVERIFIED）**：律师获客/实习生 SOP。只推进 1 家律所 + 1 名实习生访谈；0/1、0/1。
5. **发行包**：`dist/ai-factory-mvp/` 已 git commit（`本地 commit`），`selftest.ps1` PASS；GitHub 未认证，未 push，详见包内 `push.ps1`。

## 五、硬约束（违反即回滚）

- 单笔 ≤5%、单赛道 ≤20%、无退出不投、五维任一 ≤2 不投；AI 不替老板下注。
- 不碰密钥/凭证；不改 DSH/WorkBuddy 配置；不做多账号、绕限流、试用滥用、先做后付。
- 信源：D/E 级、可信度 4–6、未授权 → 只能当线索，不作证据；抓取限速 ≤1 req/3s。
- 案例 V1–V4 并联，只增不删，旧版只读。
- 一窗口一任务；跨窗口只传指针（路径 + sha + 行数），不转述、不传摘要。

## 六、常见故障与处理

| 现象 | 处理 |
|---|---|
| `state.json` 解析失败 | 复制最新 `state.json.bak-*` 覆盖，再跑 `audit.py --apply` |
| 回执 sha 与产物不符 | 以产物为准，重算 sha 写回回执；不要改产物去迁就回执 |
| T12 sha 漂移 | T12 产物锚定 `ops/bus/out/T12-evidence.json`，不要指向 `install.log`（会被追加） |
| `open > 12` | 先 `cancelled` 或拆小；禁止新建卡 |
| heartbeat 停更 | 跑 `audit.py --apply`；仍不写就查 `ops/bus` 写权限 |
| 探针大批 521/412 | 源站/风控，不是脚本 bug；记录不可达，降 `UNVERIFIED`，不绕 |
| 模型路由失效 | 查 `<USER_HOME>\.config\opencode\opencode.json` 的 `plugins`；用 `rollback.ps1` 回滚 |

## 七、当前产物指针（sha16 见资产清单）

- 破产 10 案：`reports/cases/T17_bankruptcy_10cases.md`（16 行）
- 开发者墓志铭：`reports/cases/T18_developer_epitaphs.md`（20 行）
- 信源合规地图：`reports/compliance/T19_source_compliance_map.md`（18 行）
- 财税/律师观察表：`reports/cases/T20_advisor_observation_forms.md`（24 行）
- 信源探针报告：`reports/sources/probe_20261121_125528.md`
- 资产清单：`reports/inventory/ACTIVE_INVENTORY.md`
- 大厂锚点：`reports/cases/T16_bigtech_cross_anchors.md`（28 行）
- 机构A/机构B：`reports/cases/highflyer_v4.md`（21 行证据）、`reports/cases/lingjun_v4.md`（22 行证据）
- MVP 范围/Go 决策：`reports/mvp/T0_MVP_SCOPE.md`、`reports/mvp/T0_opencode_go_decision.md`
- 插件真实调用：`reports/mvp/plugin_calls/calls.jsonl` + `README.md`
- 发行包：`dist/ai-factory-mvp/`（commit `本地 commit`，未 push）

## 八、接手第一小时

1. 读本文件 + `reports/inventory/ACTIVE_INVENTORY.md` + `reports/mvp/T0_MVP_SCOPE.md`。
2. 跑第一节的 `status.py`，确认 `open/heartbeat/latest_receipt`。
3. 跑第二节 1–4 步，确认没有 FAIL；发行包可跑 `dist\ai-factory-mvp\selftest.ps1`。
4. 从 T14、T15 里选 1 张，**只做 1 张**；没有真人访谈/付费试点证据就保持 `UNVERIFIED`。
5. 不新建卡，除非当前 open < 10 且新卡有明确“下一步四段”。
