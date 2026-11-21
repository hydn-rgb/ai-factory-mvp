# DS Parasite · 悬浮窗寄生捕获（本机）

解决"DS 网页没有前端入口、人工导出慢"：在 DeepSeek 网页上挂一个可拖动悬浮窗，自动/一键把对话送到本机工厂。**不上传第三方、不读 cookie 文件、不保存 token**。

## 组成

| 文件 | 作用 |
|---|---|
| `extension/manifest.json` + `content.js` | Edge/Chrome 扩展：只在 `chat.deepseek.com` 注入悬浮窗；包装网页自己的 fetch，观察 `history_messages` / `share/content` 响应 |
| `bridge.js` | 本机服务 `127.0.0.1:8791`，接收对话，写 `reports/ds_capture/capture_*.json` 与脱敏 `card_*.md`，并更新 `latest.json` |
| `start.ps1` | 启动桥接服务 |

## 安装（一次）

1. 启动桥接：
   ```powershell
   powershell -ExecutionPolicy Bypass -File D:\AI_Factory\tools\ds_parasite\start.ps1
   ```
   看到 `DS bridge on http://127.0.0.1:8791` 即可；窗口别关。
2. Edge 地址栏打开 `edge://extensions/` → 开启"开发人员模式" → "加载解压缩的扩展" → 选 `D:\AI_Factory\tools\ds_parasite\extension`。
3. 打开 `https://chat.deepseek.com/` 登录。悬浮窗出现在右上角，可拖动、可最小化。

## 用法

- 打开一段对话：网页自己会请求 `history_messages`，扩展自动捕获；点 **抓取当前对话** 即落盘。
- 拿到分享链接：点 **分享链接导入** 粘贴链接；扩展在 chat.deepseek.com 源内请求公开接口 `/api/v0/share/content`，不受 CORS 限制，也不需要登录。分享页会自动导入。
- 落盘后告诉我一句"读 `reports/ds_capture/latest.json`"，我会按 A/B/C/D 复核进案例卡。

## 为什么这样设计

- **分享链接是公开接口**：`GET /api/v0/share/content?share_id=...` 不带 cookie 也返回正文；但服务端没有 CORS 头，只能从 chat.deepseek.com 源里发。悬浮窗正好在这个源里。
- **不抓网页 DOM 当主路径**：DOM 改版就碎；观察网页自己的接口响应更稳。DOM 只作兜底。
- **不碰凭证**：扩展不读 localStorage.userToken、不读 cookie，只复制对话响应体；token 只在网页自己的请求里出现。

## 边界（重要）

1. **分享链接 = 公开发布**。任何拿到链接的人都能看，且可能被 Google 收录（`site:chat.deepseek.com/share`）。不要分享含密钥、个人信息、内部资料的对话；用完在 DS：设置 → 数据 → 分享链接 → 管理里删掉。
2. 桥接只监听 `127.0.0.1`，扩展只授权 `chat.deepseek.com` 与本机桥接；不接任何云端中继。
3. 自动脱敏只覆盖手机号/邮箱/证件号；更敏感的内容请自己先清理，或只导分享页里筛过的片段。
4. 网页内部接口可能改版，失败时面板会如实报错，不会假装成功。

## 保存位置与功能说明

- 落盘目录固定为 `D:\AI_Factory\reports\ds_capture\`：`capture_*.json`（原始）、`card_*.md`（脱敏案例卡）、`latest.json`（最新指针）。
- 悬浮窗抓到后会在状态栏显示**完整保存路径**；点 **打开保存目录** 可直接用资源管理器打开。
- DS 分享页的正文在 `fragments` 里（`REQUEST`/`RESPONSE`，`THINK` 跳过）；解析器已支持，分享链接导入实测 20 回合成功。

## 自检

```powershell
curl.exe http://127.0.0.1:8791/health
```
返回 `{"ok":true,"captures":N}` 即正常。
