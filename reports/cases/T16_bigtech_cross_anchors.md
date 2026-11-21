# T16 · 大厂交叉锚点库 + 失败案例（倒推补缺）

- task_id: T16
- owner: W16
- 完成日期: 2026-11-21
- 范围: 只使用公开信息；不接触内部系统、不引用内幕
- 交付: 20 个锚点 + 5 个失败案例 + 3 条反事实
- 用途: 用“大厂当时的选择”校准我方决策，不是成功学清单

## 0. 先说结论

1. 大厂的选择很少是“看到了未来”，更多是“在约束下选了一个能交付的版本”。锚点要对照的是约束，不是结果。
2. 最常见的分水岭不是技术，而是生态位：开放还是封闭、买还是建、垂直还是水平、先高价还是先规模。
3. 失败案例的共同点不是“笨”，而是用资产负债表、品牌或渠道去替代产品-市场匹配；钱能买时间，买不到生态。
4. “没做什么”比“做了什么”更能暴露约束。苹果不做 Flash、IBM 不控 CPU/OS、Tesla 不从低价车起步，都是主动放弃。
5. 反事实只能校验“哪个变量是承重墙”，不能当预测；本报告的反事实均标了置信度与可推翻条件。

## 1. 证据口径与级别

| 级别 | 定义 | 本报告用法 |
|---|---|---|
| A | 公司官方新闻稿、SEC/监管文件、政府/NASA/GAO 原始文件、官方博客/公开信 | 作为事实锚点；仍只证明“它公开说了/申报了什么” |
| B | 独立主流媒体、学术机构、行业研究、严肃传记/回顾 | 用于交叉、补足背景；不单独证明因果 |
| C | 百科、社区、二手回顾 | 只用于定位线索；本报告未把 C 作为任何一行的唯一依据 |

约束列的标签：

- `[公开]`：公司/监管文件或公开信明确写出，或属于可核对的结构事实。
- `[推断]`：基于公开事实的分析，不是内部消息，也不是“大厂当时一定这么想”。
- 失败原因同样区分“公开事实”与“推断”，不把公开叙事当内幕。

> 说明：本报告核对日期为 2026-11-21。部分媒体页有付费墙，Tesla 官网对自动抓取返回 403；A 级优先用官方原文 URL，B 级用检索摘要与独立报道交叉。未逐页存档全文，故不声称“已复现每一页”。

## 2. 锚点表（20 个）

