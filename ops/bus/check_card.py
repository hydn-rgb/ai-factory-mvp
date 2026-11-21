#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""check_card.py — 任务卡完整性校验（裂变前置）

规则：
  - 必填：task_id / owner / 目标 / 验收 / 预算
  - 下一步：写“无（已归档）”或 4 段：动作 | owner | 验收 | 预算
  - 行数 ≤ 32；task_id 必须与文件名一致
用法：python ops/bus/check_card.py [T5 ...] [--json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

BUS = Path(__file__).resolve().parent
REQ = ("task_id", "owner", "目标", "验收", "预算")
MAX_LINES = 32


def field(text, label):
    m = re.search(r"^\s*[-*]\s*%s[^:：]*[:：]\s*(.+?)\s*$" % re.escape(label), text, re.M)
    return m.group(1).strip() if m else ""


def check(path: Path) -> dict:
    errs = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for k in REQ:
        if not field(text, k):
            errs.append("缺字段 %s" % k)
    tid = field(text, "task_id")
    if tid and tid != path.stem:
        errs.append("task_id(%s) 与文件名(%s) 不一致" % (tid, path.stem))
    nxt = field(text, "下一步")
    if not nxt:
        errs.append("缺「下一步」")
    elif not nxt.startswith("无"):
        parts = [p.strip() for p in re.split(r"[|｜]", nxt)]
        if len(parts) != 4 or not all(parts):
            errs.append("「下一步」需 4 段：动作|owner|验收|预算")
    lines = len(text.splitlines())
    if lines > MAX_LINES:
        errs.append("超过 %d 行（%d）" % (MAX_LINES, lines))
    return {"card": path.name, "ok": not errs, "errors": errs, "lines": lines}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tasks", nargs="*")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    paths = ([BUS / "tasks" / (t + ".md") for t in a.tasks] if a.tasks
             else sorted((BUS / "tasks").glob("T*.md")))
    rows = [check(p) for p in paths if p.exists()]
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        for r in rows:
            print(("PASS " if r["ok"] else "FAIL ") + r["card"] + " " + str(r["lines"]) + "行")
            for e in r["errors"]:
                print("  - " + e)
    return 0 if all(r["ok"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
