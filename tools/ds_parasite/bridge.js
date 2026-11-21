// DS Parasite Bridge — 只监听 127.0.0.1，接收浏览器扩展抓到的 DeepSeek 对话，
// 在本地生成原始 JSON + 脱敏案例卡。不联网外发、不读 cookie、不存 token。
import http from "node:http";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = process.env.FACTORY_ROOT || join(HERE, "..", "..");
const OUT = join(ROOT, "reports", "ds_capture");
const LOG = join(HERE, "bridge.log");
const PORT = Number(process.env.DS_BRIDGE_PORT || 8791);
const ALLOWED_ORIGIN = "https://chat.deepseek.com";

function sha(s) { return createHash("sha256").update(s).digest("hex"); }
function log(row) {
  try { appendFileSync(LOG, JSON.stringify({ ts: new Date().toISOString(), ...row }) + "\n", "utf8"); } catch {}
}
function redact(s) {
  return String(s || "")
    .replace(/1[3-9]\d{9}/g, "[手机号]")
    .replace(/[\w.+-]+@[\w-]+\.[\w.]+/g, "[邮箱]")
    .replace(/\b\d{17}[\dXx]\b/g, "[证件号]");
}

function pickMessages(payload) {
  const candidates = [
    payload?.data?.biz_data?.messages,
    payload?.biz_data?.messages,
    payload?.data?.messages,
    payload?.messages,
    payload?.data?.biz_data?.chat_messages,
  ];
  for (const arr of candidates) if (Array.isArray(arr)) return arr;
  if (Array.isArray(payload)) return payload;
  return [];
}

function textOf(msg) {
  if (typeof msg === "string") return msg;
  // DeepSeek share 接口把正文放在 fragments 里：REQUEST / RESPONSE / THINK
  if (Array.isArray(msg?.fragments)) {
    return msg.fragments.filter((f) => f && f.type !== "THINK").map((f) => f.content || "").join("\n");
  }
  const c = msg?.content ?? msg?.text ?? msg?.message ?? msg?.body ?? "";
  if (typeof c === "string") return c;
  if (Array.isArray(c)) return c.map((x) => (typeof x === "string" ? x : x?.text || x?.content || "")).join("\n");
  return JSON.stringify(c || msg);
}

function roleOf(msg) {
  const r = String(msg?.role ?? msg?.author ?? msg?.type ?? msg?.sender ?? "").toLowerCase();
  if (/user|human|me|question/.test(r)) return "user";
  if (/assistant|model|deepseek|bot|answer/.test(r)) return "assistant";
  return /^user$/i.test(String(msg?.role_type || "")) ? "user" : "assistant";
}

function normalize(payload) {
  const msgs = pickMessages(payload);
  return msgs.map((m) => ({ role: roleOf(m), text: redact(textOf(m)).slice(0, 12000) })).filter((x) => x.text.trim());
}

function card(turns, meta) {
  return [
    "# DS 网页版对话本地捕获（待人工分级）",
    "",
    "- captured_at: " + new Date().toISOString(),
    "- source: " + (meta.source || "unknown"),
    "- page: " + (meta.url || ""),
    "- turns: " + turns.length,
    "- payload_sha256: " + meta.sha,
    "- 脱敏: 手机号/邮箱/证件号已替换为占位符；完整版未落盘",
    "",
    "> 模型输出不是事实。每条结论仍需按 A/B/C/D 复核，D 级不作证据。",
    "",
    ...turns.map((t, i) => `## 回合 ${i + 1} · ${t.role}\n\n${t.text}`),
    "",
  ].join("\n");
}

const PYTHON = process.env.FACTORY_PYTHON || "C:/Program Files/python/python.exe";