| ID | 公司 | 类型 | 决策（公开） | 时间 | 约束（标签） | 没做什么 | 结果/代价 | 来源（级别） |
|---|---|---|---|---|---|---|---|---|
| A1 | IBM | 开放架构 | 推出 IBM PC：开放架构，采用 Intel 8088 + Microsoft MS-DOS，走零售渠道 | 1981-08-12 | [公开] PC 常规开发 4–5 年，Project Chess 被要求约 1 年出货；[推断] 赶窗口必须用现成 CPU/OS | 没把 CPU/OS 做成 IBM 专有；没走封闭架构 | PC 成为行业标准，但利润流向 Intel/Microsoft；IBM 2005 年把 PC 业务卖给 Lenovo | S01 A; S02 B; S49 A |
| A2 | TSMC | 生态位/中立 | 只做晶圆代工，不做自有品牌芯片，承诺不与客户竞争 | 1987-02-21 | [公开] 建厂资本密集、良率爬坡；[推断] 客户下单前提是代工厂中立 | 没做自有芯片/品牌；没和客户抢终端市场 | 开创 pure-play foundry，成为 fabless 产业的底座 | S03 A |
| A3 | Apple | 垂直整合 | iPhone：软硬件一体、Multi-Touch、无物理键盘、不支持 Flash | 2007-01-09 | [公开] Jobs 列电池、安全、触控、第三方中间层；AT&T 独家；[推断] 无键盘是取舍 | 没做物理键盘；没支持 Flash；没授权 iOS 给其他厂商 | 重新定义智能手机；App Store 后续成为平台 | S04 A; S05 A |
| A4 | Apple | 封闭平台 | App Store：Apple 审核、封闭分发、标准 30% 抽成 | 2008-07-10 | [公开] 审核指南/开发者协议；[推断] 以封闭换安全与体验 | 没开放侧载/第三方商店（直到监管强制变化）；没放弃审核权 | 应用经济爆发；30% 抽成成为全球反垄断焦点 | S06 A; S07 A |
| A5 | Google | 开放生态 | 发布 Android + 开放手机联盟：开源、免费授权给 OEM，靠服务变现 | 2007-11-05 | [公开] OHA 30+ 厂商；Google 当时没有手机硬件规模；[推断] 开放换采用速度 | 没把 Android 做成闭源收费 OS；当时没自己做手机 | 成为最大移动 OS；碎片化/反垄断长期伴随 | S08 A; S09 A |
| A6 | Amazon | 基础设施产品化 | 把内部基础设施做成 AWS：按量付费、无最低消费、商品化硬件 | 2006-03-14 | [公开] Amazon S3 发布写明 no minimum fee/commodity hardware；[推断] 零售低毛利促使找第二曲线 | 没卖 on-prem 许可证；没要求长期合同/最低消费 | AWS 成为利润引擎，定义公有云 | S10 A |
| A7 | NVIDIA | 软件护城河 | 2006 年推 CUDA：把 GPU 从图形专用扩展到通用计算 | 2006（1.0 于 2007） | [公开] GPU 当时只服务图形管线；[推断] 软件生态先于 AI 需求 | 没停在图形卡；CUDA 没开源 | CUDA 成为 AI 算力护城河；锁定开发者 | S11 A |
| A8 | Tesla | 时机/排序 | Master Plan：先做高价 Roadster，再做 Model S，最后做大众车 | 2006-08-02 | [公开] 计划明写高端→大众；[推断] 电池成本/资本限制迫使先卖高价 | 没从低价大众车起步；没先做全产品线 | 建立品牌与三电能力；中间多次接近资金断裂 | S12 A |
| A9 | Tesla | IP 开放 | 开放全部专利，允许善意使用 | 2014-06-12 | [公开] Tesla 声明 open patents；[推断] 市场太小，扩大品类优先于守专利 | 没把专利作为排他壁垒 | 推动电动车产业投资；因果归因难，不能全算专利开放 | S13 A; S14 B |
| A10 | Netflix | 内容/分发 | 从 licensing 转向原创：2011 签 House of Cards，2013 全季一次上线 | 2011-03 / 2013-02-01 | [公开] 两季 26 集承诺、13 集一次放出；[推断] 版权成本/差异化压力 | 没做周更；没停留在只买版权 | 原创+ binge 成为流媒体标准；内容支出大幅上升 | S15 B; S16 B |
| A11 | Microsoft | 买网络 | 75 亿美元收购 GitHub，承诺独立运营、开放平台 | 2018-06-04 | [公开] 官方承诺独立/open；[推断] 开发者信任是交易前提 | 没把 GitHub 并入 Azure-only；没关闭开放平台 | 拿到开发者网络；GitHub 保持中立，Azure 协同 | S17 A; S18 A |
| A12 | Microsoft | 买模型 | 与 OpenAI 深度绑定：多轮投资，Azure 独家云，模型嵌入产品 | 2019 / 2023-01-23 | [公开] 2023 宣布 multiyear multibillion、Azure exclusive；[推断] 自建 frontier 模型太慢/太贵 | 没整体收购 OpenAI；没独自造出 GPT-4（推断） | Copilot 先发；形成对 OpenAI/算力的依赖与治理风险 | S19 A; S20 B |
| A13 | Meta | 买产品 | 10 亿美元收购 Instagram，保持独立 | 2012-04-09 | [公开] 约 10 亿美元现金+股票、独立运营；[推断] Facebook 移动端短板 | 没自建照片 app；没立即合并进 Facebook | Instagram 成为移动广告引擎 | S21 A |
| A14 | Meta | 买网络 | 约 190 亿美元收购 WhatsApp，保持独立、暂不上广告 | 2014-02-19 | [公开] 官方/SEC 文件；公开承诺 no ads（B）；[推断] 隐私是增长条件 | 没立即上广告；没立刻合并 Messenger | 20 亿+用户；变现慢、监管/隐私争议 | S22 A; S23 B |
| A15 | Meta | 大赌注 | 改名 Meta，重注 metaverse/Reality Labs | 2021-10-28 | [公开] 官方改名/Reality Labs；[推断] ATT 后寻找下一平台 | 没等 AR 硬件成熟；没保留 Facebook 母品牌 | Reality Labs 多年巨亏；2023 转向 AI/效率 | S24 A; S25 B |
| A16 | Tencent | 自我蚕食 | 广州团队做微信，允许与 QQ 内部竞争/自我蚕食 | 2011-01-21 | [公开] 2011 上线；[公开-B] 广州团队/内部竞争；[推断] 允许 cannibalization | 没保护 QQ 的既有位置；没等 QQ 移动化 | 微信成为国民级 super app；QQ 角色被重定义 | S26 A; S27 B |
| A17 | Alibaba | 免费策略 | 2003 年做淘宝：对卖家免费，独立团队对抗 eBay EachNet | 2003-05 | [公开] 招股书写明 free platform；[推断] 免费换交易流动性 | 没早期收 listing fee；没照搬 eBay 收费模式 | 击败 eBay 中国；后转向广告/服务变现 | S28 A; S29 B |
| A18 | ByteDance | 全球并购 | 收购 Musical.ly 并并入 TikTok，做全球短影音 | 2017-11 / 2018-08-02 | [公开-B] 收购/合并报道；[推断] 买海外用户+品牌，抢时间窗 | 没保留 Musical.ly 独立；没只做中国市场 | TikTok 全球规模化；伴随多国监管/禁令 | S30 B |
| A19 | Disney | 渠道自营 | 推 Disney+：DTC 优先，把内容从 Netflix 收回，低价获客 | 2019-11-12 | [公开] 投资者日/上线稿 6.99 美元/月；[推断] 有线电视 bundle 被自我蚕食 | 没继续把核心内容授权给 Netflix；没保 cable bundle 不变 | 快速破 1 亿订阅；流媒体前期巨亏、有线电视下滑 | S31 A; S32 A; S33 B |
| A20 | SpaceX / NASA | 成本结构 | COTS/CRS：固定价格、里程碑付款，垂直整合核心部件 | 2006-08 / 2008-12-23 | [公开] NASA 固定价格里程碑；[推断] cost-plus 无法约束成本 | 没用 cost-plus；没外包核心火箭/飞船 | Falcon 9/Dragon 成为低价货运主力 | S34 A; S35 A; S36 A; S37 A |

