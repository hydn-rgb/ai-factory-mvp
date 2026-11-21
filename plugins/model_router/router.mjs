// Pure routing logic: no OpenCode, no I/O, no dependencies.
// Keeping this file pure makes the policy unit-testable and auditable.

import { readFileSync } from "node:fs";

export function loadPolicy(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function normalize(text) {
  return String(text || "").toLowerCase();
}

function matchedKeywords(text, keywords) {
  const haystack = normalize(text);
  return (keywords || []).filter((k) => k && haystack.includes(String(k).toLowerCase()));
}

/**
 * Explainable four-way classifier.
 * Score = number of distinct keywords hit. Ties follow policy.classify.order.
 */
export function classifyTask(text, policy) {
  const cfg = policy.classify || {};
  const order = cfg.order || ["audit", "research", "doc", "code"];
  const scores = {};
  const matches = {};
  for (const [type, keywords] of Object.entries(cfg.keywords || {})) {
    matches[type] = matchedKeywords(text, keywords);
    scores[type] = matches[type].length;
  }
  let best = cfg.default || "code";
  let bestScore = 0;
  for (const type of order) {
    const score = scores[type] || 0;
    if (score > bestScore) {
      best = type;
      bestScore = score;
    }
  }
  return { task_type: best, score: bestScore, matched: matches[best] || [], scores };
}

function refOf(spec) {
  if (!spec) return null;
  return { providerID: spec.providerID, id: spec.modelID || spec.id };
}

export function modelKey(ref) {
  if (!ref) return "";
  const providerID = ref.providerID || "";
  const id = ref.id || ref.modelID || "";
  return providerID && id ? `${providerID}/${id}` : "";
}

/**
 * Decide the model for one prompt.
 * Priority: privacy/local > task type policy > heavy upgrade > default.
 */
export function decide(text, policy) {
  const classification = classifyTask(text, policy);
  const privacy = matchedKeywords(text, (policy.privacy || {}).keywords);
  const heavyCfg = policy.heavy || {};
  const heavy = matchedKeywords(text, heavyCfg.keywords);
  const long = normalize(text).length >= (heavyCfg.chars_threshold || Infinity);

  if (privacy.length) {
    const model = refOf(policy.local_model || policy.default_model);
    return {
      task_type: classification.task_type,
      model,
      model_key: modelKey(model),
      reason: `privacy/local; matched=${privacy.join(",")}`,
      matched: classification.matched,
      privacy: true,
      heavy: false,
    };
  }

  const typeCfg = (policy.task_types || {})[classification.task_type] || {};
  const upgrade = (heavy.length > 0 || long) && typeCfg.heavy_model;
  const model = refOf(upgrade ? typeCfg.heavy_model : typeCfg.model || policy.default_model);
  const why = [];
  if (classification.matched.length) why.push(`matched=${classification.matched.join(",")}`);
  if (upgrade) why.push(`heavy=${heavy.length ? heavy.join(",") : `chars>=${heavyCfg.chars_threshold}`}`);
  if (!why.length) why.push("no keyword; default task type");
  return {
    task_type: classification.task_type,
    model,
    model_key: modelKey(model),
    reason: `task_type=${classification.task_type}; ${why.join("; ")}`,
    matched: classification.matched,
    privacy: false,
    heavy: Boolean(upgrade),
  };
}
