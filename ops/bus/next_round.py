#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""next_round.py — 验收通过后自动派发下一轮（T6 飞轮）

链路：
  out/Tn.json --(audit.py)--> PASS --(本脚本)--> state Tn=done
                                             -> tasks/T{n+1}.md
                                             -> state 登记新卡 todo

规则：
  - 只认 audit.py 判为 ACCEPT 且 status=PASS 的回执；伪造/缺证据一律不派卡
  - 下一轮目标必须来自源卡「下一步」四段；缺失则返回 INCOMPLETE，不生成占位卡
  - 限深 ≤3、开放卡 ≤12、同目标去重；跨 owner 由新卡自动分配
  - 同一任务重复运行不会重复派卡（idempotent）
  - 不改宪法/审批；不替人做价值判断

用法：
  python ops/bus/next_round.py --task T6          # 预演（只读）
  python ops/bus/next_round.py --task T6 --apply  # 标记 done + 生成下一轮卡
  python ops/bus/next_round.py --all --apply
  python ops/bus/next_round.py --self-test
"""
import argparse
import json
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BUS = Path(__file__).resolve().parent
sys.path.insert(0, str(BUS))
import audit  # noqa: E402
import check_card  # noqa: E402

CARD_MAX_LINES = 20
MAX_DEPTH = 3
MAX_OPEN = 12


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _num(tid):
    m = re.match(r"^T(\d+)$", str(tid or "").strip())
    return int(m.group(1)) if m else 0


def next_task_id(bus, state):
    ids = set((state.get("tasks") or {}).keys())
    ids |= {p.stem for p in (Path(bus) / "tasks").glob("T*.md")}
    return "T%d" % (max([_num(t) for t in ids] or [0]) + 1)


def next_owner(state):
    nums = []
    for entry in (state.get("tasks") or {}).values():
        m = re.search(r"(\d+)", str(entry.get("owner") or ""))
        if m:
            nums.append(int(m.group(1)))
    return "W%d" % (max(nums or [0]) + 1)


def _field(text, label):
    pat = re.compile(r"^\s*[-*]\s*%s\s*[:：]\s*(.+?)\s*$" % re.escape(label), re.M)
    m = pat.search(text)
    return m.group(1).strip() if m else ""


def card_title(text):
    m = re.search(r"^#\s*T\d+\s*[·:：-]\s*(.+?)\s*$", text, re.M)
    return m.group(1).strip() if m else ""


def read_next_step(text):
    """优先读 '- 下一步: ...'，其次读 '## 下一步' 段落。"""
    m = re.search(r"^\s*[-*]\s*下一步\s*[:：]\s*(.+?)\s*$", text, re.M)
    if m:
        return m.group(1).strip()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^#{1,6}\s*下一步\s*$", line.strip()):
            buf = []
            for nxt in lines[i + 1:]:
                if re.match(r"^#{1,6}\s+", nxt):
                    break
                s = nxt.strip()
                if s:
                    buf.append(re.sub(r"^[-*]\s*", "", s))
            if buf:
                return "；".join(buf)
    return ""


def build_card(bus, state, tid, result, source_text, budget=None):
    new_id = next_task_id(bus, state)
    new_owner = next_owner(state)
    title = card_title(source_text)
    explicit = read_next_step(source_text)
    goal = explicit
    note = ""
    budget = budget or _field(source_text, "预算") or "¥10 / 3h"
    artifact = result.get("artifact") or ""

    lines = [
        "# %s · 续轮：%s%s" % (new_id, tid, (" " + title) if title else ""),
        "",
        "- task_id: %s" % new_id,
        "- owner: %s" % new_owner,
        "- parent: %s" % tid,
        "- source_receipt: `out/%s.json`" % tid,
        "- 目标: %s" % goal[:300],
        "- 输入: `ops/bus/out/%s.json`；产物 `%s`" % (tid, artifact),
        "- 输出: `ops/bus/out/%s.json` + 本轮产物" % new_id,
        "- 验收: 产物存在且 sha 与回执一致；rows>0；给出可推翻条件",
        "- 预算: %s" % budget,
        "- 禁止: 不自动改宪法/审批；不替人做价值判断",
        "- 下一步: 完成本卡时写清下一轮动作；无则报 W0，不自行加码",
        "- 回执: `out/%s.json` = {task_id, owner, status, artifact, sha, rows}" % new_id,
    ]
    if note:
        lines.append("- 备注: %s" % note)
    if len(lines) > CARD_MAX_LINES:
        lines = lines[:CARD_MAX_LINES]
    return new_id, new_owner, goal, explicit, "\n".join(lines) + "\n"


def process_task(bus, state, tid, apply=False):
    bus = Path(bus)
    out = {"task_id": tid, "action": "", "ok": False, "detail": ""}
    receipt_path = bus / "out" / (tid + ".json")
    if not receipt_path.exists():
        out.update(action="skip", detail="回执不存在")
        return out
    result = audit.audit_receipt(receipt_path, state, bus)
    if not result["accepted"]:
        out.update(action="refuse", detail="；".join(result["errors"]))
        return out
    if result["status"] != "PASS":
        out.update(action="refuse", detail="status=%s，只有 PASS 才派下一轮" % result["status"])
        return out

    entry = (state.get("tasks") or {}).get(tid)
    if entry is None:
        out.update(action="refuse", detail="state 未登记 %s" % tid)
        return out

    budget_cny = float(entry.get("budget_cny", 10) or 10)
    spent = float(entry.get("spent_cny", 0) or 0)
    child_budget = max(1.0, budget_cny - spent)

    previous = entry.get("next_task")
    if previous:
        card = bus / "tasks" / (previous + ".md")
        if card.exists() and previous in (state.get("tasks") or {}):
            out.update(action="already", ok=True, detail="已派发 %s" % previous,
                       next_task=previous)
            return out

    task_path = bus / "tasks" / (tid + ".md")
    source_text = task_path.read_text(encoding="utf-8", errors="replace") if task_path.exists() else ""
    card_check = check_card.check(task_path) if task_path.exists() else {"ok": False, "errors": ["卡不存在"]}
    if not card_check["ok"]:
        out.update(action="refuse", detail="INCOMPLETE: " + "；".join(card_check["errors"]))
        return out
    step = read_next_step(source_text)
    if not step or step.startswith("无"):
        out.update(action="refuse", detail="INCOMPLETE: 下一步为空或已归档")
        return out

    # 限深：沿 parent 链回溯
    depth, cur = 0, tid
    tasks = state.get("tasks") or {}
    while cur in tasks and depth <= MAX_DEPTH:
        parent = tasks[cur].get("parent")
        if not parent:
            break
        depth += 1
        cur = parent
    if depth >= MAX_DEPTH:
        out.update(action="refuse", detail="DEPTH: 链深已达 %d" % depth)
        return out

    # 开放卡上限
    open_cards = [t for t, v in tasks.items() if v.get("status") in ("todo", "doing")]
    if len(open_cards) >= MAX_OPEN:
        out.update(action="refuse", detail="WIP: 开放卡 %d ≥ %d" % (len(open_cards), MAX_OPEN))
        return out

    # 同目标去重（已存在开放卡则不重复生成）
    goal_key = re.sub(r"\s+", "", step)[:40]
    for t in open_cards:
        if t == tid:
            continue
        p = bus / "tasks" / (t + ".md")
        if p.exists():
            other = read_next_step(p.read_text(encoding="utf-8", errors="replace"))
            if other and re.sub(r"\s+", "", other)[:40] == goal_key:
                out.update(action="already", ok=True, detail="同目标卡已存在 %s" % t)
                return out

    new_id, new_owner, goal, explicit, card_text = build_card(
        bus, state, tid, result, source_text, budget="¥%.0f" % child_budget)

    out.update(action="dispatch" if apply else "would_dispatch", ok=True,
               next_task=new_id, next_owner=new_owner, goal=goal,
               source_of_goal="下一步" if explicit else "fallback",
               card_path=str(bus / "tasks" / (new_id + ".md")))
    if not apply:
        return out

    (bus / "tasks" / (new_id + ".md")).write_text(card_text, encoding="utf-8")
    entry["status"] = "done"
    entry["artifact"] = result.get("artifact", "")
    entry["sha"] = result.get("sha", "")
    entry["rows"] = result.get("rows")
    entry["verified_at"] = result.get("checked_at") or now_iso()
    entry["receipt"] = "out/%s.json" % tid
    entry["next_task"] = new_id
    state.setdefault("tasks", {})[new_id] = {
        "owner": new_owner,
        "status": "todo",
        "artifact": "",
        "sha": "",
        "parent": tid,
        "source_receipt": "out/%s.json" % tid,
        "created_at": now_iso(),
        "budget_cny": round(child_budget, 2),
        "spent_cny": 0,
    }
    return out


def run(bus, tids, apply=False, as_json=False):
    sig = audit.state_sig(bus)
    state = audit.load_state(bus)
    results = [process_task(bus, state, tid, apply=apply) for tid in tids]
    if apply and any(r["action"] == "dispatch" for r in results):
        try:
            audit.save_state(bus, state, backup=True, expect_sha=sig)
        except RuntimeError as e:
            print("FAIL %s" % e)
            return 1
        try:
            hb = {"ts": now_iso(), "dispatched": [r.get("next_task") for r in results
                                                  if r.get("action") == "dispatch"],
                  "open": sum(1 for v in (state.get("tasks") or {}).values()
                              if v.get("status") in ("todo", "doing"))}
            (Path(bus) / "heartbeat.json").write_text(
                json.dumps(hb, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            flag = "PASS" if r["ok"] else "FAIL"
            nxt = (" -> " + r["next_task"]) if r.get("next_task") else ""
            print("%s %s %s%s :: %s" % (flag, r["task_id"], r["action"], nxt, r["detail"]))
            if r.get("goal"):
                print("  目标: %s (%s)" % (r["goal"], r.get("source_of_goal")))
    return 0 if all(r["ok"] for r in results) else 1


# ---------------------------------------------------------------- 自检
def self_test():
    root = Path(tempfile.mkdtemp(prefix="t6_round_", dir=str(BUS)))
    checks = []

    def check(name, cond, detail=""):
        checks.append({"name": name, "ok": bool(cond), "detail": detail})

    try:
        (root / "tasks").mkdir()
        (root / "out").mkdir()
        art = root / "artifact.txt"
        art.write_text("flywheel-evidence\n", encoding="utf-8")
        digest = audit.sha256_file(art)
        (root / "tasks" / "T50.md").write_text(
            "# T50 · 样例任务\n\n- task_id: T50\n- owner: W50\n"
            "- 目标: 验证飞轮\n- 输出: artifact.txt\n"
            "- 验收: 文件存在且 sha 一致\n- 预算: ¥10 / 3h\n"
            "- 下一步: 把样例产物复核一遍并给出来源 | W51 | 复核记录 | ¥2\n"
            "- 回执: `out/T50.json`\n",
            encoding="utf-8")
        (root / "state.json").write_text(json.dumps(
            {"tasks": {"T50": {"owner": "W50", "status": "todo", "artifact": "", "sha": ""}}}),
            encoding="utf-8")

        def receipt(**over):
            data = {"task_id": "T50", "owner": "W50", "status": "PASS",
                    "artifact": str(art), "sha": digest[:16], "rows": 4}
            data.update(over)
            (root / "out" / "T50.json").write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8")

        # 伪造回执：不派卡、不改状态
        receipt(rows=0)
        r = process_task(root, audit.load_state(root), "T50", apply=True)
        check("伪造回执不派卡", not r["ok"], r)
        st = audit.load_state(root)
        check("伪造后 state 仍 todo", st["tasks"]["T50"]["status"] == "todo")
        check("伪造后无新卡", not (root / "tasks" / "T51.md").exists())

        # 真实回执：done + 新卡，目标取自“下一步”
        receipt()
        st = audit.load_state(root)
        r = process_task(root, st, "T50", apply=True)
        audit.save_state(root, st, backup=False)
        st = audit.load_state(root)
        check("真实回执派卡成功", r["ok"] and r["action"] == "dispatch", r)
        check("state T50=done", st["tasks"]["T50"]["status"] == "done")
        check("state 登记 T51 todo", st["tasks"].get("T51", {}).get("status") == "todo")
        card = root / "tasks" / "T51.md"
        text = card.read_text(encoding="utf-8") if card.exists() else ""
        check("新卡存在", card.exists())
        check("新卡目标来自下一步", "把样例产物复核一遍并给出来源" in text)
        check("新卡不超 20 行", len(text.splitlines()) <= CARD_MAX_LINES,
              len(text.splitlines()))
        check("新 owner 不重复", st["tasks"]["T51"]["owner"] != "W50")

        # 幂等：再跑不产生 T52
        r = process_task(root, audit.load_state(root), "T50", apply=True)
        check("重复运行幂等", r["action"] == "already" and not (root / "tasks" / "T52.md").exists())
        # 缺“下一步”：拒发
        (root / "tasks" / "T60.md").write_text(
            "# T60 · 缺下一步\n\n- task_id: T60\n- owner: W60\n"
            "- 目标: 缺下一步\n- 输出: artifact.txt\n- 验收: 可验证\n- 预算: ¥1\n"
            "- 回执: `out/T60.json`\n", encoding="utf-8")
        (root / "out" / "T60.json").write_text(json.dumps(
            {"task_id": "T60", "owner": "W60", "status": "PASS",
             "artifact": str(art), "sha": digest[:16], "rows": 1}), encoding="utf-8")
        st = audit.load_state(root)
        st["tasks"]["T60"] = {"owner": "W60", "status": "todo", "artifact": "", "sha": ""}
        audit.save_state(root, st, backup=False)
        r = process_task(root, audit.load_state(root), "T60", apply=True)
        check("缺下一步拒发", (not r["ok"]) and "INCOMPLETE" in r["detail"], r)
    finally:
        shutil.rmtree(str(root), ignore_errors=True)

    passed = sum(1 for c in checks if c["ok"])
    for c in checks:
        print("%s %s%s" % ("PASS" if c["ok"] else "FAIL", c["name"],
                           "" if c["ok"] else " :: %s" % c["detail"]))
    print("self_test %d/%d" % (passed, len(checks)))
    return 0 if passed == len(checks) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="T6 自动派发下一轮")
    ap.add_argument("--bus", default=str(BUS))
    ap.add_argument("--task", action="append", default=[])
    ap.add_argument("--all", action="store_true", help="处理 out/ 下所有 PASS 回执")
    ap.add_argument("--apply", action="store_true", help="真正写 state 与任务卡")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    bus = Path(args.bus)
    if args.all:
        tids = sorted(p.stem for p in (bus / "out").glob("T*.json"))
    elif args.task:
        tids = args.task
    else:
        ap.error("需要 --task Tn 或 --all")
        return 2
    return run(bus, tids, apply=args.apply, as_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
