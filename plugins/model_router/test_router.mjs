// Dependency-free machine test for the model router.
// Covers the four acceptance items that can run without a live server:
//   1. new session -> log row with task_type + model
//   2. manual model choice -> not overridden
//   3. plugin/switch error -> fallback default, hook resolves
//   4. policy/classifier behavior for privacy + heavy upgrade
// Rollback item 4 in the task card is covered by test_rollback_config.ps1.

import assert from "node:assert/strict";
import { existsSync, readFileSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const LOG = join(HERE, "test_log.jsonl");
if (existsSync(LOG)) rmSync(LOG);
process.env.MODEL_ROUTER_LOG = LOG;

const { decide, modelKey } = await import("./router.mjs");
const plugin = (await import("./index.js")).default;

const DEFAULT = { providerID: "deepseek", id: "deepseek-flash" };
const PRO = { providerID: "deepseek", id: "deepseek-v4-pro" };
const LOCAL = { providerID: "ollama", id: "qwen2.5:3b-instruct-q4_K_M" };
const MANUAL = { providerID: "xiaomi", id: "mimo-v2.6-pro" };

function makeCtx({ model, failFor = () => false, getThrows = false } = {}) {
  const state = { model: model ? { ...model } : undefined };
  const switches = [];
  const hooks = {};
  const ctx = {
    session: {
      get: async () => {
        if (getThrows) throw new Error("session.get exploded");
        return { model: state.model };
      },
      switchModel: async ({ model: target }) => {
        if (failFor(target)) throw new Error(`model unavailable: ${modelKey(target)}`);
        state.model = { ...target };
        switches.push({ ...target });
      },
      hook: async (name, fn) => {
        hooks[name] = fn;
      },
    },
    model: {
      default: async () => ({ ...DEFAULT }),
    },
  };
  ctx.hooks = hooks;
  return { ctx, state, switches, hooks };
}

async function runPrompt(ctx, sessionID, text) {
  // setup registers exactly one prompt hook in the fake context.
  assert.ok(ctx.hooks.prompt, "prompt hook should be registered");
  await ctx.hooks.prompt({ sessionID, prompt: { text } });
}

const results = [];
function pass(name, detail) {
  results.push({ name, status: "PASS", detail });
}

// --- pure policy checks ---------------------------------------------------
{
  const code = decide("修复这个 bug，重写函数并补测试", JSON.parse(readFileSync(join(HERE, "policy.json"), "utf8")));
  assert.equal(code.task_type, "code");
  assert.equal(code.model_key, "deepseek/deepseek-flash");
  pass("classify-code", code.reason);
}
{
  const privatePrompt = "这份机密资料不要联网，离线处理";
  const r = decide(privatePrompt, JSON.parse(readFileSync(join(HERE, "policy.json"), "utf8")));
  assert.equal(r.task_type, "code");
  assert.equal(r.model_key, "ollama/qwen2.5:3b-instruct-q4_K_M");
  assert.equal(r.privacy, true);
  pass("privacy-local", r.reason);
}
{
  const heavy = "请做架构级重构，多文件迁移并解决并发根因。" + "x".repeat(1500);
  const r = decide(heavy, JSON.parse(readFileSync(join(HERE, "policy.json"), "utf8")));
  assert.equal(r.model_key, "deepseek/deepseek-v4-pro");
  assert.equal(r.heavy, true);
  pass("heavy-upgrade", r.reason);
}

// --- plugin checks --------------------------------------------------------
// 1. new session -> task_type + model logged
{
  const { ctx, state } = makeCtx();
  await plugin.setup(ctx);
  await runPrompt(ctx, "test-1-new-session", "请写一个 README 文档，说明安装步骤");
  const target = decide("请写一个 README 文档，说明安装步骤", JSON.parse(readFileSync(join(HERE, "policy.json"), "utf8")));
  assert.equal(target.task_type, "doc");
  assert.equal(target.model_key, "deepseek/deepseek-flash");
  assert.equal(modelKey(state.model), "deepseek/deepseek-flash");
  pass("new-session-logs-task-type-model", "see test_log.jsonl session=test-1-new-session");
}

// 2a. explicit model before first prompt -> no override
{
  const { ctx, state, switches } = makeCtx({ model: PRO });
  await plugin.setup(ctx);
  await runPrompt(ctx, "test-2a-manual-first", "请写一个 README 文档");
  assert.equal(modelKey(state.model), "deepseek/deepseek-v4-pro");
  assert.equal(switches.length, 0);
  pass("manual-first-prompt-not-overridden", "model stayed deepseek/deepseek-v4-pro");
}

// 2b. manual /model after a plugin switch -> no override
{
  const { ctx, state, switches } = makeCtx();
  await plugin.setup(ctx);
  await runPrompt(ctx, "test-2b-manual-after", "请写一个 README 文档");
  assert.equal(modelKey(state.model), "deepseek/deepseek-flash");
  state.model = { ...MANUAL };
  await runPrompt(ctx, "test-2b-manual-after", "审计这段代码的安全性");
  assert.equal(modelKey(state.model), "xiaomi/mimo-v2.6-pro");
  assert.equal(switches.length, 1, "only the first prompt should switch");
  pass("manual-after-switch-not-overridden", "manual xiaomi/mimo-v2.6-pro preserved");
}

// 3. switch failure -> fallback default, no throw
{
  const { ctx, state } = makeCtx({ failFor: (m) => modelKey(m) === "deepseek/deepseek-v4-pro" });
  await plugin.setup(ctx);
  await runPrompt(ctx, "test-3-fallback", "审计这段代码的安全性");
  assert.equal(modelKey(state.model), "deepseek/deepseek-flash");
  pass("switch-error-falls-back-default", "pro unavailable -> deepseek/deepseek-flash");
}

// 3b. session.get failure -> still runs, never rejects
{
  const { ctx } = makeCtx({ getThrows: true, failFor: (m) => modelKey(m) === "deepseek/deepseek-v4-pro" });
  await plugin.setup(ctx);
  await runPrompt(ctx, "test-3b-hook-error", "审计这段代码");
  pass("hook-error-does-not-block", "handler resolved despite session.get failure");
}

// 4. privacy route
{
  const { ctx, state } = makeCtx();
  await plugin.setup(ctx);
  await runPrompt(ctx, "test-4-privacy", "这份机密资料不要联网，离线处理");
  assert.equal(modelKey(state.model), "ollama/qwen2.5:3b-instruct-q4_K_M");
  pass("privacy-routes-local", "ollama/qwen2.5:3b-instruct-q4_K_M");
}

// 5. heavy upgrade
{
  const { ctx, state } = makeCtx();
  await plugin.setup(ctx);
  await runPrompt(ctx, "test-5-heavy", "请做架构级重构，多文件迁移并解决并发根因。" + "x".repeat(1500));
  assert.equal(modelKey(state.model), "deepseek/deepseek-v4-pro");
  pass("heavy-routes-pro", "deepseek/deepseek-v4-pro");
}

// log integrity
{
  const rows = readFileSync(LOG, "utf8").trim().split(/\r?\n/).filter(Boolean).map((l) => JSON.parse(l));
  const newRow = rows.find((r) => r.session === "test-1-new-session");
  assert.ok(newRow, "new session row missing");
  assert.equal(newRow.task_type, "doc");
  assert.equal(newRow.model, "deepseek/deepseek-flash");
  const manualRow = rows.find((r) => r.session === "test-2a-manual-first");
  assert.ok(manualRow, "manual row missing");
  assert.equal(manualRow.event, "manual_skip");
  const fallbackRow = rows.find((r) => r.session === "test-3-fallback" && r.event === "fallback");
  assert.ok(fallbackRow, "fallback row missing");
  console.log(`rows=${rows.length}`);
  pass("test-log-schema", `rows=${rows.length}`);
}

for (const r of results) console.log(`${r.status} ${r.name} :: ${r.detail}`);
console.log("ALL PASS");