function cmdStatus() {
  const p = join(ROOT, "ops", "bus", "state.json");
  const d = JSON.parse(readFileSync(p, "utf8"));
  const counts = {};
  for (const t of Object.values(d.tasks || {})) counts[t.status] = (counts[t.status] || 0) + 1;
  return { ok: true, cmd: "status", counts, updated_at: d.updated_at };
}
function cmdAudit() {
  const script = join(ROOT, "ops", "bus", "audit.py");
  const r = spawnSync(PYTHON, [script, "--json"], { cwd: ROOT, encoding: "utf8", maxBuffer: 8 * 1024 * 1024, timeout: 60_000 });
  if (r.error) throw r.error;
  const rows = JSON.parse(r.stdout || "[]");
  return { ok: true, cmd: "audit", total: rows.length, accepted: rows.filter((x) => x.accepted).length,
    focus: rows.filter((x) => ["T0", "T1", "T2"].includes(x.task_id)).map((x) => ({ task: x.task_id, verdict: x.verdict })) };
}
function cmdHandoff() {
  const dir = join(ROOT, "reports", "mvp", "handoff");
  const files = readdirSync(dir).filter((f) => f.endsWith(".md") && f.startsWith("handoff_")).sort();
  if (!files.length) return { ok: false, error: "无 handoff 文件" };
  const p = join(dir, files[files.length - 1]);
  const b = readFileSync(p);
  return { ok: true, cmd: "handoff", path: p, sha256: sha(b.toString("utf8")) };
}
function cmdDs() {
  const p = join(ROOT, "reports", "ds_capture", "latest.json");
  if (!existsSync(p)) return { ok: false, error: "尚无 DS 捕获" };
  return { ok: true, cmd: "ds", ...JSON.parse(readFileSync(p, "utf8")) };
}

const CASE_MAP = {
  T0: "reports/mvp/T0_MVP_SCOPE.md", T1: "reports/cases/highflyer_v4.md", T2: "reports/cases/lingjun_v4.md",
  T16: "reports/cases/T16_bigtech_cross_anchors.md", T17: "reports/cases/T17_bankruptcy_10cases.md",
  T18: "reports/cases/T18_developer_epitaphs.md", T19: "reports/compliance/T19_source_compliance_map.md",
  T20: "reports/cases/T20_advisor_observation_forms.md",
};
function cmdCase(arg) {
  const id = String(arg || "").toUpperCase();
  const rel = CASE_MAP[id];
  if (!rel) return { ok: false, error: "可用案例：" + Object.keys(CASE_MAP).join(",") };
  const p = join(ROOT, rel);
  if (!existsSync(p)) return { ok: false, error: "文件不存在：" + rel };
  const b = readFileSync(p);
  return { ok: true, cmd: "case", id, path: p, sha256: sha(b.toString("utf8")), bytes: b.length, excerpt: b.toString("utf8").slice(0, 1800) };
}
function cmdCases() {
  const files = [];
  for (const dir of ["reports/cases", "reports/mvp", "reports/compliance"]) {
    const d = join(ROOT, dir);
    if (existsSync(d)) for (const f of readdirSync(d).filter((x) => x.endsWith(".md"))) files.push(dir + "/" + f);
  }
  return { ok: true, cmd: "cases", count: files.length, files: files.slice(0, 120) };
}
function cmdMvp() {
  const state = JSON.parse(readFileSync(join(ROOT, "ops", "bus", "state.json"), "utf8"));
  const counts = {};
  for (const t of Object.values(state.tasks || {})) counts[t.status] = (counts[t.status] || 0) + 1;
  const release = join(ROOT, "dist", "ai-factory-mvp");
  let commit = "unknown";
  if (existsSync(release)) {
    const r = spawnSync("git", ["-C", release, "log", "-1", "--format=%h %s"], { encoding: "utf8", timeout: 10_000 });
    if (!r.error && r.stdout) commit = r.stdout.trim();
  }
  return { ok: true, cmd: "mvp", counts, cards: Object.keys(state.tasks || {}).length, receipts: readdirSync(join(ROOT, "ops", "bus", "out")).filter((f) => /^T\d+\.json$/.test(f)).length, release_commit: commit, open: Object.entries(state.tasks || {}).filter(([, v]) => v.status === "todo" || v.status === "doing").map(([k]) => k) };
}
function cmdDoc(rel, cmd) {
  const p = join(ROOT, rel);
  if (!existsSync(p)) return { ok: false, error: "文件不存在：" + rel };
  const t = readFileSync(p, "utf8");
  return { ok: true, cmd, path: p, sha256: sha(t), excerpt: t.slice(0, 2200) };
}
function cmdSelftest() {
  const script = join(ROOT, "dist", "ai-factory-mvp", "selftest.ps1");
  if (!existsSync(script)) return { ok: false, error: "selftest.ps1 不存在" };
  const r = spawnSync("powershell", ["-ExecutionPolicy", "Bypass", "-File", script], { cwd: join(ROOT, "dist", "ai-factory-mvp"), encoding: "utf8", timeout: 180_000, maxBuffer: 4 * 1024 * 1024 });
  // powershell.exe 重定向时偶尔输出 UTF-16LE，去掉空字节再匹配
  const out = (String(r.stdout || "") + String(r.stderr || "")).replace(/\0/g, "");
  return { ok: !r.error && r.status === 0 && /SELFTEST PASS/.test(out), cmd: "selftest", tail: out.slice(-1200) };
}
function cmdNote(arg) {
  if (!arg) return { ok: false, error: "用法：/note 内容" };
  const dir = join(ROOT, "reports", "inbox");
  mkdirSync(dir, { recursive: true });
  const p = join(dir, "edge_notes.md");
  appendFileSync(p, "\n- " + new Date().toISOString() + " " + redact(arg) + "\n", "utf8");
  return { ok: true, cmd: "note", path: p };
}
async function cmdProbe(arg) {
  const url = String(arg || "").trim();
  let u;
  try { u = new URL(url); } catch { return { ok: false, error: "URL 非法" }; }
  if (!["http:", "https:"].includes(u.protocol)) return { ok: false, error: "仅 http(s)" };
  const t0 = Date.now();
  try {
    const r = await fetch(url, { redirect: "follow", signal: AbortSignal.timeout(12_000), headers: { "user-agent": "factory-edge-parasite/1.0" } });
    const b = Buffer.from(await r.arrayBuffer());
    return { ok: true, cmd: "probe", url, status: r.status, bytes: b.length, sha256: sha(b), elapsed_ms: Date.now() - t0, grade: r.ok ? "A/B 候选，需人工判级" : "D（不作证据）" };
  } catch (e) { return { ok: false, cmd: "probe", error: String(e && e.message || e), grade: "D" }; }
}
function cmdCapture(input) {
  const text = String(input.text || "").slice(0, 200_000);
  if (!text.trim()) return { ok: false, error: "没有页面文本" };
  const dir = join(ROOT, "reports", "browser_capture");
  mkdirSync(dir, { recursive: true });
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
  const p = join(dir, "capture_" + ts + ".md");
  writeFileSync(p, ["# 浏览器页面捕获", "", "- url: " + (input.url || ""), "- title: " + (input.title || ""), "- captured_at: " + new Date().toISOString(), "- sha256: " + sha(text), "", redact(text)].join("\n"), "utf8");
  return { ok: true, cmd: "capture", path: p, sha256: sha(text), bytes: text.length };
}

