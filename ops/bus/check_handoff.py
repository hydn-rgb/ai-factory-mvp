# -*- coding: utf-8 -*-
"""校验回执与状态：缺字段、sha 不符、一任务多 owner 都判 FAIL。"""
import json, hashlib, re, sys, tempfile, os
from pathlib import Path

BUS = Path(__file__).resolve().parents[2] / "ops" / "bus"
REQ = ("task_id", "owner", "status", "artifact", "sha", "rows")
OK_STATUS = ("PASS", "FAIL", "UNVERIFIED")
RECEIPT_RE = re.compile(r"^T\d+\.json$")


def sha16(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


def check_file(p: Path) -> list:
    errs = []
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return ["%s: JSON 解析失败 %s" % (p.name, type(e).__name__)]
    for k in REQ:
        if not d.get(k):
            errs.append("%s: 缺字段 %s" % (p.name, k))
    if d.get("status") not in OK_STATUS:
        errs.append("%s: status 非法" % p.name)
    art = Path(str(d.get("artifact") or ""))
    if art and art.exists():
        if d.get("sha") and sha16(art) != str(d.get("sha"))[:16]:
            errs.append("%s: sha 与产物不符" % p.name)
    elif art:
        errs.append("%s: 产物不存在 %s" % (p.name, art))
    return errs


def check_state() -> list:
    errs = []
    p = BUS / "state.json"
    if not p.exists():
        return ["state.json 缺失"]
    st = json.loads(p.read_text(encoding="utf-8"))
    owners = {}
    for tid, t in (st.get("tasks") or {}).items():
        owners.setdefault(t.get("owner"), []).append(tid)
    for o, tids in owners.items():
        if len(tids) > 1:
            errs.append("owner %s 同时负责 %s（一任务一窗口被破坏）" % (o, ",".join(tids)))
    return errs


def main() -> int:
    errs = check_state()
    outs = sorted(p for p in (BUS / "out").glob("T*.json") if RECEIPT_RE.match(p.name))
    for p in outs:
        errs += check_file(p)
    print("out_files", len(outs))
    if errs:
        print("\n".join("FAIL " + e for e in errs))
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
