# -*- coding: utf-8 -*-
"""T8 · 每轮迭代指标（交付率 / 命中率 / 成本）+ 下一轮动作。

设计原则（对应任务卡 T8 的禁止项）：
- 不美化：分母为 0 时返回 null，不拿 0 或 100% 充数；未入账成本标 lower_bound。
- 不删失败：回执里 status=FAIL/UNVERIFIED 的行原样保留在明细里。
- 不把"跑了"当"成了"：只有 sha 与产物一致且 status=PASS 的回执才算交付。
- Hermes 降级：只产出提醒（reminder），不自动"进化"、不自动发卡/改制度。

用法：
  python ops\\metrics.py --round r20261121
  python ops\\metrics.py --round r20261121 --tasks T3,T4
  python ops\\metrics.py --round r20261121 --since 2026-11-21T00:00:00
  python ops\\metrics.py --history
  python ops\\metrics.py --pred-add --id P1 --statement "..." --due 2026-12-01 --prob 0.6
  python ops\\metrics.py --pred-settle --id P1 --result hit
  python ops\\metrics.py --hermes-remind --round r20261121
  python ops\\metrics.py --self-test
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

DEFAULT_ROOT = os.environ.get("AI_FACTORY_ROOT", r"D:\AI_Factory")
TEMPLATE = Path(__file__).with_name("templates") / "weekly_report.md"


# ---------------------------------------------------------------- 基础工具
def sha16(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def sha_full(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_ts(value):
    if not value:
        return None
    text = str(value).strip().replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def in_window(ts, since, until) -> bool:
    if ts is None:
        # 无时间戳的回执不猜时间：只有显式点名 --tasks 时才由调用方纳入
        return since is None and until is None
    if since and ts < since:
        return False
    if until and ts > until:
        return False
    return True


def ratio(num, den):
    if den in (None, 0):
        return None
    return round(float(num) / float(den), 4)


# ---------------------------------------------------------------- 数据读取
def read_cards(root: Path):
    cards = {}
    tasks_dir = root / "ops" / "bus" / "tasks"
    for p in sorted(tasks_dir.glob("T*.md")):
        tid = p.stem
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            text = ""
        cards[tid] = {"task_id": tid, "path": str(p), "lines": len(text.splitlines())}
    return cards


def read_receipts(root: Path, cards):
    rows = []
    out_dir = root / "ops" / "bus" / "out"
    for p in sorted(out_dir.glob("T*.json")):
        d = load_json(p, None)
        if not isinstance(d, dict):
            rows.append({
                "task_id": p.stem, "path": str(p), "status": "UNVERIFIED",
                "accepted": False, "reason": "JSON 解析失败或结构非法", "sha": None, "ts": None,
            })
            continue
        art = Path(str(d.get("artifact") or ""))
        reason = ""
        accepted = False
        if d.get("status") != "PASS":
            reason = "status=%s" % d.get("status")
        elif not art.exists():
            reason = "产物不存在"
        elif not d.get("sha"):
            reason = "缺 sha"
        elif sha16(art) != str(d.get("sha"))[:16]:
            reason = "sha 与产物不符"
        else:
            accepted = True
            reason = "PASS + sha 一致"
        rows.append({
            "task_id": d.get("task_id") or p.stem,
            "owner": d.get("owner"),
            "path": str(p),
            "status": d.get("status"),
            "accepted": accepted,
            "reason": reason,
            "sha": d.get("sha"),
            "ts": d.get("ts"),
            "spent_cny": (d.get("budget") or {}).get("spent_cny"),
            "level": d.get("level"),
            "in_cards": (d.get("task_id") or p.stem) in cards,
        })
    return rows


def read_predictions(root: Path):
    path = root / "ops" / "metrics_ledger" / "predictions.jsonl"
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def read_cost_rows(root: Path):
    path = root / "data" / "cost_ledger.jsonl"
    rows = []
    if not path.exists():
        return rows, path
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows, path


# ---------------------------------------------------------------- 指标计算
def compute(root: Path, round_name, since=None, until=None, task_ids=None, usd_cny=7.2):
    cards = read_cards(root)
    receipts = read_receipts(root, cards)
    if task_ids:
        task_ids = set(task_ids)
        cards_f = {k: v for k, v in cards.items() if k in task_ids}
        receipts_f = [r for r in receipts if r["task_id"] in task_ids]
    else:
        cards_f = cards
        receipts_f = [r for r in receipts
                      if r.get("ts") and in_window(parse_ts(r.get("ts")), since, until)]
        # 显式窗口内的回执；无 ts 的不进分母，避免"跑了当成了"

    accepted = [r for r in receipts_f if r["accepted"]]
    failed = [r for r in receipts_f if not r["accepted"]]

    # 交付率
    delivery_rate = ratio(len(accepted), len(cards_f))

    # 命中率（只算已到期且已结算：hit / miss；open 与 void 不进分母）
    preds = read_predictions(root)
    if task_ids:
        preds = [p for p in preds if p.get("task_id") in task_ids]
    due_preds, hits, misses, open_preds = [], 0, 0, []
    for p in preds:
        due = parse_ts(p.get("due"))
        status = p.get("status")
        if status in ("hit", "miss"):
            due_preds.append(p)
            hits += 1 if status == "hit" else 0
            misses += 1 if status == "miss" else 0
        elif status == "open" and due is not None:
            if until is None or due <= until:
                open_preds.append(p)
    # 已结算预测未记录结算时间：全部计入，不隐藏也不补造
    hit_rate = ratio(hits, len(due_preds))

    # 成本：优先回执 budget.spent_cny，缺失则用 cost_ledger 的 ok 行
    cost_rows, cost_path = read_cost_rows(root)
    receipt_spent = [float(r["spent_cny"]) for r in receipts_f
                     if isinstance(r.get("spent_cny"), (int, float))]
    missing_cost = [r["task_id"] for r in receipts_f if not isinstance(r.get("spent_cny"), (int, float))]
    ledger_spent_usd = 0.0
    ledger_rows_used = 0
    for row in cost_rows:
        ts = parse_ts(row.get("ts"))
        if ts is None:
            continue
        if since and ts < since:
            continue
        if until and ts > until:
            continue
        if row.get("ok") is False:
            continue
        try:
            ledger_spent_usd += float(row.get("cost_usd") or 0.0)
            ledger_rows_used += 1
        except (TypeError, ValueError):
            continue
    spent_cny = round(sum(receipt_spent) + ledger_spent_usd * usd_cny, 4)
    cost_source = "receipt.budget.spent_cny + data/cost_ledger.jsonl"
    effective = len(accepted)
    cost_per_product = ratio(spent_cny, effective)

    detail = {
        "cards_total": len(cards_f),
        "receipts_total": len(receipts_f),
        "receipts_accepted": effective,
        "receipts_failed": len(failed),
        "receipts_missing_cost": len(missing_cost),
        "ledger_rows_used": ledger_rows_used,
        "predictions_due": len(due_preds),
        "predictions_hit": hits,
        "predictions_miss": misses,
        "predictions_open": len(open_preds),
        "failed": failed,
        "accepted": [{"task_id": r["task_id"], "sha": r["sha"], "path": r["path"]} for r in accepted],
        "open_predictions": open_preds,
    }
    metrics = {
        "delivery_rate": {
            "value": delivery_rate,
            "num": effective,
            "den": len(cards_f),
            "formula": "通过验收回执 / 发卡数",
            "note": None if delivery_rate is not None else "无卡或未发卡：分母为 0，不计算",
        },
        "hit_rate": {
            "value": hit_rate,
            "num": hits,
            "den": len(due_preds),
            "formula": "预测命中 / 到期预测",
            "note": None if hit_rate is not None else "无已结算到期预测：分母为 0，不计算",
        },
        "cost_per_product_cny": {
            "value": cost_per_product,
            "spent_cny": spent_cny,
            "effective_products": effective,
            "formula": "本轮花费 / 有效产物数",
            "is_lower_bound": bool(missing_cost or not cost_rows),
            "note": ("%d 条回执未记账，成本为下限；不含订阅/包月" % len(missing_cost))
            if missing_cost else "仅统计已入账付费调用；不含订阅/包月",
        },
    }
    return {
        "round": round_name,
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "root": str(root),
        "window": {
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
            "tasks": sorted(task_ids) if task_ids else None,
        },
        "metrics": metrics,
        "detail": detail,
        "sources": {
            "cards": str(root / "ops" / "bus" / "tasks"),
            "receipts": str(root / "ops" / "bus" / "out"),
            "predictions": str(root / "ops" / "metrics_ledger" / "predictions.jsonl"),
            "cost": str(cost_path),
        },
        "cost_source": cost_source,
    }


def previous_snapshot(root: Path, round_name):
    d = root / "ops" / "metrics_ledger" / "rounds"
    if not d.exists():
        return None
    snaps = []
    for p in d.glob("*.json"):
        if p.stem == round_name:
            continue
        data = load_json(p, None)
        if isinstance(data, dict) and data.get("ts"):
            data["_path"] = str(p)
            snaps.append(data)
    if not snaps:
        return None
    snaps.sort(key=lambda x: x.get("ts") or "")
    return snaps[-1]


# 指标下降 -> 1 条可执行动作（每个下降指标各 1 条，按优先级取第一条作为 next_action）
ACTIONS = {
    "delivery_rate": "把回执 status=FAIL/UNVERIFIED 的卡按任务卡'回执'字段补齐 artifact+sha+证据后重提；本轮新卡上限 3 张，未通过验收的不开新卡。",
    "hit_rate": "本轮冻结新预测；对上轮每个 miss 在 predictions.jsonl 写 1 行失效原因，并把下轮到期预测补到 ≥3 条（带概率与截止）。",
    "cost_per_product_cny": "关闭本轮付费调用，优先复用已有产物；单卡预算降到 ¥5，且回执必须填 budget.spent_cny（缺省即拒收）。",
}
METRIC_KEYS = ("delivery_rate", "hit_rate", "cost_per_product_cny")
# 成本是越低越好，其余越高越好
LOWER_IS_BETTER = {"cost_per_product_cny"}


def evaluate_against(prev, cur):
    out = {"baseline": prev is None, "deltas": {}, "actions": []}
    if prev is None:
        return out
    for key in METRIC_KEYS:
        a = (prev.get("metrics") or {}).get(key, {}).get("value")
        b = (cur.get("metrics") or {}).get(key, {}).get("value")
        out["deltas"][key] = {"prev": a, "cur": b,
                              "delta": (round(b - a, 4) if isinstance(a, (int, float))
                                        and isinstance(b, (int, float)) else None)}
        if a is None or b is None:
            out["actions"].append("%s 上轮或本轮无有效分母（null≠0），先补数据源再比较。" % key)
            continue
        declined = (b > a) if key in LOWER_IS_BETTER else (b < a)
        if declined:
            out["actions"].append(ACTIONS[key])
    # 去重但保持顺序，最多给 3 条，next_action 取第一条
    seen, uniq = set(), []
    for a in out["actions"]:
        if a not in seen:
            seen.add(a)
            uniq.append(a)
    out["actions"] = uniq
    return out


# ---------------------------------------------------------------- 输出渲染
def render_report(snapshot, evaluation, template_text):
    m = snapshot["metrics"]
    d = snapshot["detail"]

    def fmt(metric, suffix=""):
        v = metric.get("value")
        return "null（%s）" % metric.get("note") if v is None else ("%s%s" % (v, suffix))

    deltas = evaluation.get("deltas") or {}
    rows = []
    for key in METRIC_KEYS:
        delta = (deltas.get(key) or {}).get("delta")
        if "den" in m[key]:
            frac = "%s/%s" % (m[key]["num"], m[key]["den"])
        else:
            frac = "%s / %s 产物" % (m[key].get("spent_cny"), m[key].get("effective_products"))
        rows.append("| %s | %s | %s | %s |" % (
            key, fmt(m[key]), "—" if delta is None else delta, frac))
    action = evaluation["actions"][0] if evaluation["actions"] else "指标未下降：保持节奏，本轮把单产物成本压到 ≤¥5。"
    failed_lines = "\n".join(
        "- %s: %s（%s）" % (f["task_id"], f["reason"], f["status"]) for f in d["failed"]
    ) or "- 无"
    open_lines = "\n".join(
        "- %s: %s（due %s）" % (p.get("id"), p.get("statement"), p.get("due"))
        for p in d["open_predictions"]
    ) or "- 无"
    token = {
        "{{ROUND}}": str(snapshot["round"]),
        "{{TS}}": snapshot["ts"],
        "{{DELIVERY}}": fmt(m["delivery_rate"]),
        "{{HIT}}": fmt(m["hit_rate"]),
        "{{COST}}": fmt(m["cost_per_product_cny"], " CNY/产物"),
        "{{CARDS}}": str(d["cards_total"]),
        "{{ACCEPTED}}": str(d["receipts_accepted"]),
        "{{FAILED}}": str(d["receipts_failed"]),
        "{{FAILED_LINES}}": failed_lines,
        "{{OPEN_LINES}}": open_lines,
        "{{NEXT_ACTION}}": action,
        "{{COST_NOTE}}": m["cost_per_product_cny"].get("note") or "",
        "{{METRIC_TABLE}}": "\n".join(rows),
        "{{BASELINE}}": "基线轮（无上轮快照，不判定升降）" if evaluation["baseline"] else "有上轮快照",
        "{{ACTIONS}}": "\n".join("- " + a for a in evaluation["actions"]) or "- 无（未下降）",
    }
    text = template_text
    for k, v in token.items():
        text = text.replace(k, v)
    return text


def hermes_reminder(snapshot, evaluation):
    """Hermes 只提醒，不进化。返回结构化提醒，供人或调度器读取。"""
    declined = [k for k in METRIC_KEYS
                if (evaluation.get("deltas") or {}).get(k, {}).get("delta") is not None
                and (((evaluation["deltas"][k]["cur"] or 0) > (evaluation["deltas"][k]["prev"] or 0))
                     if k in LOWER_IS_BETTER else
                     ((evaluation["deltas"][k]["cur"] or 0) < (evaluation["deltas"][k]["prev"] or 0)))]
    return {
        "kind": "reminder",
        "mode": "degraded_reminder_only",
        "round": snapshot["round"],
        "declined_metrics": declined,
        "message": evaluation["actions"][0] if evaluation["actions"] else "本轮指标未下降，无提醒。",
        "forbidden": ["自动改制度", "自动生成任务卡", "自动调模型/预算", "自称进化完成"],
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ---------------------------------------------------------------- 自检
def self_test():
    ok = []

    def check(name, cond):
        ok.append((name, bool(cond)))

    tmp = Path(tempfile.mkdtemp(prefix="t8_metrics_"))
    try:
        (tmp / "ops" / "bus" / "tasks").mkdir(parents=True)
        (tmp / "ops" / "bus" / "out").mkdir(parents=True)
        (tmp / "data").mkdir(parents=True)
        (tmp / "ops" / "metrics_ledger").mkdir(parents=True)
        for tid in ("T10", "T11", "T12"):
            (tmp / "ops" / "bus" / "tasks" / (tid + ".md")).write_text("# %s\n" % tid, encoding="utf-8")
        (tmp / "art_ok.txt").write_text("ok", encoding="utf-8")
        good = sha_full(tmp / "art_ok.txt")
        write_json(tmp / "ops" / "bus" / "out" / "T10.json", {
            "task_id": "T10", "owner": "W10", "status": "PASS",
            "artifact": str(tmp / "art_ok.txt"), "sha": good,
            "ts": "2026-11-21T10:00:00", "budget": {"spent_cny": 3.0},
        })
        write_json(tmp / "ops" / "bus" / "out" / "T11.json", {
            "task_id": "T11", "owner": "W11", "status": "PASS",
            "artifact": str(tmp / "art_ok.txt"), "sha": "deadbeefdeadbeef",
            "ts": "2026-11-21T10:10:00",
        })
        (tmp / "ops" / "metrics_ledger" / "predictions.jsonl").write_text(
            json.dumps({"id": "P1", "task_id": "T10", "statement": "s1", "due": "2026-11-21",
                        "status": "hit", "prob": 0.6}) + "\n" +
            json.dumps({"id": "P2", "task_id": "T11", "statement": "s2", "due": "2026-11-21",
                        "status": "miss", "prob": 0.5}) + "\n" +
            json.dumps({"id": "P3", "task_id": "T12", "statement": "s3", "due": "2027-01-01",
                        "status": "open", "prob": 0.7}) + "\n",
            encoding="utf-8")
        (tmp / "data" / "cost_ledger.jsonl").write_text(
            json.dumps({"ts": "2026-11-21T11:00:00", "cost_usd": 0.1, "ok": True}) + "\n",
            encoding="utf-8")

        snap = compute(tmp, "r1", parse_ts("2026-11-21"), parse_ts("2026-11-22"))
        check("delivery_rate=1/3", snap["metrics"]["delivery_rate"]["value"] == 0.3333)
        check("hit_rate=1/2", snap["metrics"]["hit_rate"]["value"] == 0.5)
        # 3.0(回执) + 0.1*7.2 = 3.72；有效产物 1 -> 3.72
        check("cost=3.72", abs(snap["metrics"]["cost_per_product_cny"]["value"] - 3.72) < 1e-6)
        check("失败不删", snap["detail"]["receipts_failed"] == 1)
        check("缺成本回执被标记", snap["detail"]["receipts_missing_cost"] == 1)

        # 空目录：分母为 0 -> null，不是 0
        empty = tmp / "empty"
        (empty / "ops" / "bus" / "tasks").mkdir(parents=True)
        (empty / "ops" / "bus" / "out").mkdir(parents=True)
        s2 = compute(empty, "r0")
        check("空分母返回 null", s2["metrics"]["delivery_rate"]["value"] is None
              and s2["metrics"]["hit_rate"]["value"] is None
              and s2["metrics"]["cost_per_product_cny"]["value"] is None)

        # 下降 -> 至少 1 条可执行动作
        prev = {"ts": "2026-11-20T00:00:00", "metrics": {
            "delivery_rate": {"value": 0.9}, "hit_rate": {"value": 0.9},
            "cost_per_product_cny": {"value": 1.0}}}
        ev = evaluate_against(prev, snap)
        check("三项下降给出动作", len(ev["actions"]) == 3)
        check("动作可执行(含动词/路径)", all(len(a) > 10 for a in ev["actions"]))

        rem = hermes_reminder(snap, ev)
        check("Hermes 只提醒", rem["mode"] == "degraded_reminder_only" and "自动改制度" in rem["forbidden"])

        tpl = TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.exists() else "{{ROUND}}|{{NEXT_ACTION}}"
        report = render_report(snap, ev, tpl)
        check("周报含轮次与动作", "r1" in report and ev["actions"][0] in report)
        check("周报无未替换占位", "{{" not in report)
    finally:
        import shutil
        shutil.rmtree(str(tmp), ignore_errors=True)

    passed = sum(1 for _, c in ok if c)
    for name, cond in ok:
        print("%s %s" % ("PASS" if cond else "FAIL", name))
    print("self-test %d/%d" % (passed, len(ok)))
    return 0 if passed == len(ok) else 1


# ---------------------------------------------------------------- CLI
def cmd_pred_add(root: Path, args):
    path = root / "ops" / "metrics_ledger" / "predictions.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not args.id or not args.statement or not args.due:
        print("need --id --statement --due")
        return 2
    row = {"id": args.id, "task_id": args.task or "", "statement": args.statement,
           "due": args.due, "prob": args.prob, "status": "open",
           "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("added %s" % args.id)
    return 0


def cmd_pred_settle(root: Path, args):
    path = root / "ops" / "metrics_ledger" / "predictions.jsonl"
    if not path.exists():
        print("predictions.jsonl missing")
        return 2
    if args.result not in ("hit", "miss", "void"):
        print("--result must be hit|miss|void")
        return 2
    rows, found = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("id") == args.id:
            row["status"] = args.result
            row["settled_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            found = True
        rows.append(row)
    if not found:
        print("id not found: %s" % args.id)
        return 2
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print("settled %s=%s" % (args.id, args.result))
    return 0


def cmd_history(root: Path):
    d = root / "ops" / "metrics_ledger" / "rounds"
    rows = []
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        s = load_json(p, {}) or {}
        m = s.get("metrics") or {}
        rows.append({
            "round": s.get("round", p.stem),
            "ts": s.get("ts"),
            "delivery_rate": (m.get("delivery_rate") or {}).get("value"),
            "hit_rate": (m.get("hit_rate") or {}).get("value"),
            "cost_per_product_cny": (m.get("cost_per_product_cny") or {}).get("value"),
        })
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="T8 每轮指标")
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--round", default=datetime.now().strftime("r%Y%m%d"))
    ap.add_argument("--since", default=None)
    ap.add_argument("--until", default=None)
    ap.add_argument("--tasks", default=None, help="逗号分隔，如 T3,T4")
    ap.add_argument("--usd-cny", type=float, default=7.2)
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--history", action="store_true")
    ap.add_argument("--hermes-remind", action="store_true")
    ap.add_argument("--pred-add", action="store_true")
    ap.add_argument("--pred-settle", action="store_true")
    ap.add_argument("--id", default=None)
    ap.add_argument("--statement", default=None)
    ap.add_argument("--due", default=None)
    ap.add_argument("--prob", type=float, default=None)
    ap.add_argument("--task", default=None)
    ap.add_argument("--result", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root)
    if args.self_test:
        return self_test()
    if args.pred_add:
        return cmd_pred_add(root, args)
    if args.pred_settle:
        return cmd_pred_settle(root, args)
    if args.history:
        return cmd_history(root)

    if not root.exists():
        print("root not found: %s" % root)
        return 2

    since = parse_ts(args.since)
    until = parse_ts(args.until)
    if args.since and since is None:
        print("bad --since")
        return 2
    if args.until and until is None:
        print("bad --until")
        return 2
    task_ids = [t.strip() for t in args.tasks.split(",")] if args.tasks else None

    snap = compute(root, args.round, since, until, task_ids, args.usd_cny)
    prev = previous_snapshot(root, args.round)
    ev = evaluate_against(prev, snap)
    snap["evaluation"] = ev
    snap["next_action"] = ev["actions"][0] if ev["actions"] else \
        "指标未下降：保持节奏，本轮把单产物成本压到 ≤¥5。"

    if not args.no_save:
        write_json(root / "ops" / "metrics_ledger" / "rounds" / (args.round + ".json"), snap)
        tpl = TEMPLATE.read_text(encoding="utf-8") if TEMPLATE.exists() else "# {{ROUND}}\n\n{{METRIC_TABLE}}\n\n下一步：{{NEXT_ACTION}}\n"
        report = render_report(snap, ev, tpl)
        rp = root / "ops" / "metrics_ledger" / "reports" / ("WEEKLY_%s.md" % args.round)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(report, encoding="utf-8")
        snap["report_path"] = str(rp)

    if args.hermes_remind:
        rem = hermes_reminder(snap, ev)
        write_json(root / "ops" / "metrics_ledger" / "hermes_reminder.json", rem)
        snap["hermes_reminder"] = rem

    if args.json:
        print(json.dumps(snap, ensure_ascii=False, indent=2))
    else:
        m = snap["metrics"]
        print("round=%s" % snap["round"])
        for key in METRIC_KEYS:
            print("  %-22s %s  (%s)" % (key, m[key]["value"],
                                        "num=%s/den=%s" % (m[key].get("num"), m[key].get("den"))
                                        if "den" in m[key] else "spent=%s" % m[key].get("spent_cny")))
        print("  next_action: %s" % snap["next_action"])
        if "report_path" in snap:
            print("  report: %s" % snap["report_path"])
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    raise SystemExit(main())
