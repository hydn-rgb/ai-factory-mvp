#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""audit.py — 回执验收器（T6）

只做本地校验：不联网、不调用模型、不改宪法/审批。
校验 out/Tn.json 的 status / artifact / sha / rows / owner：
  - 缺字段、产物不存在、sha 不符、rows 非正数  -> 拒收
  - 回执 owner 与 state owner 不一致           -> 拒收（同一任务两 owner）
  - state 里同一 owner 负责多个任务            -> 拒收
  - --apply 时：通过且 PASS -> state 标 done；拒收 -> 状态回 todo

用法：
  python ops/bus/audit.py                     # 审计全部回执（只读）
  python ops/bus/audit.py --task T6 --json    # 只看 T6，输出 JSON
  python ops/bus/audit.py --apply             # 把结论写回 state.json（先备份）
  python ops/bus/audit.py --self-test         # 伪造/真实回执全量自检
"""
import argparse
import hashlib
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
REQUIRED = ("task_id", "owner", "status", "artifact", "sha", "rows")
OK_STATUS = ("PASS", "FAIL", "UNVERIFIED")
DONE_STATUS = ("done", "PASS")


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def stamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha_ok(actual, claimed):
    a = str(actual or "").lower()
    c = str(claimed or "").strip().lower()
    if not a or not c:
        return False
    if len(c) >= 8 and a.startswith(c):
        return True
    return a[:16] == c[:16]


def norm_owner(value):
    s = str(value or "").strip()
    for pref in ("执行窗口", "窗口", "worker", "window"):
        if s.lower().startswith(pref.lower()):
            s = s[len(pref):]
            break
    return s.strip(" -_#:：·").lower()


def load_state(bus):
    p = Path(bus) / "state.json"
    if not p.exists():
        raise FileNotFoundError("state.json 缺失: %s" % p)
    return json.loads(p.read_text(encoding="utf-8"))


def state_sig(bus):
    p = Path(bus) / "state.json"
    return sha256_file(p) if p.exists() else ""


def save_state(bus, state, backup=True, expect_sha=None):
    bus = Path(bus)
    p = bus / "state.json"
    if expect_sha is not None and state_sig(bus) != expect_sha:
        raise RuntimeError("state.json 已被其他窗口修改，拒绝覆盖（写前 sha 校验失败）")
    if backup and p.exists():
        bak = bus / ("state.json.bak-T6-%s" % stamp())
        shutil.copy2(str(p), str(bak))
    state["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    p.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return p


def owners_map(state):
    out = {}
    for tid, t in sorted((state.get("tasks") or {}).items()):
        out.setdefault(norm_owner(t.get("owner")), []).append(tid)
    return out


def audit_receipt(path, state, bus=None):
    """审计单份回执，返回 {task_id, verdict, accepted, errors, warnings, ...}。"""
    path = Path(path)
    bus = Path(bus) if bus else path.parent.parent
    res = {
        "receipt": str(path),
        "task_id": path.stem,
        "owner": "",
        "status": "",
        "verdict": "REJECT",
        "accepted": False,
        "errors": [],
        "warnings": [],
        "checked_at": now_iso(),
    }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        res["errors"].append("JSON 解析失败: %s" % type(e).__name__)
        return res
    if not isinstance(data, dict):
        res["errors"].append("回执必须是 JSON 对象")
        return res

    for key in REQUIRED:
        val = data.get(key)
        if val is None or val == "":
            res["errors"].append("缺字段: %s" % key)
    res["task_id"] = str(data.get("task_id") or path.stem).strip()
    res["owner"] = str(data.get("owner") or "").strip()
    res["status"] = str(data.get("status") or "").strip()
    res["artifact"] = str(data.get("artifact") or "").strip()
    res["sha"] = str(data.get("sha") or "").strip()
    res["rows"] = data.get("rows")

    if res["task_id"] != path.stem:
        res["errors"].append("task_id(%s) 与文件名(%s) 不一致" % (res["task_id"], path.stem))
    if res["status"] and res["status"] not in OK_STATUS:
        res["errors"].append("status 非法: %s" % res["status"])

    rows = data.get("rows")
    if isinstance(rows, bool) or not isinstance(rows, int) or rows <= 0:
        res["errors"].append("rows 必须是正整数（证据行数/检查项数）")

    tasks = state.get("tasks") or {}
    entry = tasks.get(res["task_id"])
    if entry is None:
        res["errors"].append("state 未登记任务 %s" % res["task_id"])
    else:
        if not res["owner"]:
            pass
        elif norm_owner(res["owner"]) != norm_owner(entry.get("owner")):
            if data.get("maintenance") and norm_owner(data.get("maintained_by") or "") == "w0":
                res["warnings"].append("W0 维护复验：允许 owner 不一致")
            else:
                res["errors"].append(
                    "owner 不一致: 回执=%s state=%s（同一任务不得两 owner）"
                    % (res["owner"], entry.get("owner"))
                )
        dup = [t for t in owners_map(state).get(norm_owner(entry.get("owner")), [])
               if t != res["task_id"]]
        if dup:
            res["errors"].append(
                "owner %s 同时负责 %s（同一任务两 owner）"
                % (entry.get("owner"), ",".join(dup))
            )

    art = Path(res["artifact"]) if res["artifact"] else None
    if art is not None:
        if not art.is_absolute():
            # 发行包内回执路径统一相对仓库根（check_handoff 同样按 CWD 解析）
            art = Path(bus).parent.parent / art
        if not art.exists():
            res["errors"].append("产物不存在: %s" % art)
        elif art.is_dir():
            res["errors"].append("产物是目录，sha 无法直接校验: %s" % art)
        else:
            actual = sha256_file(art)
            res["artifact_sha256"] = actual
            if not res["sha"]:
                pass
            elif not sha_ok(actual, res["sha"]):
                res["errors"].append("sha 与产物不符: 回执=%s 实际=%s" % (res["sha"][:16], actual[:16]))
            res["artifact_exists"] = True

    # 可选证据文件：声明了就必须存在；声明了 sha 就必须一致
    ev = data.get("evidence_path")
    if ev:
        evp = Path(str(ev))
        if not evp.is_absolute():
            evp = bus / evp
        if not evp.exists():
            res["errors"].append("证据文件不存在: %s" % evp)
        else:
            res["evidence_exists"] = True
    report = data.get("report") or {}
    if isinstance(report, dict) and report.get("path"):
        rp = Path(str(report["path"]))
        if not rp.is_absolute():
            rp = bus / rp
        if not rp.exists():
            res["errors"].append("报告文件不存在: %s" % rp)
        elif report.get("sha") and not sha_ok(sha256_file(rp), report["sha"]):
            res["errors"].append("报告 sha 不符: %s" % rp)

    res["accepted"] = not res["errors"]
    res["verdict"] = "ACCEPT" if res["accepted"] else "REJECT"
    if res["accepted"] and res["status"] != "PASS":
        res["warnings"].append("回执有效但 status=%s，不会进入 done" % res["status"])
    return res


def audit_all(bus=None):
    bus = Path(bus) if bus else BUS
    state = load_state(bus)
    results = []
    for p in sorted((bus / "out").glob("T*.json")):
        results.append(audit_receipt(p, state, bus))
    return results


def apply_results(bus, results):
    bus = Path(bus)
    sig = state_sig(bus)
    state = load_state(bus)
    tasks = state.setdefault("tasks", {})
    changed = []
    for r in results:
        tid = r.get("task_id")
        entry = tasks.get(tid)
        if entry is None:
            continue
        old = entry.get("status")
        if r["accepted"] and r["status"] == "PASS":
            entry["status"] = "done"
            entry["artifact"] = r.get("artifact", "")
            entry["sha"] = r.get("sha", "")
            entry["rows"] = r.get("rows")
            entry["verified_at"] = r.get("checked_at")
            entry["receipt"] = str(Path(r["receipt"]).relative_to(bus)).replace("\\", "/")
        else:
            entry["status"] = "todo"
            entry["last_reject"] = {
                "at": r.get("checked_at"),
                "receipt": str(Path(r["receipt"]).name),
                "errors": r.get("errors", []),
            }
        if old != entry.get("status"):
            changed.append({"task_id": tid, "from": old, "to": entry.get("status")})
    save_state(bus, state, backup=True, expect_sha=sig)
    try:
        hb = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "accepted": sum(1 for r in results if r.get("accepted")),
            "rejected": sum(1 for r in results if not r.get("accepted")),
            "open": sum(1 for v in tasks.values() if v.get("status") in ("todo", "doing")),
        }
        (bus / "heartbeat.json").write_text(json.dumps(hb, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return changed


def print_results(results, as_json=False):
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    for r in results:
        line = "%s %s owner=%s rows=%s" % (
            r["verdict"], r["task_id"], r["owner"] or "-", r.get("rows", "-"))
        print(line)
        for e in r["errors"]:
            print("  - " + e)
        for w in r["warnings"]:
            print("  ! " + w)


# ---------------------------------------------------------------- 自检
def _write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def self_test():
    root = Path(tempfile.mkdtemp(prefix="t6_audit_", dir=str(BUS)))
    checks = []

    def check(name, cond, detail=""):
        checks.append({"name": name, "ok": bool(cond), "detail": detail})

    try:
        (root / "out").mkdir()
        (root / "tasks").mkdir()
        art = root / "artifact.txt"
        art.write_text("real-evidence\n", encoding="utf-8")
        digest = sha256_file(art)
        state = {"tasks": {
            "T20": {"owner": "W20", "status": "todo", "artifact": "", "sha": ""},
            "T21": {"owner": "W21", "status": "todo", "artifact": "", "sha": ""},
        }}
        (root / "state.json").write_text(json.dumps(state), encoding="utf-8")

        def receipt(name, **over):
            data = {"task_id": name, "owner": "W%s" % name[1:], "status": "PASS",
                    "artifact": str(art), "sha": digest[:16], "rows": 3}
            data.update(over)
            p = root / "out" / (name + ".json")
            p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return p

        good = receipt("T20")
        r = audit_receipt(good, load_state(root), root)
        check("真实回执通过", r["accepted"], r["errors"])

        cases = [
            ("伪造-缺 rows", dict(rows=None)),
            ("伪造-产物不存在", dict(artifact=str(root / "nope.txt"))),
            ("伪造-sha 不符", dict(sha="0" * 16)),
            ("伪造-owner 不符", dict(owner="W99")),
            ("伪造-status 非法", dict(status="已完成")),
            ("伪造-rows=0", dict(rows=0)),
        ]
        for i, (name, over) in enumerate(cases):
            p = receipt("T21", **over)
            r = audit_receipt(p, load_state(root), root)
            check(name + " 被拒", not r["accepted"], r["errors"])

        # 同一 owner 负责两个任务 -> 拒收
        dup = {"tasks": {
            "T20": {"owner": "W20", "status": "todo"},
            "T21": {"owner": "W20", "status": "todo"},
        }}
        (root / "state.json").write_text(json.dumps(dup), encoding="utf-8")
        p = receipt("T21", owner="W20")
        r = audit_receipt(p, load_state(root), root)
        check("同一 owner 两任务被拒", not r["accepted"], r["errors"])

        # 恢复并 apply：真实 PASS -> done，伪造 -> todo
        (root / "state.json").write_text(json.dumps(state), encoding="utf-8")
        good = receipt("T20")
        bad = receipt("T21", sha="0" * 16)
        rs = [audit_receipt(good, state, root), audit_receipt(bad, state, root)]
        changed = apply_results(root, rs)
        st = load_state(root)
        check("通过后 state=done", st["tasks"]["T20"]["status"] == "done", changed)
        check("拒收后 state=todo", st["tasks"]["T21"]["status"] == "todo", changed)
    finally:
        shutil.rmtree(str(root), ignore_errors=True)

    passed = sum(1 for c in checks if c["ok"])
    for c in checks:
        print("%s %s%s" % ("PASS" if c["ok"] else "FAIL", c["name"],
                           "" if c["ok"] else " :: %s" % c["detail"]))
    print("self_test %d/%d" % (passed, len(checks)))
    return 0 if passed == len(checks) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="T6 回执验收器")
    ap.add_argument("--bus", default=str(BUS))
    ap.add_argument("--task", action="append", default=[], help="只看指定任务，可重复")
    ap.add_argument("--apply", action="store_true", help="把验收结论写回 state.json")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    bus = Path(args.bus)
    state = load_state(bus)
    if args.task:
        paths = [bus / "out" / (t + ".json") for t in args.task]
        missing = [str(p) for p in paths if not p.exists()]
        if missing:
            print("FAIL 回执不存在: %s" % ", ".join(missing))
            return 1
        results = [audit_receipt(p, state, bus) for p in paths]
    else:
        results = audit_all(bus)
    print_results(results, args.json)
    if args.apply:
        try:
            changed = apply_results(bus, results)
        except RuntimeError as e:
            print("FAIL %s" % e)
            return 1
        if not args.json:
            for c in changed:
                print("STATE %s %s -> %s" % (c["task_id"], c["from"], c["to"]))
    return 0 if all(r["accepted"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