### 锚点分组速览

- 开放/封闭：A1 IBM PC、A4 Apple App Store、A5 Android、A2 TSMC 中立、A9 Tesla 专利。
- 买/建：A11 GitHub、A12 OpenAI、A13 Instagram、A14 WhatsApp、A18 Musical.ly。
- 垂直/水平：A3 iPhone、A6 AWS、A7 CUDA、A19 Disney+、A20 SpaceX。
- 时机/排序：A8 Tesla Master Plan、A10 Netflix 原创、A15 Meta metaverse、A16 微信、A17 淘宝。

## 3. 失败案例（5 个）

### F1 · Amazon Fire Phone（2014）

- 事实：2014-06-18 发布，7 月上市；Fire OS + Dynamic Perspective/Firefly；AT&T 独家；合约价 199 美元。2014 年 Q3 计提约 1.70 亿美元，季末 Fire Phone 库存/供应商承诺约 8,300 万美元。
- 决策逻辑：用手机抢购物入口，硬件补贴、服务变现。
- 约束/误判：没有 Google Play，应用生态缺口；价格对标 iPhone/Samsung；运营商独家缩小用户；[推断] 把“入口”当成“购买理由”。
- 代价：1.70 亿美元减值；产品退出主力；品牌与组织成本。
- 教训：硬件入口不能替代生态、价格、渠道任一基本盘；大公司资产负债表不能买来 PMF。
- 来源/级别：S38 A（SEC 10-Q）；S39 B（Guardian）。
- 可推翻：若 Fire Phone 首月销量超过 100 万或长期维持 199 美元价位，则“定价/生态失败”结论需改。

