// Factory Edge Commander — 任意页面悬浮命令窗。
// 白名单命令；不执行任意 JS；不读 cookie/token；所有本地动作走 127.0.0.1:8791。
(() => {
  const BRIDGE = "http://127.0.0.1:8791/command";
  let root, input, logEl, history = [], hi = -1;

  function build() {
    root = document.createElement("div");
    root.id = "factory-edge-commander";
    root.innerHTML = `
      <div id="fec-head" style="padding:5px 8px;background:#0f172a;color:#e2e8f0;cursor:move;font:12px system-ui;border-radius:8px 8px 0 0">
        <b>⌘ Factory 命令窗</b><span style="opacity:.6"> /help</span>
        <button id="fec-close" style="float:right;background:none;border:0;color:#e2e8f0;cursor:pointer">×</button>
      </div>
      <div style="background:#020617;color:#e2e8f0;padding:8px;font:12px/1.5 system-ui;width:330px;border-radius:0 0 8px 8px">
        <input id="fec-input" placeholder="/status  /probe https://...  /goto ..." style="width:100%;box-sizing:border-box;background:#1e293b;color:#e2e8f0;border:1px solid #334155;border-radius:5px;padding:6px;font:12px system-ui">
        <pre id="fec-log" style="max-height:150px;overflow:auto;white-space:pre-wrap;word-break:break-all;margin:6px 0 0;opacity:.85"></pre>
      </div>`;
    Object.assign(root.style, { position: "fixed", left: "20px", bottom: "20px", zIndex: "2147483646", boxShadow: "0 6px 24px rgba(0,0,0,.5)", borderRadius: "8px" });
    document.body.appendChild(root);
    input = root.querySelector("#fec-input");
    logEl = root.querySelector("#fec-log");
    root.querySelector("#fec-close").onclick = () => { root.style.display = "none"; };
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); run(input.value); input.value = ""; }
      if (e.key === "ArrowUp") { e.preventDefault(); hi = Math.max(0, hi - 1); if (history[hi]) input.value = history[hi]; }
      if (e.key === "ArrowDown") { e.preventDefault(); hi = Math.min(history.length, hi + 1); input.value = history[hi] || ""; }
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
    root.addEventListener("pointermove", (e) => {
      if (!drag) return;
      root.style.left = (e.clientX - ox) + "px"; root.style.top = (e.clientY - oy) + "px"; root.style.bottom = "auto";
    });
    root.addEventListener("pointerup", () => { drag = false; });
    log("就绪。Ctrl+Shift+Y 收起/展开。");
  }

  function log(s) { logEl.textContent = String(s).slice(0, 3000); }
  function visible(el) { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== "hidden"; }

  function clickText(text) {
    const nodes = [...document.querySelectorAll("button,a,[role=button],input[type=button],input[type=submit]")];
    const hit = nodes.find((n) => visible(n) && ((n.innerText || n.value || n.ariaLabel || n.title || "").includes(text)));
    if (!hit) return "没找到可点元素：" + text;
    hit.click();
    return "已点击：" + (hit.innerText || hit.value || text);
  }
  function fillLabel(label, value) {
    let field = [...document.querySelectorAll("input,textarea,[contenteditable=true]")].find((n) =>
      visible(n) && ((n.placeholder || n.ariaLabel || n.name || n.id || "").toLowerCase().includes(label.toLowerCase())));
    if (!field) {
      const lab = [...document.querySelectorAll("label")].find((n) => (n.innerText || "").includes(label));
      if (lab && lab.control) field = lab.control;
    }
    if (!field) return "没找到输入框：" + label;
    field.value = value;
    field.dispatchEvent(new Event("input", { bubbles: true }));
    field.dispatchEvent(new Event("change", { bubbles: true }));
    return "已填入：" + label;
  }
  function gotoUrl(url) {
    const u = new URL(url, location.href);
    if (!["http:", "https:"].includes(u.protocol)) return "仅 http(s)";
    location.href = u.href;
    return "跳转：" + u.href;
  }

  async function post(cmd, arg, extra) {
    try {
      const r = await fetch(BRIDGE, { method: "POST", mode: "cors", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cmd, arg, ...(extra || {}) }) });
      const j = await r.json();
      return JSON.stringify(j, null, 1);
    } catch (e) { return "桥接失败：" + e.message + "（先运行 start.ps1）"; }
  }

  async function run(raw) {
    const line = String(raw || "").trim();
    if (!line) return;
    history.push(line); hi = history.length;
    log("执行：" + line);
    const m = line.match(/^\/(\S+)\s*([\s\S]*)$/);
    if (!m) return log("命令要以 / 开头；/help 看列表");
    const cmd = m[1].toLowerCase(), arg = m[2].trim();
    if (cmd === "goto") return log(gotoUrl(arg));
    if (cmd === "click") return log(clickText(arg));
    if (cmd === "fill") {
      const fm = arg.match(/^(\S+)\s+([\s\S]+)$/);
      return log(fm ? fillLabel(fm[1], fm[2]) : "用法：/fill 标签 值");
    }
    if (cmd === "capture") {
      return log(await post("capture", "", { text: document.body.innerText.slice(0, 200000), url: location.href, title: document.title }));
    }
    if (cmd === "help") {
      return log(["/status 任务状态", "/audit 回执验收", "/handoff 最新交接", "/ds 最近捕获",
        "/probe <url> 探针", "/note <文本> 记一条", "/capture 捕获本页", "/goto <url> 跳转",
        "/click <文字> 点击", "/fill <标签> <值> 填写"].join("\n"));
    }
    log(await post(cmd, arg));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
  else build();
})();