function fuzzyScore(text, q) {
  const t = String(text || "").toLowerCase();
  const s = String(q || "").trim().toLowerCase();
  if (!s) return 0;
  if (t.includes(s)) return 100;
  // 中文/英文按字符子序列匹配，允许中间隔字
  let i = 0;
  for (const ch of t) if (ch === s[i]) i++;
  if (i === s.length) return 60;
  const tokens = s.split(/[\s,，、]+/).filter(Boolean);
  if (tokens.length > 1 && tokens.every((x) => t.includes(x))) return 50;
  return 0;
}
function skillDirs() {
  const dirs = [join(ROOT, ".opencode", "skills")];
  try {
    const cfg = JSON.parse(readFileSync(join(process.env.USERPROFILE || "", ".config", "opencode", "opencode.json"), "utf8"));
    for (const p of cfg.skills || []) if (p) dirs.push(Path_isAbsolute(p) ? p : join(ROOT, String(p).replace(/^D:\/AI_Factory\//i, "")));
  } catch {}
  return dirs;
}
function Path_isAbsolute(p) { return /^[A-Za-z]:[\\/]/.test(String(p)) || String(p).startsWith("/"); }
const ALIAS_OVERRIDE = {
  "psyche-card-forge": ["角色卡锻造", "本地生成角色卡与世界书，含完整/脱敏/马赛克三版"],
  "persona-case-simulator": ["人物案例模拟", "用真实人物公开资料生成带证据级的可交互角色卡"],
  "human-network-graph": ["人物关系图谱", "把真人角色卡与关系交集结构化成可检索图谱"],
  "whitehat-socratic-mentor": ["白客苏格拉底导师", "按角色卡画像个性化引导零基础转型学习路线"],
  "compliance-agency-guard": ["合规机构守卫", "检查对外动作是否越过合规与机构红线"],
};
function friendly(desc, name) {
  const raw = String(desc || "").replace(/\s+/g, " ").trim();
  const first = raw.split(/[。；;，,|｜]/)[0].slice(0, 46);
  return { alias: ALIAS_OVERRIDE[name]?.[0] || first || name, purpose: ALIAS_OVERRIDE[name]?.[1] || (raw.length > 46 ? raw.slice(0, 46) + "…" : raw) || "用途见 SKILL.md" };
}
const SKILL_CATALOG_PY = "import sys,json;sys.path.insert(0,'.');import skill_catalog;print(json.dumps([{k:(str(v) if k=='path' else v) for k,v in r.items()} for r in skill_catalog.scan()],ensure_ascii=False))";
function scanSkillsLocal() {
  const out = [];
  for (const dir of skillDirs()) {
    let entries = [];
    try { entries = readdirSync(dir); } catch { continue; }
    for (const e of entries) {
      let p = join(dir, e, "SKILL.md");
      if (!existsSync(p)) p = join(dir, e, "skills", "SKILL.md");
      if (!existsSync(p)) continue;
      const t = readFileSync(p, "utf8");
      const nm = t.match(/^name:\s*(.+)$/m);
      const ds = t.match(/^description:\s*(.+)$/m);
      const name = (nm && nm[1] || e).trim();
      const desc = (ds && ds[1] || "").trim().slice(0, 300);
      const f = friendly(desc, name);
      out.push({ name, description: desc, alias: f.alias, purpose: f.purpose, category: "其他", path: p });
    }
  }
  return out;
}
function allSkills() {
  // 优先用飞书技能表同源的 skill_catalog.py，拿到中文一句话用途与分类
  try {
    const r = spawnSync(PYTHON, ["-X", "utf8", "-c", SKILL_CATALOG_PY], {
      cwd: join(ROOT, "cyber_cockpit", "tools"), encoding: "utf8", timeout: 30_000, maxBuffer: 4 * 1024 * 1024,
    });
    if (!r.error && r.status === 0 && r.stdout) {
      const rows = JSON.parse(r.stdout).map((x) => {
        const alias = ALIAS_OVERRIDE[x.name]?.[0] || String(x.purpose || "").split(/[，。；,;]/)[0].slice(0, 14) || x.name;
        const purpose = ALIAS_OVERRIDE[x.name]?.[1] || x.purpose || x.description || "用途见 SKILL.md";
        return { name: x.name, description: x.description || "", alias, purpose, category: x.category || "其他", path: x.path };
      });
      if (rows.length) return rows;
    }
  } catch {}
  return scanSkillsLocal();
}
function cmdSkills(arg) {
  let list = allSkills();
  if (arg) {
    list = list.map((s) => ({ ...s, score: fuzzyScore(s.name + " " + s.alias + " " + s.purpose + " " + s.description, arg) })).filter((s) => s.score > 0).sort((a, b) => b.score - a.score);
  }
  return { ok: true, cmd: "skills", count: list.length, skills: list.slice(0, 200).map(({ name, alias, purpose, category, path }) => ({ name, alias, purpose, category, path })) };
}
function cmdSkill(arg) {
  const q = String(arg || "").trim();
  const list = allSkills().map((s) => ({ ...s, score: fuzzyScore(s.name + " " + s.alias + " " + s.purpose, q) })).filter((s) => s.score > 0).sort((a, b) => b.score - a.score);
  if (!list.length) return { ok: false, error: "没匹配到技能：" + q };
  const s = list[0];
  const t = readFileSync(s.path, "utf8");
  return { ok: true, cmd: "skill", name: s.name, alias: s.alias, purpose: s.purpose, category: s.category, path: s.path, score: s.score, excerpt: t.slice(0, 3000) };
}
function cmdCard(arg) {
  const id = String(arg || "").toUpperCase().match(/T\d+/)?.[0];
  if (!id) return { ok: false, error: "用法：/card T14" };
  const p = join(ROOT, "ops", "bus", "tasks", id + ".md");
  if (!existsSync(p)) return { ok: false, error: "任务卡不存在：" + id };
  const t = readFileSync(p, "utf8");
  return { ok: true, cmd: "card", id, path: p, sha256: sha(t), excerpt: t.slice(0, 2200) };
}
function cmdFind(arg) {
  const q = String(arg || "").trim();
  if (!q) return { ok: false, error: "用法：/find 关键词" };
  const hits = [];
  for (const s of allSkills()) {
    const sc = fuzzyScore(s.name + " " + s.alias + " " + s.purpose + " " + s.description, q);
    if (sc) hits.push({ type: "skill", name: s.alias + "（" + s.name + "）", cmd: "/skill " + s.name, score: sc, purpose: s.purpose, path: s.path });
  }
  const CASE_KW = {
    T0: "范围 mvp 边界 签收 发布 同行定位", T1: "幻方 highflyer deepseek 梁文锋 算力",
    T2: "灵均 lingjun 处罚 异常交易 合规", T16: "大厂 锚点 失败案例", T17: "破产 10案 捡漏",
    T18: "墓志铭 开发者 不做", T19: "合规 信源 地图 红线", T20: "观察表 律师 财税",
  };
  for (const [id, rel] of Object.entries(CASE_MAP)) {
    const sc = fuzzyScore(id + " " + rel + " " + (CASE_KW[id] || ""), q);
    if (sc) hits.push({ type: "case", name: id + " " + rel.split("/").pop(), cmd: "/case " + id, score: sc + 10, path: rel });
  }
  try {
    for (const f of readdirSync(join(ROOT, "ops/bus/tasks"))) {
      const sc = fuzzyScore(f, q);
      if (sc) hits.push({ type: "card", name: f, cmd: "/card " + f.replace(/\.md$/, ""), score: sc, path: "ops/bus/tasks/" + f });
    }
  } catch {}
  hits.sort((a, b) => b.score - a.score);
  return { ok: true, cmd: "find", query: q, count: hits.length, hits: hits.slice(0, 30) };
}

function cmdSkillCatalog() {
  const list = allSkills().sort((a, b) => a.alias.localeCompare(b.alias, "zh"));
  const lines = ["# 技能目录（一句话用途）", "", "- 生成时间：" + new Date().toISOString(), "- 技能数：" + list.length, "- 改名规则：显示友好名，原名保留供 OpenCode 调用；不重命名目录，避免破坏引用。", "", "| 友好名（选项显示） | 原名（调用用） | 分类 | 一句话用途 | 路径 |", "|---|---|---|---|---|"];
  for (const s of list) lines.push("| " + s.alias + " | `" + s.name + "` | " + s.category + " | " + s.purpose.replace(/\|/g, "｜") + " | `" + s.path.replace(/^.*[\\/]AI_Factory[\\/]/, "") + "` |");
  lines.push("", "> 与飞书「技能」表同源（skill_catalog.py）；五列分别是 友好名 / 原名 / 分类 / 一句话用途 / 路径。");
  return { ok: true, cmd: "skill_catalog", count: list.length, markdown: lines.join("\n") };
}

async function dispatch(input) {
  const cmd = String(input.cmd || "").replace(/^\//, "").trim().toLowerCase();
  const arg = String(input.arg || "").trim();
  const map = {
    status: () => cmdStatus(), audit: () => cmdAudit(), handoff: () => cmdHandoff(),
    ds: () => cmdDs(), note: () => cmdNote(arg), probe: () => cmdProbe(arg),
    capture: () => cmdCapture(input),
    mvp: () => cmdMvp(), cases: () => cmdCases(), case: () => cmdCase(arg),
    compliance: () => cmdDoc("reports/compliance/T19_source_compliance_map.md", "compliance"),
    inventory: () => cmdDoc("reports/inventory/ACTIVE_INVENTORY.md", "inventory"),
    selftest: () => cmdSelftest(),
    skills: () => cmdSkills(arg), skill: () => cmdSkill(arg), card: () => cmdCard(arg), find: () => cmdFind(arg),
    skill_catalog: () => cmdSkillCatalog(),
    open_capture: () => {
      const dir = join(ROOT, "reports", "ds_capture");
      spawnSync("explorer.exe", [dir], { windowsHide: true });
      return { ok: true, cmd: "open_capture", path: dir };
    },
    help: () => ({ ok: true, cmd: "help", commands: ["/status", "/audit", "/handoff", "/ds", "/probe <url>", "/capture", "/note <文本>", "/goto <url>", "/click <文字>", "/fill <标签> <值>", "/open_capture", "/mvp", "/cases", "/case T1", "/compliance", "/inventory", "/selftest", "/skills [关键词]", "/skill <名称>", "/card T14", "/find <关键词>"] }),
  };
  if (!map[cmd]) return { ok: false, error: "未知命令：" + cmd + "；用 /help 查看" };
  return await map[cmd]();
}

const server = http.createServer((req, res) => {
  const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Private-Network": "true",
    "Vary": "Origin",
    "Content-Type": "application/json; charset=utf-8",
  };
  if (req.method === "OPTIONS") { res.writeHead(204, headers); return res.end(); }

  if (req.method === "GET" && req.url === "/health") {
    const n = existsSync(OUT) ? readdirSync(OUT).filter((f) => f.endsWith(".json")).length : 0;
    res.writeHead(200, headers); return res.end(JSON.stringify({ ok: true, captures: n }));
  }
  if (req.method === "GET" && req.url === "/latest") {
    const p = join(OUT, "latest.json");
    res.writeHead(existsSync(p) ? 200 : 404, headers);
    return res.end(existsSync(p) ? readFileSync(p, "utf8") : JSON.stringify({ ok: false }));
  }
  if (req.method === "POST" && req.url === "/command") {
    let body = "";
    req.on("data", (chunk) => { body += chunk; if (body.length > 4 * 1024 * 1024) req.destroy(); });
    req.on("end", async () => {
      try {
        const input = JSON.parse(body);
        const result = await dispatch(input);
        log({ event: "command", cmd: input.cmd, ok: result.ok });
        res.writeHead(result.ok ? 200 : 400, headers);
        res.end(JSON.stringify(result));
      } catch (e) {
        log({ event: "command-error", error: String(e && e.message || e) });
        res.writeHead(400, headers); res.end(JSON.stringify({ ok: false, error: String(e && e.message || e) }));
      }
    });
    return;
  }
  if (req.method === "POST" && req.url === "/ingest") {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > 4 * 1024 * 1024) { req.destroy(); }
    });
    req.on("end", () => {
      try {
        const input = JSON.parse(body);
        const raw = JSON.stringify(input.payload ?? input, null, 1);
        const turns = normalize(input.payload ?? input);
        const ts = new Date().toISOString().replace(/[:.]/g, "-");
        mkdirSync(OUT, { recursive: true });
        const rawPath = join(OUT, "capture_" + ts + ".json");
        const cardPath = join(OUT, "card_" + ts + ".md");
        const metaSha = sha(raw);
        writeFileSync(rawPath, raw, "utf8");
        writeFileSync(cardPath, card(turns, { ...input, sha: metaSha }), "utf8");
        writeFileSync(join(OUT, "latest.json"), JSON.stringify({
          ok: true, raw: rawPath, card: cardPath, turns: turns.length,
          sha256: metaSha, card_sha256: sha(readFileSync(cardPath, "utf8")), ts: new Date().toISOString(),
        }, null, 1), "utf8");
        log({ event: "ingest", source: input.source, url: input.url, turns: turns.length, bytes: body.length });
        res.writeHead(200, headers);
        res.end(JSON.stringify({ ok: true, raw: rawPath, card: cardPath, turns: turns.length, sha256: metaSha }));
      } catch (e) {
        log({ event: "error", error: String(e && e.message || e) });
        res.writeHead(400, headers);
        res.end(JSON.stringify({ ok: false, error: String(e && e.message || e) }));
      }
    });
    return;
  }
  res.writeHead(404, headers); res.end(JSON.stringify({ ok: false }));
});

server.listen(PORT, "127.0.0.1", () => {
  log({ event: "start", port: PORT, root: ROOT });
  console.log("DS bridge on http://127.0.0.1:" + PORT + " -> " + OUT);
});