### F2 · Microsoft-Nokia（2013–2015）

- 事实：2013-09-03 宣布 72 亿美元收购 Nokia 设备与服务；2014-04 完成；2015-07-08 宣布约 76 亿美元减值、裁员 7,800 人。
- 决策逻辑：买下 Windows Phone 的硬件能力，做“第三生态”。
- 约束/误判：Windows Phone 份额约 3%；Android/iOS 双寡头；Nokia 2011 已押注 Windows；[推断] 买硬件买不到开发者。
- 代价：减值超过收购价；裁员；手机业务退出。
- 教训：平台份额低于 10% 时，垂直整合可能加速沉没；先有生态再买硬件。
- 来源/级别：S40 A；S41 B。
- 可推翻：若收购后 Windows Phone 份额升至 10% 以上且持续 2 年，则结论需改。

### F3 · Yahoo 拒绝 Microsoft（2008）

- 事实：2008-02-01 Microsoft 报价 446 亿美元（31 美元/股，62% 溢价）；2008-02-11 Yahoo 董事会拒绝，称低估；2016-07 Verizon 同意 48.3 亿美元收购核心，2017 年降至 44.8 亿美元并完成。
- 决策逻辑：董事会认为独立价值更高，想争取更高价或替代方案。
- 约束/误判：搜索广告竞争、组织动荡；[推断] 没有可信的 standalone 翻盘计划，却用“低估”当拒绝理由。
- 代价：核心业务最终售价约为 2008 报价的 10%。
- 教训：拒绝溢价不是错，错在拿不出可执行的替代路径；董事会信心不是证据。
- 来源/级别：S42 A；S43 B；S44 A。
- 可推翻：若 Yahoo 独立市值在 2010 年前超过 446 亿美元，则“拒绝是价值毁灭”需改。

### F4 · Google Glass（2013–2015）

- 事实：2013 年 Explorer 版 1,500 美元；2015-01-15 宣布结束 Explorer，1 月 19 日最后一天向个人销售；团队移出 Google X，转企业方向。
- 决策逻辑：用 Explorer 公开 beta，抢占消费级 AR。
- 约束/误判：社会接受度/隐私反弹；电池/发热；使用场景弱；价格高；[推断] 把开发者 beta 当成消费者产品。
- 代价：消费版搁置；品牌争议；企业版另起。
- 教训：硬件+社会规范；beta 不能替代 use case 和社会许可。
- 来源/级别：S45 B；S46 B。
- 可推翻：若 Explorer 有 10 万以上日活且企业版非必需，则“时机过早”需改。

### F5 · Kodak 数字相机（1975–2012）

- 事实：1975 年 Steven Sasson 在 Kodak 做出首台自包含数字相机原型；1977 年申请专利；Kodak 未率先把消费级数字相机做成主业务；2012-01-19 申请 Chapter 11。Kodak 后来也做数字相机，失败不是“没技术”，是“没把技术变成主业务”。
- 决策逻辑：保护胶片高毛利与冲印生态。
- 约束/误判：胶片利润结构、组织惯性、渠道/化学能力；[B] 前员工/报道称原型被搁置；[推断] 不是不知道技术，而是不愿自我蚕食。
- 代价：破产重组；胶片市场崩塌。
- 教训：incumbent 的约束是利润结构；要 cannibalize，需独立单元、独立成本模型和独立 KPI。
- 来源/级别：S47 A；S48 B。
- 可推翻：若 Kodak 在 1985 年前推出消费级数字相机并保住份额，则“未商业化”结论需改。

