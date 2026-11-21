# 已立项且在用 · 资产清单

- 生成: 2026-11-21
- 口径: 只列“现在还能跑/还能读”的资产；sha16 为文件内容哈希，目录/外部系统写 `-`
- 状态以 `ops/bus/state.json` 为准；本表不替代回执

| # | 资产 | 路径 | 状态 | 入口 | sha16 | owner | 备注 |
|---|---|---|---|---|---|---|---|
| 1 | 调度台状态源 | `ops/bus/state.json` | 在用（唯一事实源） | `python ops/bus/status.py` | `2c1b2751f3950702` | W0 | open/done/cancelled + 预算 + 回执指针 |
| 2 | 回执验收 | `ops/bus/audit.py` | 在用 | `python ops/bus/audit.py --apply` | `91bf595706143930` | W0 | 必填 6 字段；UNVERIFIED 不进 done |
| 3 | 裂变/发卡 | `ops/bus/next_round.py` | 在用（限深3/开放12） | `python ops/bus/next_round.py --self-test` | `361f3fb91267ce66` | W0 | 删 fallback；预算继承父卡剩余 |
| 4 | 任务卡校验 | `ops/bus/check_card.py` | 在用 | `python ops/bus/check_card.py` | `88230c83ec6dcb77` | W0 | 必填字段 + 下一步四段 + ≤32 行 |
| 5 | 交接校验 | `ops/bus/check_handoff.py` | 在用 | `python ops/bus/check_handoff.py` | `8c7d13a762ca0da6` | W0 | 回执缺字段/sha 不符/一 owner 多任务 |
| 6 | 信源探针 | `ops/probes/source_ledger.py` | 在用 | `python ops/probes/source_ledger.py --self-test` / `--probe` | `877bcc409946255e` | W0 | Admiralty A-F×1-6 + 5 维；硬门槛 |
| 7 | 信源登记 | `ops/probes/sources.json` | 在用（18 源） | 由探针读取 | `6570071cf5738b60` | W0 | legal 字段分三层 |
| 8 | 模型路由 | `plugins/model_router/index.js` | 已安装并强制启用 | `node plugins/model_router/test_router.mjs` | `e922ea94123a99fe` | W0 | doc/code/audit 三路由；手动优先 |
| 9 | 上下文巡检 | `ops/context/watch.py` | 在用 | `python ops/context/watch.py --check --dry-run` | `5357328bffe1d215` | W0 | 超阈值出 handoff，不自动删 |
| 10 | 认知训练站 | `projects/cognitive_gym/BUILD.json` | 48/48 PASS | `cd projects/cognitive_gym; python tests/verify.py` | `3bcdef1a2d8fc128` | W0 | 本地 8787，纯静态 |
| 11 | 破产 10 案 | `reports/cases/T17_bankruptcy_10cases.md` | 已验收（16 行） | 直接读 | `5ece4faac1631286` | W17 | 10 案 + 3 失败 + 3 信号 |
| 12 | 开发者墓志铭 | `reports/cases/T18_developer_epitaphs.md` | 已验收（20 行） | 直接读 | `b13468393f8622bc` | W18 | 20 例 + 10 条不做 |
| 13 | 信源合规地图 | `reports/compliance/T19_source_compliance_map.md` | 已验收（18 行） | 直接读 | `dc34dab1d5d01eca` | W19 | G/Y/R 三层 + robots 实测 |
| 14 | 财税/律师观察表 | `reports/cases/T20_advisor_observation_forms.md` | 已验收（24 行） | 直接读 | `ba76d71d2f31c9d1` | W20 | 只观察，不切入 |
| 15 | 大厂锚点 | `reports/cases/T16_bigtech_cross_anchors.md` | 已验收（28 行） | 直接读 | `bf698110461100eb` | W16 | 锚点/失败/反事实 |
| 16 | 非标需求探针 | `ops/probe/T14_nonstandard_demand_probe.md` | UNVERIFIED（0 访谈） | 直接读 | `027fc7b5f9207888` | W14 | 5 workaround，0/10 访谈，0/3 试点 |
| 17 | 律师获客探针 | `ops/probe/T15_lawyer_process_probe.md` | UNVERIFIED（0 访谈） | 直接读 | `51e16adc40271186` | W15 | 5 渠道，0/1 律所，0/1 实习生 |
| 18 | 宪法 | `constitution.json` | v3.45.0（只读） | 直接读 | `05adf7602a07d02d` | 老板 | 98 条硬约束；改前先备份 |

## 外部系统（只存指针，不存凭证）

| 系统 | 指针 | 状态 | 备注 |
|---|---|---|---|
| 飞书多维表 | app `TI5Lbesh1afNDHsSW0oclcsrn8f`；看板 `tblPxaHvDmfBMD1e`；工具观察 `tblMcv5Be0sSrz4S`；预测 `tbl48OkD4dvw73c5`；下注 `tblp29KGfi5v49Ah` | 在用 | 只读/人工写入；不在本仓库存 token |
| AgentHUD | `D:\Apps\AgentHUD`（0.6.7） | 在用 | 备份 `AgentHUD.bak-0.6.4`；升级后是否重索引 `UNVERIFIED` |
| OpenCode 配置 | `C:\Users\doudo\.config\opencode\opencode.json` | 在用 | plugins=[model_router]；改前自动备份 |

## 不在清单里的东西

- 任何密钥/凭证/token；任何客户个人信息；任何未验收的草稿。
- 已 cancelled 的 T10（fallback 占位卡）不再列为资产。
