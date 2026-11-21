# Factory Edge Commander · 通用悬浮命令窗

在**任意 Edge 页面**按 `Ctrl+Shift+Y` 或点左下角 `⌘ Factory 命令窗`，输入 `/命令` 回车即执行。动作分两类：页面内动作（跳转/点击/填写/捕获）和本机动作（状态/审计/探针/交接/记录），全部走本机 `127.0.0.1:8791`。

## 命令（白名单，不执行任意 JS）

| 命令 | 作用 |
|---|---|
| `/status` | 读工厂 `state.json`，输出 open/done/todo/cancelled |
| `/audit` | 只读跑 `audit.py --json`，输出 T0/T1/T2 结论 |
| `/handoff` | 返回最新交接文件路径与 sha |
| `/ds` | 返回 DS 悬浮窗最近一次捕获 |
| `/probe <url>` | HTTP 探针：状态码/字节/sha/耗时；内网被拒 |
| `/note <文本>` | 追加到 `reports/inbox/edge_notes.md`（自动脱敏手机号/邮箱/证件号） |
| `/capture` | 把当前页纯文本写到 `reports/browser_capture/`（带 url/title/sha） |
| `/goto <url>` | 跳到指定 http(s) 地址 —— 例如豆包手机宣传片页面 |
| `/click <文字>` | 点击页面上包含该文字的按钮/链接 |
| `/fill <标签> <值>` | 按 placeholder/aria-label/label 找到输入框并填入 |
| `/help` | 帮助 |

## Siri 式功能说明

命令窗头部有彩色呼吸灯和 **功能说明** 按钮：点开后是一张能力卡片列表（类似发布会演示），每张卡显示图标、命令、作用；点卡片会把示例命令填进输入框。按 `Ctrl+Shift+Y` 收起/展开，`↑/↓` 翻历史。

## 安装

1. 桥接服务（与 DS 悬浮窗共用）：
   ```powershell
   powershell -ExecutionPolicy Bypass -File <repo>\tools\ds_parasite\start.ps1
   ```
2. Edge：`edge://extensions/` → 开发人员模式 → 加载解压缩的扩展 → 选 `<repo>\tools\edge_parasite\extension`。
3. 任意页面左下角出现命令窗；`Ctrl+Shift+Y` 可收起/展开，`↑/↓` 翻历史。

## 豆包宣传片体验怎么走

不预设具体 URL（活动页会变）：

```
/goto https://www.doubao.com/...     ← 你拿到的宣传片/手机体验页地址
/capture                            ← 把页面文字落到工厂
/note 豆包手机宣传片：卖点是……         ← 记录观察
```

之后回到 OpenCode 说“读 `reports/browser_capture/latest.json` 或最新 capture”，我按 A/B/C/D 复核进案例库。

## 边界

- **不执行任意代码**：`/goto /click /fill` 是白名单 DOM 动作；没有 `/js` 或 shell 任意执行。
- 不读 cookie、localStorage token、不代登录；`/fill` 只在你已经打开的页面里模拟输入。
- 桥接只监听 `127.0.0.1`，不做云端中继；`/note` 和 `/capture` 只写本地。
- 任何涉及购买、发布、删除的页面动作仍需你手动确认，我不会自动点。
- 捕获内容可能含个人信息；自动脱敏只覆盖手机号/邮箱/证件号，分享/上传前自己再过一遍。
- 扩展权限覆盖所有 http(s) 站点，安装前确认这是你自己的浏览器与机器。