## 4. 三条反事实

> 反事实不是事实；只用于识别“哪个变量是承重墙”。每条给：前提、证据、必须成立的条件、结论、置信度、可推翻条件。

### C1 · 如果 IBM 把 PC 做成封闭架构

- 前提：IBM 像 Apple 一样保留架构、CPU、OS 的控制权，不分给 Intel/Microsoft/克隆厂商。
- 证据：IBM 实际选择开放架构与现成 CPU/OS（S01 A）；PC 克隆市场迅速形成（S02 B）；IBM 2005 年把 PC 业务卖给 Lenovo（S49 A）。
- 必须成立的条件：IBM 能在控制架构的同时，把成本压到克隆厂商水平，并让开发者愿意只为一个封闭平台开发；IBM 的内部流程/成本结构能支持消费级迭代。
- 结论：单靠“封闭”救不了 IBM PC 利润。更可能的结局是份额更早流失；真正的承重墙是组织与成本结构，不是开放/封闭本身。
- 置信度：中低。
- 来源/级别：S01 A；S02 B；S49 A。
- 可推翻：若封闭版 IBM PC 在 1990 年前保持 30% 以上份额且持续正毛利，则本反事实需改。

### C2 · 如果 Google 留下 Motorola 并垂直整合

- 前提：Google 不把 Motorola 卖给 Lenovo，而是把手机硬件做成核心业务，与 Samsung/Huawei 正面竞争。
- 证据：Google 收购 Motorola 时明确承诺 Android 保持开放、Motorola 独立运营（S50 A）；2014 年把 Motorola 卖给 Lenovo（S51 A）；Android 的规模来自多家 OEM（S08 A、S09 A）。
- 必须成立的条件：Google 能在硬件上超过 Samsung/Huawei，同时让这些 OEM 相信“Google 不会用平台优势偏袒自己”；还要解决运营商/渠道能力。
- 结论：中立是 Android 规模的承重墙；当年若留下 Motorola，硬件收益大概率抵不过 OEM 信任流失。Pixel 后来证明 Google 能做硬件，但那是小规模、不同时间窗。
- 置信度：中。
- 来源/级别：S08 A；S09 A；S50 A；S51 A。
- 可推翻：若 Google 整合 Motorola 后 Android OEM 份额没有下降，且硬件业务持续正毛利，则本反事实需改。

### C3 · 如果 Yahoo 接受 Microsoft 的 446 亿美元

- 前提：2008 年 Yahoo 董事会接受 31 美元/股、总价 446 亿美元的报价，交易按原价完成。
- 证据：Microsoft 报价含 62% 溢价（S42 A）；Yahoo 董事会拒绝（S43 B）；2017 年 Verizon 以 44.8 亿美元收购 Yahoo 核心（S44 A）。
- 必须成立的条件：交易不被反垄断/股东诉讼拖垮，价格不被大幅重谈；Yahoo 独立经营不会在 2008 金融危机后反弹到更高估值。
- 结论：从事后价格看，拒绝摧毁了约 90% 的核心价值；从当时看，董事会若拿不出可信的独立计划，“低估”就不是充分理由。股东大概率在接报价时更好，但交易能否完成仍有不确定性。
- 置信度：价值比较中高；交易完成/执行不确定性高。
- 来源/级别：S42 A；S43 B；S44 A。
- 可推翻：若 Yahoo 独立市值在 2011 年前超过 446 亿美元，或 Microsoft 当时无论如何都会撤回报价，则本反事实需改。

## 5. 用锚点校验我方决策（下一步模板）

选 1 个我方真实决策，按下面 5 步写一页校验报告：

1. **定类型**：它是开放/封闭、买/建、垂直/水平、定价/免费、时机/排序中的哪一类？每类选 3 个同类型锚点。
2. **对约束**：把锚点的 `[公开]` 约束逐条对照我方；不同就降权，不要把“大厂也这么做”当理由。
3. **看“没做什么”**：锚点明确放弃的东西，我方是否正在做？如果做，写清为什么我们的约束不同。
4. **算代价**：锚点的结果/代价里，最坏损失、退出成本、时间成本分别是多少？我方能否承受。
5. **写可推翻条件**：给出 6/12 个月内可观察的指标；不达标就撤回，不追加叙事。

