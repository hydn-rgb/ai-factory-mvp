// Factory Edge Commander — 任意页面悬浮助手：选项行 + 输入行 + 模糊匹配 + 技能/项目直连。
// 白名单命令；不执行任意 JS；不读 cookie/token；所有本地动作走 127.0.0.1:8791。
(() => {
  const BRIDGE = "http://127.0.0.1:8791/command";
  const CAPS = [
    ["📊", "/status", "看工厂任务状态：open / done / cancelled"],
    ["✅", "/audit", "验收 T0/T1/T2 回执，确认没有假完成"],
    ["🔁", "/handoff", "拿最新交接文件，新窗口不用人肉传话"],
    ["📥", "/ds", "看 DS 悬浮窗最近一次捕获"],
    ["🔍", "/probe <url>", "探针网页：状态码 / 字节 / sha / 耗时"],
    ["📝", "/note <文本>", "记一条观察到本地收件箱（自动打码）"],
    ["📄", "/capture", "把当前页链接到工厂（正文 + URL + 标题）"],
    ["➡️", "/goto <url>", "跳到任意 http(s) 页面"],
    ["👆", "/click <文字>", "按文字点页面按钮 / 链接"],
    ["⌨️", "/fill <标签> <值>", "按 placeholder / label 填输入框"],
    ["📂", "/open_capture", "打开捕获文件保存目录"],
    ["🏭", "/mvp", "T0–T20 完成度、开放卡、发行 commit"],
    ["🗂", "/cases", "列出全部案例卡"],
    ["📕", "/case T1", "读案例卡：幻方 / 灵均 / T16–T20"],
    ["🛡", "/compliance", "T19 信源合规地图：G/Y/R + 5 类不碰"],
    ["📦", "/inventory", "在用资产清单与 sha"],
    ["🧪", "/selftest", "跑一次发行包自检"],
    ["🧩", "/skills", "列出已装技能（可模糊筛选）"],
    ["📖", "/skill <名称>", "读某技能的 SKILL.md 说明"],
    ["🗃", "/card T14", "读任务卡（T14/T15 仍未验证）"],
    ["🔎", "/find <关键词>", "按模糊词查技能 / 案例 / 任务卡"],
  ];
  const KW = {
    "/status": "状态 任务 卡 open done 收束 现在",
    "/audit": "审计 验收 回执 accept 核对",
    "/handoff": "交接 接力 新窗口 传话",
    "/ds": "ds deepseek 抓取 对话 捕获",
    "/probe": "探针 网址 链接 网页 检测",
    "/note": "记录 笔记 观察 写一条",
    "/capture": "链接本页 保存 截流 当前页 抓页面",
    "/goto": "跳转 打开 网页 地址",
    "/click": "点击 按钮 链接",
    "/fill": "填写 输入 输入框",
    "/open_capture": "目录 保存位置 打开 文件在哪",
    "/mvp": "mvp 项目 产品 完成度 发行 交付",
    "/cases": "案例 列表 卡片 所有",
    "/case": "幻方 灵均 案例 卡 highflyer lingjun",
    "/compliance": "合规 信源 红线 不能做什么",
    "/inventory": "资产 清单 在用",
    "/selftest": "自检 测试 验证 pass",
    "/skills": "技能 列表 能力",
    "/skill": "技能 说明 怎么用",
    "/card": "任务卡 卡片 t14 t15 开放",
    "/find": "查找 搜索 匹配 模糊 项目",
  };
  let root, input, logEl, capEl, optEl, skills = [], history = [], hi = -1, sel = -1, finding = false;

  function fuzzy(text, q) {
    const t = String(text || "").toLowerCase(), s = String(q || "").trim().toLowerCase();
    if (!s) return 0;
    if (t.includes(s)) return 100;
    let i = 0;
    for (const ch of t) if (ch === s[i]) i++;
    if (i === s.length) return 60;
    const parts = s.split(/[\s,，、]+/).filter(Boolean);
    if (parts.length > 1 && parts.every((x) => t.includes(x))) return 50;
    return 0;
  }
  function log(s) { logEl.textContent = String(s).slice(0, 3000); }
  function visible(el) { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== "hidden"; }

  function build() {
    root = document.createElement("div");
    root.id = "factory-edge-commander";
    root.innerHTML = `
      <div id="fec-head" style="padding:5px 8px;background:linear-gradient(90deg,#312e81,#7c3aed,#db2777);color:#fff;cursor:move;font:12px system-ui;border-radius:8px 8px 0 0">
        <span id="fec-orb" style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#a7f3d0;margin-right:6px;box-shadow:0 0 8px #34d399;animation:fecpulse 2s infinite"></span>
        <b>Factory 助手</b><span style="opacity:.7"> 选项行 / 输入行 / 模糊匹配</span>
        <button id="fec-cards" style="float:right;background:rgba(255,255,255,.18);border:0;color:#fff;border-radius:4px;cursor:pointer;padding:1px 5px">功能说明</button>
        <button id="fec-link" style="float:right;background:#34d399;color:#052e16;border:0;border-radius:4px;cursor:pointer;padding:1px 5px;margin-right:4px;font-weight:bold">⚡链接本页</button>
        <button id="fec-close" style="float:right;background:none;border:0;color:#fff;cursor:pointer;margin-right:4px">×</button>
      </div>
      <div style="background:rgba(2,6,23,.92);backdrop-filter:blur(10px);color:#e2e8f0;padding:8px;font:12px/1.5 system-ui;width:380px;border-radius:0 0 8px 8px">
        <input id="fec-input" placeholder="输入模糊词：状态 / 幻方 / 合规 / 技能… 或 /命令" style="width:100%;box-sizing:border-box;background:#1e293b;color:#e2e8f0;border:1px solid #334155;border-radius:5px;padding:6px;font:12px system-ui">
        <div id="fec-options" style="margin-top:6px;max-height:220px;overflow:auto"></div>
        <div id="fec-cap" style="display:none;margin-top:8px;max-height:260px;overflow:auto"></div>
        <pre id="fec-log" style="max-height:120px;overflow:auto;white-space:pre-wrap;word-break:break-all;margin:6px 0 0;opacity:.85"></pre>
      </div>
      <style>@keyframes fecpulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.45;transform:scale(.8)}}</style>`;
    Object.assign(root.style, { position: "fixed", left: "20px", bottom: "20px", zIndex: "2147483646", boxShadow: "0 6px 24px rgba(0,0,0,.5)", borderRadius: "8px" });
    document.body.appendChild(root);
    input = root.querySelector("#fec-input");
    logEl = root.querySelector("#fec-log");
    capEl = root.querySelector("#fec-cap");
    optEl = root.querySelector("#fec-options");
    capEl.innerHTML = '<div style="font-size:11px;opacity:.7;margin-bottom:6px">Siri 式能力说明 · 点卡片填入命令</div>' +
      '<div style="display:grid;gap:4px">' + CAPS.map((c) => optionRow(c[0], c[1], c[2])).join('') + '</div>';
    capEl.querySelectorAll("[data-cmd]").forEach(bindRow);
    root.querySelector("#fec-link").onclick = () => run("/capture");
    root.querySelector("#fec-cards").onclick = () => { capEl.style.display = capEl.style.display === "none" ? "" : "none"; };
    root.querySelector("#fec-close").onclick = () => { root.style.display = "none"; };
    input.addEventListener("input", () => { sel = -1; renderOptions(input.value); maybeFind(input.value); });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); const q = input.value.trim(); if (!q && sel >= 0) { const rows = optEl.querySelectorAll("[data-cmd]"); if (rows[sel]) run(rows[sel].getAttribute("data-cmd")); return; } run(q); input.value = ""; }
      if (e.key === "ArrowDown") { e.preventDefault(); const rows = optEl.querySelectorAll("[data-cmd]"); sel = Math.min(rows.length - 1, sel + 1); paintSel(rows); }
      if (e.key === "ArrowUp") { e.preventDefault(); const rows = optEl.querySelectorAll("[data-cmd]"); sel = Math.max(0, sel - 1); paintSel(rows); }
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") return;
      if (e.key === "ArrowUp" && !input.value) { e.preventDefault(); hi = Math.max(0, hi - 1); if (history[hi]) input.value = history[hi]; }
    });
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === "y") {
        root.style.display = root.style.display === "none" ? "" : "none";
        if (root.style.display !== "none") input.focus();
      }
    });
    let drag = false, ox = 0, oy = 0;
    root.querySelector("#fec-head").addEventListener("pointerdown", (e) => {
      if (e.target.tagName === "BUTTON") return;
      drag = true; ox = e.clientX - root.getBoundingClientRect().left; oy = e.clientY - root.getBoundingClientRect().top; root.setPointerCapture(e.pointerId);
    });
    root.addEventListener("pointermove", (e) => { if (!drag) return; root.style.left = (e.clientX - ox) + "px"; root.style.top = (e.clientY - oy) + "px"; root.style.bottom = "auto"; });
    root.addEventListener("pointerup", () => { drag = false; });
    loadSkills();
    renderOptions("");
  }

  function optionRow(icon, cmd, desc) {
    return '<div data-cmd="' + cmd.replace(/<[^>]+>/g, "").trim() + '" style="display:flex;gap:6px;align-items:center;padding:4px 6px;background:#1e293b;border:1px solid #334155;border-radius:6px;cursor:pointer">' +
      '<span>' + icon + '</span><span><b>' + cmd + '</b><br><span style="opacity:.7">' + desc + '</span></span></div>';
  }
  function bindRow(el) {
    const cmd = el.getAttribute("data-cmd");
    el.onclick = () => {
      if (cmd === "/probe") input.value = "/probe " + location.href;
      else input.value = cmd;
      input.focus();
      renderOptions(input.value);
    };
  }
  function paintSel(rows) {
    rows.forEach((r, i) => { r.style.borderColor = i === sel ? "#34d399" : "#334155"; });
    if (rows[sel]) rows[sel].scrollIntoView({ block: "nearest" });
  }

  function renderOptions(q) {
    const rows = [];
    const seen = new Set();
    const add = (icon, cmd, desc, text) => {
      const key = cmd.replace(/<[^>]+>/g, "").trim();
      if (seen.has(key)) return;
      if (q && !fuzzy(text + " " + cmd + " " + (KW[key] || ""), q)) return;
      seen.add(key);
      rows.push(optionRow(icon, cmd, desc));
    };
    for (const c of CAPS) add(c[0], c[1], c[2], c[2]);
    if (q) for (const s of skills) add("🧩", "/skill " + s.name, s.description || s.name, s.name + " " + s.description);
    optEl.innerHTML = rows.join('') || '<div style="opacity:.6;padding:4px">没有匹配项，试试 /find 关键词</div>';
    optEl.querySelectorAll("[data-cmd]").forEach(bindRow);
    sel = -1;
  }

  async function maybeFind(q) {
    if (!q || q.startsWith("/") || finding || q.length < 2) return;
    finding = true;
    try {
      const j = JSON.parse(await postRaw({ cmd: "find", arg: q }));
      if (j.ok && j.hits) {
        const extra = j.hits.slice(0, 8).map((h) => optionRow(h.type === "skill" ? "🧩" : h.type === "case" ? "📕" : "🗃", h.cmd, h.name)).join("");
        optEl.innerHTML = extra + optEl.innerHTML;
        optEl.querySelectorAll("[data-cmd]").forEach(bindRow);
      }
    } catch {} finally { finding = false; }
  }

  async function loadSkills() {
    try { const j = JSON.parse(await postRaw({ cmd: "skills" })); skills = j.ok ? j.skills || [] : []; } catch { skills = []; }
  }
  function postRaw(body) {
    return new Promise((resolve) => {
      fetch(BRIDGE, { method: "POST", mode: "cors", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
        .then((r) => r.text()).then(resolve).catch((e) => resolve(JSON.stringify({ ok: false, error: e.message })));
    });
  }
  async function post(cmd, arg, extra) {
    try {
      const j = JSON.parse(await postRaw({ cmd, arg, ...(extra || {}) }));
      if (cmd === "skills" && j.ok) skills = j.skills || [];
      return JSON.stringify(j, null, 1);
    } catch (e) { return "桥接失败：" + e.message + "（先运行 start.ps1）"; }
  }

  function clickText(text) {
    const nodes = [...document.querySelectorAll("button,a,[role=button],input[type=button],input[type=submit]")];
    const hit = nodes.find((n) => visible(n) && ((n.innerText || n.value || n.ariaLabel || n.title || "").includes(text)));
    if (!hit) return "没找到可点元素：" + text;
    hit.click(); return "已点击：" + (hit.innerText || hit.value || text);
  }
  function fillLabel(label, value) {
    let field = [...document.querySelectorAll("input,textarea,[contenteditable=true]")].find((n) =>
      visible(n) && ((n.placeholder || n.ariaLabel || n.name || n.id || "").toLowerCase().includes(label.toLowerCase())));
    if (!field) { const lab = [...document.querySelectorAll("label")].find((n) => (n.innerText || "").includes(label)); if (lab && lab.control) field = lab.control; }
    if (!field) return "没找到输入框：" + label;
    field.value = value;
    field.dispatchEvent(new Event("input", { bubbles: true }));
    field.dispatchEvent(new Event("change", { bubbles: true }));
    return "已填入：" + label;
  }
  function gotoUrl(url) {
    const u = new URL(url, location.href);
    if (!["http:", "https:"].includes(u.protocol)) return "仅 http(s)";
    location.href = u.href; return "跳转：" + u.href;
  }

  async function run(raw) {
    const line = String(raw || "").trim();
    if (!line) return;
    history.push(line); hi = history.length;
    log("执行：" + line);
    const m = line.match(/^\/(\S+)\s*([\s\S]*)$/);
    if (!m) { log(await post("find", line)); return; }
    const cmd = m[1].toLowerCase(), arg = m[2].trim();
    if (cmd === "goto") return log(gotoUrl(arg));
    if (cmd === "click") return log(clickText(arg));
    if (cmd === "fill") { const fm = arg.match(/^(\S+)\s+([\s\S]+)$/); return log(fm ? fillLabel(fm[1], fm[2]) : "用法：/fill 标签 值"); }
    if (cmd === "capture") return log(await post("capture", "", { text: document.body.innerText.slice(0, 200000), url: location.href, title: document.title }));
    if (cmd === "help") return log(["状态 /status", "验收 /audit", "交接 /handoff", "DS /ds", "探针 /probe <url>", "记录 /note", "链接本页 /capture", "技能 /skills /skill", "模糊查找 /find"].join("\n"));
    log(await post(cmd, arg));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
  else build();
})();
