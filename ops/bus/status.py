#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""status.py — 一屏看飞轮是否真的在跑。

读：state.json、tasks/*.md、out/*.json、heartbeat.json
不改任何文件；审计用 audit.audit_receipt（只读）。
用法：python ops/bus/status.py [--json]
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

BUS = Path(__file__).resolve().parent
sys.path.insert(0, str(BUS))
import audit  # noqa: E402
import check_card  # noqa: E402


def ts(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds") if p.exists() else "-"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    state = audit.load_state(BUS)
    tasks = state.get("tasks") or {}
    receipts = {}
    for p in sorted((BUS / "out").glob("T*.json")):
        receipts[p.stem] = audit.audit_receipt(p, state, BUS)

    rows = []
    for tid in sorted(tasks, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0):
        v = tasks[tid]
        r = receipts.get(tid) or {}
        card = BUS / "tasks" / (tid + ".md")
        cc = check_card.check(card) if card.exists() else {"ok": False, "errors": ["卡不存在"]}
        rows.append({
            "task": tid, "owner": v.get("owner"), "status": v.get("status"),
            "budget": v.get("budget_cny", "-"), "spent": v.get("spent_cny", 0),
            "verdict": (r.get("verdict") or "-") if r else "-",
            "receipt": "Y" if r else "-",
            "card": "OK" if cc["ok"] else "BAD",
        })

    open_n = sum(1 for v in tasks.values() if v.get("status") in ("todo", "doing"))
    done_n = sum(1 for v in tasks.values() if v.get("status") == "done")
    hb = {}
    hp = BUS / "heartbeat.json"
    if hp.exists():
        try:
            hb = json.loads(hp.read_text(encoding="utf-8"))
        except ValueError:
            hb = {}

    out = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "open": open_n, "done": done_n, "cancelled": sum(1 for v in tasks.values() if v.get("status") == "cancelled"),
        "wip_cap": 12,
        "last_heartbeat": hb.get("ts", "-"),
        "state_mtime": ts(BUS / "state.json"),
        "latest_receipt": max((ts(p) for p in (BUS / "out").glob("T*.json")), default="-"),
        "tasks": rows,
    }
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    print("open=%d/%d done=%d cancelled=%d" % (open_n, out["wip_cap"], done_n, out["cancelled"]))
    print("heartbeat=%s  state=%s  latest_receipt=%s" % (out["last_heartbeat"], out["state_mtime"], out["latest_receipt"]))
    print("%-5s %-6s %-10s %-10s %-9s %-7s %-5s" % ("task", "owner", "status", "budget/spent", "verdict", "card", "rcpt"))
    for r in rows:
        print("%-5s %-6s %-10s %-10s %-9s %-7s %-5s" % (
            r["task"], r["owner"], r["status"], "%s/%s" % (r["budget"], r["spent"]),
            r["verdict"], r["card"], r["receipt"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