不要做：

- 不要把大厂结果当因果；结果里混着时机、垄断、资本、运气。
- 不要用“他们也这么做”替代约束匹配。
- 不要把公开叙事当内幕；`[推断]` 只能当假设。
- 不要只挑赢家；本报告已用 5 个失败和 1 个亏损锚点（A15）做反向校验。

## 6. 来源登记表

| ID | 来源 | URL | 级别 | 备注 |
|---|---|---|---|---|
| S01 | IBM History · The IBM PC | https://www.ibm.com/history/personal-computer | A | 官方历史页；1981-08-12、开放架构 |
| S02 | Computer History Museum · August 12 | https://www.computerhistory.org/tdih/august/12/ | B | 日期与 x86/MS-DOS 交叉 |
| S03 | TSMC · About TSMC | https://www.tsmc.com/english/aboutTSMC | A | 1987 成立、pure-play foundry |
| S04 | Apple Newsroom · iPhone | https://www.apple.com/newsroom/2007/01/09Apple-Reinvents-the-Phone-with-iPhone/ | A | 2007-01-09 发布 |
| S05 | Apple · Thoughts on Flash（存档） | https://web.archive.org/web/20100502021750/www.apple.com/hotnews/thoughts-on-flash | A | 原 apple.com/hotnews/thoughts-on-flash 已 404；存档核对 |
| S06 | Apple Newsroom · iPhone 3G / App Store | https://www.apple.com/newsroom/2008/07/10iPhone-3G-on-Sale-Tomorrow/ | A | 2008-07-10 App Store 上线 |
| S07 | Apple · App Store Review Guidelines | https://developer.apple.com/app-store/review/guidelines/ | A | 现行审核/抽成政策；非 2008 原文 |
| S08 | Open Handset Alliance · 2007-11-05 | http://www.openhandsetalliance.com/press_110507.html | A | Android 开源发布 |
| S09 | Google Blog · Where's my Gphone | https://googleblog.blogspot.com/2007/11/wheres-my-gphone.html | A | Android/OHA 官方说明 |
| S10 | Amazon Press · AWS Launches S3 | https://press.aboutamazon.com/2006/3/amazon-web-services-launches | A | 2006-03-14；no minimum fee |
| S11 | NVIDIA · CUDA Programming Guide | https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/introduction.html | A | 2006 引入 CUDA |
| S12 | Tesla · Secret Master Plan | https://www.tesla.com/secret-master-plan | A | 2006-08-02；官网对自动抓取 403 |
| S13 | Tesla · All Our Patent Are Belong To You | https://www.tesla.com/blog/all-our-patent-are-belong-you | A | 2014-06-12；官网对自动抓取 403 |
| S14 | CNIPA · Tesla Opens the Patent Wall | https://english.cnipa.gov.cn/art/2014/6/30/art_2706_165201.html | B | 政府网站转述，交叉 Tesla 博文 |
| S15 | NYT · House of Cards Arrives as a Netflix Series | https://www.nytimes.com/2013/01/20/arts/television/house-of-cards-arrives-as-a-netflix-series.html | B | 2013-02-01 全季上线；可能有付费墙 |
| S16 | Deadline · Netflix Enters Original Programming | https://deadline.com/2011/03/netflix-to-enter-original-programming-with-mega-deal-for-david-fincher-kevin-spacey-drama-series-house-of-cards-114184/ | B | 2011-03；两季 26 集承诺 |
| S17 | Microsoft Blog · Microsoft + GitHub | https://blogs.microsoft.com/blog/2018/06/04/microsoft-github-empowering-developers/ | A | 2018-06-04；独立/open 承诺 |
| S18 | SEC · Microsoft GitHub Exhibit 99.1 | https://www.sec.gov/Archives/edgar/data/789019/000119312518182975/d600091dex991.htm | A | 75 亿美元、全股票 |
| S19 | OpenAI · Microsoft and OpenAI extend partnership | https://openai.com/index/openai-and-microsoft-extend-partnership/ | A | 2023-01-23；multi-year multibillion |
| S20 | Reuters · Microsoft invests more in OpenAI | https://www.reuters.com/technology/microsoft-invest-more-openai-tech-race-heats-up-2023-01-23/ | B | 金额未公开；媒体称约 100 亿美元 |
| S21 | Meta · Facebook to Acquire Instagram | https://about.fb.com/news/2012/04/facebook-to-acquire-instagram/ | A | 2012-04-09；约 10 亿美元 |
| S22 | SEC · Facebook/WhatsApp Press Release | https://www.sec.gov/Archives/edgar/data/1326801/000132680114000010/exhibit991_pressrelease219.htm | A | 2014-02-19；约 190 亿美元 |
| S23 | WSJ · Facebook to Buy WhatsApp | https://www.wsj.com/articles/SB10001424052702304914204579393452029288302 | B | 交叉价格/条款；可能有付费墙 |
| S24 | Meta · The Facebook Company Is Now Meta | https://about.fb.com/news/2021/10/facebook-company-is-now-meta/ | A | 2021-10-28 |
| S25 | Reuters · Facebook changes name to Meta | https://www.reuters.com/technology/facebooks-zuckerberg-kicks-off-its-virtual-reality-event-with-metaverse-vision-2021-10-28/ | B | 交叉 metaverse 定位 |
| S26 | Tencent · Weixin & WeChat | https://www.tencent.com/products/weixin-wechat/ | A | 2011 上线 |
| S27 | SAGE · How Tencent's culture shaped WeChat | https://journals.sagepub.com/doi/10.1177/1742766520923008 | B | 学术回顾；广州团队/内部竞争 |
| S28 | SEC · Alibaba 424B4 Prospectus | https://www.sec.gov/Archives/edgar/data/1577552/000119312514347620/d709111d424b4.htm | A | 招股书：2003 淘宝 free platform |
| S29 | HBS · Taobao Digital Winner | https://aiinstitute.hbs.edu/platform-digit/submission/digital-winner-in-chinas-online-c2c-marketplace-taobao-com/ | B | 交叉 eBay EachNet/免费策略 |
| S30 | Hollywood Reporter · ByteDance merges Musical.ly with TikTok | https://www.hollywoodreporter.com/business/digital/musically-owner-bytedance-merges-app-tiktok-1131630/ | B | 2017 收购、2018-08-02 合并 |
| S31 | Disney · 2019 Investor Day DTC Strategy | https://thewaltdisneycompany.com/news/disney-spotlights-comprehensive-direct-to-consumer-strategy-at-2019-investor-day/ | A | 2019-04-11；Disney+ 6.99 美元/月 |
| S32 | Disney · Disney+ Launches Today | https://thewaltdisneycompany.com/news/disney-launches-today-and-a-new-era-of-disney-entertainment-begins/ | A | 2019-11-12 |
| S33 | LA Times · Disney's streaming gamble | https://www.latimes.com/entertainment-arts/business/story/2019-11-12/disney-plus-streaming | B | 交叉前期亏损/有线电视压力 |
| S34 | NASA · COTS Space Act Agreement | https://www.nasa.gov/wp-content/uploads/2015/04/189228main_setc_nnj06ta26a.pdf | A | 2006；里程碑付款 |
| S35 | NASA OIG · COTS/ISS | https://oig.nasa.gov/docs/IG-13-016.pdf | A | 2006 年 2.78 亿美元 SAA；固定价格 |
| S36 | NASA · 2008 Archives（CRS） | https://www3.nasa.gov/audience/formedia/archives/2008-all-archives.html | A | 2008-12-23 CRS 合同 |
| S37 | GAO · NASA Commercial Partners | https://www.gao.gov/assets/a291016.html | A | 固定价格、绩效里程碑 |
| S38 | SEC · Amazon 2014 Q3 10-Q | https://www.sec.gov/Archives/edgar/data/1018724/000101872414000055/amzn-20140930x10q.htm | A | Fire Phone 库存/供应商承诺 8,300 万美元 |
| S39 | Guardian · Amazon writes off 1.70 亿美元 | https://www.theguardian.com/technology/2014/oct/24/amazon-unsold-fire-phones | B | 交叉 1.70 亿美元减值、发布/定价 |
| S40 | Microsoft · Restructuring phone hardware business | https://news.microsoft.com/source/2015/07/08/microsoft-announces-restructuring-of-phone-hardware-business/ | A | 2015-07-08；76 亿美元减值、7,800 裁员 |
| S41 | Reuters · Microsoft hangs up on Nokia | https://www.reuters.com/article/business/microsoft-hangs-up-on-nokia-business-to-cut-7800-jobs-idUSKCN0PI0GI/ | B | 交叉 72 亿美元收购价、3% 份额 |
| S42 | Microsoft · Responds to Yahoo announcement | https://news.microsoft.com/source/2008/02/11/microsoft-responds-to-yahoo-announcement/ | A | 2008-02-01 报价 446 亿美元、62% 溢价 |
| S43 | NYT · Yahoo rejects Microsoft offer | https://www.nytimes.com/2008/02/11/technology/11iht-11cndyahoo.9937476.html | B | 2008-02-11 拒绝；可能有付费墙 |
| S44 | SEC · Verizon/Yahoo Press Release | https://www.sec.gov/Archives/edgar/data/1011006/000119312517049548/d353690dex991.htm | A | 2017 年完成；约 44.8 亿美元 |
| S45 | Time · Google Glass Ends Explorer Beta | https://time.com/3669927/google-glass-explorer-program-ends/ | B | 2015-01-15；1,500 美元、1 月 19 日停售 |
| S46 | BBC · Google Glass sales halted | https://www.bbc.com/news/technology-30831128 | B | 交叉 Explorer 结束 |
| S47 | SEC · Kodak Chapter 11 Press Release | https://www.sec.gov/Archives/edgar/data/31235/000119312512016443/d285282dex991.htm | A | 2012-01-19 |
| S48 | NYT Lens · Kodak's First Digital Moment | https://archive.nytimes.com/lens.blogs.nytimes.com/2015/08/12/kodaks-first-digital-moment/ | B | 1975 原型、前员工回顾 |
| S49 | Lenovo · Completes IBM PC Division Acquisition | https://news.lenovo.com/pressroom/press-releases/lenovo-completes-acquisition-ibms-personal-computing-division/ | A | 2005 年完成；IBM 退出 PC |
| S50 | SEC · Google/Motorola Joint Press Release | https://www.sec.gov/Archives/edgar/data/1288776/000119312511222169/dex991.htm | A | 2011-08-15；125 亿美元；Android 保持开放 |
| S51 | Lenovo · Completes Motorola Mobility Acquisition | https://news.lenovo.com/pressroom/press-releases/lenovo-completes-full-acquisition-motorola-mobility-from-google/ | A | 2014-10-30；29.1 亿美元 |

## 7. 边界与未验证项

- 未逐页抓取所有来源全文；部分媒体有付费墙，Tesla 官网对自动抓取返回 403。A 级以官方原文/监管文件为准，B 级用于交叉。
- “结果/代价”是公开结果记录，不声称单一决策导致该结果；大厂结果混有时机、垄断、资本与运气。
- 约束列的 `[推断]` 是分析假设，不是内幕；不得当作“大厂当时真实想法”。
- 失败原因中，Kodak 的“搁置”来自公开报道/前员工回顾，属于 B 级叙事，不是董事会文件。
- 本报告没有用锚点校验我方具体决策；那是任务卡的下一步（W16，¥3）。
- 未发生付费数据/数据库采购；预算花费为公开网页检索与整理时间，金额不估价。
