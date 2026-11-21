// Model router plugin (OpenCode V2 local plugin).
// Policy: classify each new user prompt into code/research/doc/audit, then
// switch the session model only when the user has not chosen one explicitly.
// Every failure is swallowed and falls back to the default model so chat is
// never blocked.

import { appendFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { decide, loadPolicy, modelKey } from "./router.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const LOG_PATH = process.env.MODEL_ROUTER_LOG || join(HERE, "test_log.jsonl");
const PLUGIN_ID = "model_router";

function writeLog(row) {
  try {
    mkdirSync(dirname(LOG_PATH), { recursive: true });
    appendFileSync(LOG_PATH, JSON.stringify(row) + "\n", "utf8");
  } catch {
    // Logging must never break a conversation.
  }
}

function infoModel(info) {
  const node = info && info.data ? info.data : info;
  const model = node && node.model ? node.model : node;
  if (!model || !model.providerID) return null;
  const id = model.id || model.modelID;
  return id ? { providerID: model.providerID, id } : null;
}

function defaultModel(ctx) {
  return Promise.resolve()
    .then(() => ctx.model.default())
    .then((value) => {
      const node = value && value.data ? value.data : value;
      if (!node || !node.providerID) return null;
      const id = node.id || node.modelID;
      return id ? { providerID: node.providerID, id } : null;
    })
    .catch(() => null);
}

function modelFor(typeCfg, key) {
  const spec = (typeCfg && typeCfg[key]) || {};
  const id = spec.modelID || spec.id;
  return spec.providerID && id ? { providerID: spec.providerID, id } : null;
}

export default {
  id: PLUGIN_ID,

  async setup(ctx) {
    let policy;
    try {
      policy = loadPolicy(join(HERE, "policy.json"));
    } catch (error) {
      writeLog({ ts: new Date().toISOString(), plugin: PLUGIN_ID, event: "error", reason: `policy load failed: ${error && error.message}` });
      return;
    }

    const fallback = modelFor(policy, "default_model");
    const lastApplied = new Map();
    const manual = new Set();

    async function applyDefault(sessionID, reason, extra = {}) {
      if (!fallback) return false;
      try {
        await ctx.session.switchModel({ sessionID, model: fallback });
        lastApplied.set(sessionID, fallback);
        writeLog({
          ts: new Date().toISOString(),
          plugin: PLUGIN_ID,
          event: "fallback",
          session: sessionID,
          task_type: extra.task_type || null,
          model: modelKey(fallback),
          reason,
        });
        return true;
      } catch (error) {
        writeLog({
          ts: new Date().toISOString(),
          plugin: PLUGIN_ID,
          event: "error",
          session: sessionID,
          task_type: extra.task_type || null,
          model: modelKey(fallback),
          reason: `${reason}; fallback failed: ${error && error.message}`,
        });
        return false;
      }
    }

    try {
      await ctx.session.hook("prompt", async (event) => {
        const sessionID = event && event.sessionID;
        if (!sessionID) return;

        try {
          const text = (event.prompt && event.prompt.text) || "";
          const info = await ctx.session.get({ sessionID }).catch(() => null);
          const current = infoModel(info);
          const applied = lastApplied.get(sessionID);

          // Manual override wins, permanently for this session.
          if (manual.has(sessionID)) {
            writeLog({ ts: new Date().toISOString(), plugin: PLUGIN_ID, event: "manual_skip", session: sessionID, task_type: null, model: modelKey(current), reason: "session marked manual" });
            return;
          }
          if (applied && modelKey(current) !== modelKey(applied)) {
            manual.add(sessionID);
            writeLog({ ts: new Date().toISOString(), plugin: PLUGIN_ID, event: "manual_skip", session: sessionID, task_type: null, model: modelKey(current), reason: "session model changed outside plugin (manual /model)" });
            return;
          }
          if (!applied && current) {
            const globalDefault = await defaultModel(ctx);
            if (globalDefault && modelKey(current) !== modelKey(globalDefault)) {
              manual.add(sessionID);
              writeLog({ ts: new Date().toISOString(), plugin: PLUGIN_ID, event: "manual_skip", session: sessionID, task_type: null, model: modelKey(current), reason: "explicit model differs from global default" });
              return;
            }
          }

          const choice = decide(text, policy);
          const target = choice.model;
          if (!target) {
            await applyDefault(sessionID, "policy target missing", { task_type: choice.task_type });
            return;
          }

          if (modelKey(current) === modelKey(target)) {
            lastApplied.set(sessionID, target);
            writeLog({
              ts: new Date().toISOString(),
              plugin: PLUGIN_ID,
              event: "noop",
              session: sessionID,
              task_type: choice.task_type,
              model: choice.model_key,
              reason: choice.reason,
            });
            return;
          }

          lastApplied.set(sessionID, target);
          try {
            await ctx.session.switchModel({ sessionID, model: target });
            writeLog({
              ts: new Date().toISOString(),
              plugin: PLUGIN_ID,
              event: "switch",
              session: sessionID,
              task_type: choice.task_type,
              model: choice.model_key,
              reason: choice.reason,
            });
          } catch (error) {
            lastApplied.delete(sessionID);
            await applyDefault(sessionID, `switch failed: ${error && error.message}`, { task_type: choice.task_type });
          }
        } catch (error) {
          writeLog({ ts: new Date().toISOString(), plugin: PLUGIN_ID, event: "error", session: sessionID, task_type: null, model: "", reason: `hook failed: ${error && error.message}` });
          // Best effort: never rethrow, so the conversation is not blocked.
          await applyDefault(sessionID, "unexpected hook failure");
        }
      });
    } catch (error) {
      writeLog({ ts: new Date().toISOString(), plugin: PLUGIN_ID, event: "error", reason: `hook registration failed: ${error && error.message}` });
    }
  },
};
