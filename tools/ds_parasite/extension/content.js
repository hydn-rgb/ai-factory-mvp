// Factory DS Parasite — 只运行在 chat.deepseek.com。
// 观察网页自己的 fetch（history_messages / share/content），不碰 token、不读 cookie。
(() => {
  const BRIDGE = "http://127.0.0.1:8791/ingest";
  const captured = {};
  let panel, statusEl, countEl;

  // 1) 寄生：包装 fetch，抓取网页自己的对话接口响应
  const origFetch = window.fetch.bind(window);
  window.fetch = async function (input, init) {
    const url = typeof input === "string" ? input : (input && input.url) || "";
    const res = await origFetch(input, init);
    if (/api\/v0\/(chat\/history_messages|share\/content|share\/create)/.test(url)) {
      try {
        const json = await res.clone().json();
        captured[url] = json;
        updateCount();
      } catch (_) {}
    }
    return res;
  };

  function updateCount() {
    if (countEl) countEl.textContent = "已捕获 " + Object.keys(captured).length + " 份接口响应";
  }
  function status(msg) { if (statusEl) statusEl.textContent = msg; }

  // 2) 悬浮窗（可拖动、可收起）
  function build() {
    panel = document.createElement("div");
    panel.id = "factory-ds-panel";
    panel.innerHTML = `
      <div style="display:flex;align-items:center;gap:6px;padding:6px 8px;background:#1f2937;color:#e5e7eb;border-radius:8px 8px 0 0;cursor:move;font:12px/1.4 system-ui">
        <b>⚙ Factory 捕获</b><span id="fds-count" style="opacity:.7"></span>
        <button id="fds-min" style="margin-left:auto;background:none;border:0;color:#e5e7eb;cursor:pointer">–</button>
      </div>
      <div id="fds-body" style="padding:8px;background:#111827;color:#e5e7eb;border-radius:0 0 8px 8px;font:12px/1.5 system-ui;width:250px">
        <div style="display:flex;gap:4px;flex-wrap:wrap">
          <button id="fds-now" style="flex:1">抓取当前对话</button>
          <button id="fds-share" style="flex:1">分享链接导入</button>
        </div>
        <div id="fds-status" style="margin-top:6px;opacity:.8;word-break:break-all">就绪；先登录 DS 并打开一段对话。</div>
      </div>`;
    Object.assign(panel.style, {
      position: "fixed", top: "80px", right: "24px", zIndex: "2147483647",
      background: "#111827", boxShadow: "0 6px 24px rgba(0,0,0,.45)", borderRadius: "8px",
      fontFamily: "system-ui", userSelect: "none",
    });
    document.body.appendChild(panel);
    countEl = panel.querySelector("#fds-count");
    statusEl = panel.querySelector("#fds-status");
    updateCount();

    let dragging = false, ox = 0, oy = 0;
    panel.querySelector("div").addEventListener("pointerdown", (e) => {
      if (e.target.tagName === "BUTTON") return;
      dragging = true; ox = e.clientX - panel.getBoundingClientRect().left; oy = e.clientY - panel.getBoundingClientRect().top;
      panel.setPointerCapture(e.pointerId);
    });
    panel.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      panel.style.left = (e.clientX - ox) + "px"; panel.style.top = (e.clientY - oy) + "px"; panel.style.right = "auto";
    });
    panel.addEventListener("pointerup", () => { dragging = false; });
    panel.querySelector("#fds-min").onclick = () => {
      const b = panel.querySelector("#fds-body");
      b.style.display = b.style.display === "none" ? "" : "none";
    };
    panel.querySelector("#fds-now").onclick = () => sendCurrent();
    panel.querySelector("#fds-share").onclick = () => {
      const link = prompt("粘贴 chat.deepseek.com/share/... 链接或 share_id：");
      if (link) importShare(link);
    };
  }

  function bestPayload() {
    const keys = Object.keys(captured);
    const key = keys.find((k) => /history_messages/.test(k)) || keys.find((k) => /share\/content/.test(k)) || keys[0];
    return key ? { key, payload: captured[key] } : null;
  }

  async function domFallback() {
    const nodes = [...document.querySelectorAll("[data-testid*='message'],[class*='message'],[class*='chat-item']")];
    const turns = nodes.map((n) => {
      const t = (n.innerText || "").trim();
      const r = /user|我|question|human/i.test(n.className + " " + (n.getAttribute("data-testid") || "")) ? "user" : "assistant";
      return { role: r, content: t };
    }).filter((x) => x.content.length > 1);
    return { messages: turns, title: document.title };
  }

  async function post(payload, source) {
    status("发送中…");
    try {
      const res = await origFetch(BRIDGE, {
        method: "POST", mode: "cors",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source, url: location.href, ts: Date.now(), payload }),
      });
      const j = await res.json();
      status(j.ok ? "已落盘 " + j.turns + " 回合" : ("失败：" + (j.error || res.status)));
    } catch (e) {
      status("桥接失败：" + e.message + "（先启动 bridge.js）");
    }
  }

  async function sendCurrent() {
    const best = bestPayload();
    if (best) return post(best.payload, "api:" + best.key);
    status("没抓到接口响应，尝试 DOM 兜底…");
    post(await domFallback(), "dom");
  }

  async function importShare(link) {
    const m = String(link).match(/(?:share\/)?([a-zA-Z0-9_-]{16,})/);
    if (!m) return status("链接里没找到 share_id");
    const id = m[1];
    try {
      const res = await origFetch("/api/v0/share/content?share_id=" + encodeURIComponent(id), { credentials: "omit" });
      const json = await res.json();
      captured["/api/v0/share/content?share_id=" + id] = json;
      updateCount();
      await post(json, "share:" + id);
    } catch (e) { status("分享读取失败：" + e.message); }
  }

  // 分享页自动读一次公开接口（同源，不需要登录）
  if (/^\/share\//.test(location.pathname)) {
    const id = location.pathname.split("/").filter(Boolean)[1];
    if (id) window.addEventListener("load", () => importShare(location.href));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build);
  else build();
})();
