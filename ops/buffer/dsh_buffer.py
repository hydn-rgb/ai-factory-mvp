#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
# ============================================================
# 合规声明 (Compliance Declaration)
# 本模块只做本地校验、拒收与留痕：不联网、不调用模型、不代写被校验对象。
# 默认只读；只有 --report / --propose / 事件日志会写文件，且都在 ops/buffer 下。
# DSH 对宪法 / 任务卡 / 审批 的直接写入一律拒绝并记事件；只接受“提案”。
# 完成的判定不看自述，只看产物 sha + 命令退出码 + 证据文件是否存在。
# ============================================================
"""dsh_buffer.py —— DSH ↔ 工厂 四段缓冲层（T3）

四条链路：
  1 输入缓冲  DSH 只拿任务卡（≤20 行）；超限或夹带“全史” → 拒收
  2 输出缓冲  回执缺 status/artifact/sha/rows → 拒收；PASS 必须有五要素证据
  3 状态缓冲  回执声称的状态必须与 state.json 一致（不接受口头“已完成”）
  4 安全缓冲  DSH 不得直接改宪法/任务/审批 → 拒收并记事件，只能提案

用法：
  python dsh_buffer.py --self-test                 全量自检（含 4 条验收）
  python dsh_buffer.py --verify T3                 校验真实总线上的任务卡+回执
  python dsh_buffer.py --report                    生成校验报告
  python dsh_buffer.py --guard-write PATH --actor DSH
  python dsh_buffer.py --propose TARGET --to done --note "..."
"""
import argparse
import fnmatch
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent                      # D:\AI_Factory
BUS = ROOT / "ops" / "bus"
EVENT_LOG = BASE / "events.jsonl"
PROPOSAL_DIR = BASE / "proposals"
REPORT_PATH = BASE / "REPORT_T3.md"
ARTIFACT = Path(__file__).resolve()

REQUIRED_FIELDS = ("task_id", "owner", "status", "artifact", "sha", "rows")
OK_STATUS = ("PASS", "FAIL", "UNVERIFIED")
OK_LEVELS = ("L0", "L1", "L2", "L3")
DSH_ACTORS = ("dsh", "deepseek-harness", "deepseek_harness", "deepseek")
CARD_MAX_LINES = 20

# 受保护对象：DSH 只能提案，不能直写
PROTECTED_GLOBS = (
    "constitution.json",
    "constitution.json.*",
    "constitution*.bak-*",
    "institution/*",
    "ops/bus/tasks/*",
    "ops/bus/state.json",
    "progress/approvals.jsonl",
    "progress/approval_tickets.jsonl",
    "progress/approval_packet.json",
    "progress/plans/*",
    "quota_policy.json",
)
HISTORY_MARKS = ("## 全史", "## 历史全文", "## 上下文全文", "<full_history>")


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _norm(value):
    return str(value).replace("\\", "/").strip().lower()


def _resolve(path, root):
    p = Path(str(path))
    return p if p.is_absolute() else Path(root) / p


def _rel_to(path, root):
    """把路径归一成相对 root 的形式；不在 root 内则返回空串。"""
    ap = os.path.abspath(str(path))
    if not os.path.isabs(str(path)):
        ap = os.path.abspath(os.path.join(str(root), str(path)))
    rp = os.path.abspath(str(root))
    if os.path.normcase(ap) == os.path.normcase(rp):
        return ""
    if not os.path.normcase(ap).startswith(os.path.normcase(rp) + os.sep):
        return ""
    return _norm(os.path.relpath(ap, rp))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _append_jsonl(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def log_event(level, event, payload=None, log_path=None):
    row = {
        "ts": now_iso(),
        "level": level,
        "node": "DSH_BUFFER",
        "event": event,
        "payload": payload or {},
    }
    _append_jsonl(log_path or EVENT_LOG, row)
    return row


# ---------------------------------------------------------------- 身份/状态
def norm_owner(owner):
    s = str(owner or "").strip()
    for prefix in ("执行窗口", "窗口", "worker", "window"):
        low, pref = s.lower(), prefix.lower()
        if low.startswith(pref):
            s = s[len(prefix):].strip(" -_#:：")
            break
    return s.upper()


def _norm_status(status):
    s = _norm(status)
    if s in ("pass", "done", "completed", "complete", "ok", "green"):
        return "done"
    if s in ("fail", "failed", "red", "rejected"):
        return "fail"
    return s


def is_protected(path, root=ROOT):
    """返回 (是否受保护, 命中的规则)。"""
    rel = _rel_to(path, root)
    if not rel:
        return False, ""
    name = _norm(Path(str(path)).name)
    for pattern in PROTECTED_GLOBS:
        if fnmatch.fnmatchcase(rel, pattern) or fnmatch.fnmatchcase(name, pattern):
            return True, pattern
    return False, ""


def guard_write(path, actor, root=ROOT, log_path=None):
    """DSH 直写受保护对象 → 拒绝并记事件；其他人写 → 放行但留痕。"""
    protected, rule = is_protected(path, root)
    is_dsh = _norm(actor) in DSH_ACTORS or norm_owner(actor) == "DSH"
    if protected and is_dsh:
        event = log_event("ERROR", "DSH_PROTECTED_WRITE_REJECTED", {
            "path": str(path), "rule": rule, "actor": str(actor),
            "action": "DENY_ONLY_PROPOSE"}, log_path)
        return {"allowed": False, "reason": "PROTECTED_FOR_DSH",
                "rule": rule, "event": event["event"]}
    if protected:
        log_event("WARN", "PROTECTED_WRITE_BY_NON_DSH", {
            "path": str(path), "rule": rule, "actor": str(actor),
            "action": "ALLOW_WITH_TRACE"}, log_path)
        return {"allowed": True, "reason": "NON_DSH_OWNER", "rule": rule}
    return {"allowed": True, "reason": "NOT_PROTECTED", "rule": ""}


def propose_change(target, action="modify", frm="", to="",
                   note="", evidence="", actor="DSH",
                   root=ROOT, proposal_dir=None, extra=None):
    """受保护对象只能走提案：落 proposals/，目标文件一个字节都不动。"""
    protected, rule = is_protected(target, root)
    if not protected:
        return {"status": "REJECTED", "reason": "TARGET_NOT_PROTECTED"}
    out_dir = Path(proposal_dir or PROPOSAL_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    path = out_dir / ("prop-%s.json" % stamp)
    payload = {
        "schema": "dsh-proposal/v1",
        "proposal_id": path.stem,
        "created_at": now_iso(),
        "target": _norm(_rel_to(target, root) or target),
        "protected_by": rule,
        "action": action,
        "from": frm,
        "to": to,
        "note": note,
        "evidence": str(evidence),
        "requested_by": actor,
        "approved_by": None,
        "status": "OPEN",
        "applied": False,
    }
    if isinstance(extra, dict):
        payload.update(extra)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    tmp.replace(path)
    log_event("INFO", "PROPOSAL_WRITTEN", {
        "proposal": str(path), "target": payload["target"],
        "actor": actor}, out_dir.parent / "events.jsonl")
    return {"status": "PROPOSED", "path": str(path), "proposal": payload}


# ---------------------------------------------------------------- 1 输入缓冲
def _card_field(text, key):
    for line in str(text).splitlines():
        s = line.strip()
        if not s.startswith("-"):
            continue
        body = s[1:].strip()
        if ":" not in body:
            continue
        name, value = body.split(":", 1)
        if name.strip().lower() == key.lower():
            return value.strip()
    return ""


def read_task_card(card_path, max_lines=CARD_MAX_LINES):
    p = Path(card_path)
    result = {"path": str(p), "exists": p.is_file(),
              "max_lines": int(max_lines), "lines": 0, "sha": "",
              "card": "", "ok": False, "reasons": [], "task_id": "",
              "owner": ""}
    if not p.is_file():
        result["reasons"] = ["CARD_MISSING"]
        return result
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()
    result.update({
        "lines": len(lines),
        "sha": sha256_file(p),
        "card": text,
        "task_id": _card_field(text, "task_id"),
        "owner": _card_field(text, "owner"),
    })
    reasons = []
    if len(lines) > int(max_lines):
        reasons.append("CARD_TOO_LONG:%d>%d" % (len(lines), int(max_lines)))
    for mark in HISTORY_MARKS:
        if mark in text:
            reasons.append("CARD_CARRIES_HISTORY:%s" % mark)
    result["reasons"] = reasons
    result["ok"] = not reasons
    return result


def handoff_to_dsh(card_path, max_lines=CARD_MAX_LINES):
    """交给 DSH 的只有卡本身：卡文本 + sha + 行数，绝不附带回溯史。"""
    card = read_task_card(card_path, max_lines=max_lines)
    return {
        "task_id": card["task_id"],
        "card": card["card"],
        "sha": card["sha"],
        "lines": card["lines"],
        "ok": card["ok"],
        "reasons": card["reasons"],
    }


# ---------------------------------------------------------------- 状态缓冲
def owner_duplicates(state):
    seen = {}
    for task_id, item in ((state or {}).get("tasks") or {}).items():
        owner = norm_owner((item or {}).get("owner"))
        if not owner:
            continue
        seen.setdefault(owner, []).append(task_id)
    return ["%s <- %s" % (owner, ",".join(tids))
            for owner, tids in seen.items() if len(tids) > 1]


# ---------------------------------------------------------------- 2/3/4 输出缓冲
def validate_receipt(receipt, task_card=None, state=None, root=ROOT,
                     actor=None, event_log=None):
    checks, reasons = [], []

    def rec(name, ok, detail=""):
        ok = bool(ok)
        checks.append({"check": name, "ok": ok, "detail": str(detail)})
        if not ok:
            reasons.append(name + ((":" + str(detail)) if detail else ""))
        return ok

    if not isinstance(receipt, dict):
        return {"verdict": "REJECT", "reasons": ["NOT_AN_OBJECT"],
                "checks": checks, "artifact_sha": ""}

    # 2 输出缓冲：六字段
    for field in ("task_id", "owner", "status", "artifact", "sha"):
        value = receipt.get(field)
        rec("field:" + field,
            isinstance(value, str) and bool(value.strip()), repr(value))

    rows = receipt.get("rows")
    if isinstance(rows, bool):
        rows_ok = False
    elif isinstance(rows, int):
        rows_ok = rows >= 0
    elif isinstance(rows, list):
        rows_ok = len(rows) > 0
    else:
        rows_ok = False
    rec("field:rows", rows_ok, repr(rows))
    rec("status:allowed", receipt.get("status") in OK_STATUS,
        str(receipt.get("status")))

    # 2b 任务卡对齐（卡超限由输入缓冲单独判，不阻断回执本身）
    if isinstance(task_card, dict) and task_card.get("card"):
        card = task_card["card"]
        rec("card:task_id", norm_owner(receipt.get("task_id")) ==
            norm_owner(_card_field(card, "task_id")),
            "card=%s" % _card_field(card, "task_id"))
        card_owner = _card_field(card, "owner")
        if card_owner:
            rec("card:owner", norm_owner(card_owner) ==
                norm_owner(receipt.get("owner")),
                "card=%s" % card_owner)

    # 3 状态缓冲：state.json 是所有权的唯一事实源
    if isinstance(state, dict):
        duplicates = owner_duplicates(state)
        rec("state:owner_unique", not duplicates, "; ".join(duplicates))
        task_id = str(receipt.get("task_id") or "")
        entry = ((state.get("tasks") or {}).get(task_id))
        rec("state:entry", isinstance(entry, dict), "state.json 无 %s" % task_id)
        if isinstance(entry, dict):
            rec("state:owner_match",
                norm_owner(entry.get("owner")) ==
                norm_owner(receipt.get("owner")),
                "state=%s receipt=%s" % (entry.get("owner"),
                                         receipt.get("owner")))
            claim = receipt.get("state_claim")
            if isinstance(claim, dict):
                rec("state:status_match",
                    _norm_status(claim.get("status")) ==
                    _norm_status(entry.get("status")),
                    "claim=%s state=%s" % (claim.get("status"),
                                           entry.get("status")))
                if claim.get("sha") and entry.get("sha"):
                    rec("state:sha_match",
                        _norm(claim.get("sha")).startswith(
                            _norm(entry.get("sha"))[:16]),
                        "claim=%s state=%s" % (claim.get("sha"),
                                               entry.get("sha")))

    # 2c 产物 + sha（全量优先；截断必须显式声明，见 NEG-E5）
    artifact_sha = ""
    artifact = receipt.get("artifact")
    artifact_path = _resolve(artifact, root) if artifact else None
    rec("artifact:exists", artifact_path is not None and
        artifact_path.exists(), str(artifact_path))
    if artifact_path is not None and artifact_path.exists():
        rec("artifact:is_file", artifact_path.is_file(), str(artifact_path))
        if artifact_path.is_file():
            claimed = _norm(receipt.get("sha"))
            artifact_sha = sha256_file(artifact_path)
            if len(claimed) == 64:
                rec("sha:full_match", claimed == artifact_sha, artifact_sha)
            elif len(claimed) >= 8:
                rec("sha:prefix_match", artifact_sha.startswith(claimed),
                    artifact_sha)
                rec("sha:truncation_declared",
                    receipt.get("sha_len") == len(claimed),
                    "sha_len=%r len=%d" % (receipt.get("sha_len"),
                                           len(claimed)))
            else:
                rec("sha:full_match", False, "TOO_SHORT")

    # 报告证据：路径 + sha 都验，防止“报告写了但没落盘”
    report = receipt.get("report")
    if isinstance(report, dict) and report.get("path"):
        report_path = _resolve(report["path"], root)
        rec("report:exists", report_path.is_file(), str(report_path))
        if report_path.is_file():
            claimed = _norm(report.get("sha"))
            actual = sha256_file(report_path)
            ok = (claimed == actual) if len(claimed) == 64 \
                else (len(claimed) >= 8 and actual.startswith(claimed))
            rec("report:sha_match", ok, actual)

    # 2d 完成声明五要素（INS-A11）：缺一即视为伪造“已完成”
    if receipt.get("status") == "PASS":
        rec("claim:level", receipt.get("level") in OK_LEVELS,
            str(receipt.get("level")))
        rec("claim:command", bool(str(receipt.get("command") or "").strip()))
        exit_code = receipt.get("exit_code")
        rec("claim:exit_code",
            isinstance(exit_code, int) and not isinstance(exit_code, bool)
            and exit_code == 0, str(exit_code))
        evidence = receipt.get("evidence_path")
        evidence_path = _resolve(evidence, root) if evidence else None
        rec("claim:evidence", evidence_path is not None and
            evidence_path.exists(), str(evidence_path))
        rec("claim:request", bool(str(receipt.get("request") or "").strip()))
        self_test = receipt.get("self_test")
        if isinstance(self_test, dict):
            passed, total = self_test.get("passed"), self_test.get("total")
            rec("claim:self_test",
                isinstance(passed, int) and isinstance(total, int)
                and total > 0 and passed == total,
                "%r/%r" % (passed, total))

    # 4 安全缓冲：回执里声明的写入目标也要过闸
    writes = receipt.get("writes") or []
    if not isinstance(writes, list):
        writes = [writes]
    for target in writes:
        protected, rule = is_protected(target, root)
        bad = rec("safe:no_protected_write", not protected,
                  "%s -> %s" % (target, rule))
        if not bad and event_log:
            log_event("ERROR", "DSH_PROTECTED_WRITE_REJECTED", {
                "path": str(target), "rule": rule,
                "actor": actor or receipt.get("owner"),
                "via": "receipt"}, event_log)

    return {"verdict": "ACCEPT" if not reasons else "REJECT",
            "reasons": reasons, "checks": checks,
            "artifact_sha": artifact_sha,
            "rejected": len(reasons), "checked": len(checks)}


# ---------------------------------------------------------------- 真实总线核验
def verify(task_id="T3", root=ROOT, bus=None, event_log=None):
    bus = Path(bus or (Path(root) / "ops" / "bus"))
    card_path = bus / "tasks" / ("%s.md" % task_id)
    card = read_task_card(card_path)
    state_path = bus / "state.json"
    state = None
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            state = None
            state_error = "%s:%s" % (type(exc).__name__, exc)
        else:
            state_error = ""
    else:
        state_error = "STATE_MISSING"

    receipt_path = bus / "out" / ("%s.json" % task_id)
    receipt = {}
    if receipt_path.is_file():
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            receipt = {"_parse_error": "%s:%s" % (type(exc).__name__, exc)}

    verdict = validate_receipt(receipt, task_card=card, state=state,
                               root=root, event_log=event_log)
    entry = ((state or {}).get("tasks") or {}).get(task_id) or {}
    verdict.update({
        "task_id": task_id,
        "card_path": str(card_path),
        "card": {"lines": card["lines"], "max_lines": card["max_lines"],
                 "sha": card["sha"], "ok": card["ok"],
                 "reasons": card["reasons"]},
        "state_path": str(state_path),
        "state_error": state_error,
        "state_entry": entry,
        "receipt_path": str(receipt_path),
        "verified_at": now_iso(),
    })
    return verdict


# ---------------------------------------------------------------- 自检
def self_test():
    checks = []

    def ok(name, cond, detail=""):
        checks.append({"check": name, "ok": bool(cond),
                       "detail": str(detail)})

    tag = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    tmp = BASE / "test_tmp" / tag
    (tmp / "ops" / "bus" / "tasks").mkdir(parents=True, exist_ok=True)
    log = tmp / "events.jsonl"

    # 1 输入缓冲 -------------------------------------------------
    card20 = ("# T-20\n"
              + "\n".join("- line %d" % i for i in range(18))
              + "\n- 回执: out/T20.json\n")
    p20 = tmp / "ops" / "bus" / "tasks" / "T20.md"
    p20.write_text(card20, encoding="utf-8")
    c20 = read_task_card(p20)
    ok("输入缓冲: 20 行卡放行", c20["ok"] and c20["lines"] == 20, c20["reasons"])

    p21 = tmp / "ops" / "bus" / "tasks" / "T21.md"
    p21.write_text(card20 + "- 多一行\n", encoding="utf-8")
    c21 = read_task_card(p21)
    ok("输入缓冲: 21 行卡拒收",
       (not c21["ok"]) and any(r.startswith("CARD_TOO_LONG")
                               for r in c21["reasons"]), c21["reasons"])

    p_hist = tmp / "ops" / "bus" / "tasks" / "T22.md"
    p_hist.write_text("# T-22\n## 全史\n- 之前的全部对话...\n", encoding="utf-8")
    c_hist = read_task_card(p_hist)
    ok("输入缓冲: 夹带全史拒收",
       (not c_hist["ok"]) and any(r.startswith("CARD_CARRIES_HISTORY")
                                  for r in c_hist["reasons"]),
       c_hist["reasons"])

    handoff = handoff_to_dsh(p20)
    ok("输入缓冲: 只传卡不传全史",
       set(handoff) >= {"task_id", "card", "sha", "lines"}
       and handoff["lines"] <= 20 and "全史" not in handoff["card"],
       sorted(handoff))

    # 2 输出缓冲 -------------------------------------------------
    artifact = tmp / "artifact.txt"
    artifact.write_text("T20 artifact\n", encoding="utf-8")
    sha = sha256_file(artifact)
    good = {
        "task_id": "T20", "owner": "W20", "status": "PASS",
        "artifact": str(artifact), "sha": sha, "rows": 3,
        "level": "L1", "command": "python dsh_buffer.py --self-test",
        "exit_code": 0, "evidence_path": str(artifact),
        "request": "按卡做 T20 自检", "writes": [],
        "state_claim": {"task_id": "T20", "status": "PASS"},
        "self_test": {"passed": 3, "total": 3},
    }
    state_ok = {"tasks": {"T20": {"owner": "W20", "status": "done"}}}
    result = validate_receipt(good, state=state_ok, root=tmp)
    ok("输出缓冲: 六字段 + 五要素齐全 → 放行",
       result["verdict"] == "ACCEPT", result["reasons"])

    fake = dict(good)
    fake.update({"level": "", "command": "", "exit_code": None,
                 "evidence_path": "", "request": ""})
    fake.pop("self_test", None)
    result = validate_receipt(fake, state=state_ok, root=tmp)
    ok("验收① 伪造已完成 → 拒收",
       result["verdict"] == "REJECT"
       and any(x.startswith("claim:level") for x in result["reasons"]),
       result["reasons"])

    bad_exit = dict(good)
    bad_exit["exit_code"] = 1
    result = validate_receipt(bad_exit, state=state_ok, root=tmp)
    ok("输出缓冲: 退出码非 0 的 PASS → 拒收",
       result["verdict"] == "REJECT"
       and any(x.startswith("claim:exit_code") for x in result["reasons"]),
       result["reasons"])

    no_rows = dict(good)
    no_rows.pop("rows")
    result = validate_receipt(no_rows, state=state_ok, root=tmp)
    ok("输出缓冲: 缺 rows → 拒收",
       result["verdict"] == "REJECT"
       and any(x == "field:rows" or x.startswith("field:rows")
               for x in result["reasons"]), result["reasons"])

    bad_sha = dict(good)
    bad_sha["sha"] = "0" * 64
    result = validate_receipt(bad_sha, state=state_ok, root=tmp)
    ok("验收② sha 不符 → 拒收",
       result["verdict"] == "REJECT"
       and any(x.startswith("sha:") for x in result["reasons"]),
       result["reasons"])

    truncated = dict(good)
    truncated["sha"] = sha[:16]
    result = validate_receipt(truncated, state=state_ok, root=tmp)
    ok("验收② 截断 sha 未声明 → 拒收（NEG-E5）",
       result["verdict"] == "REJECT"
       and any(x.startswith("sha:truncation_declared")
               for x in result["reasons"]), result["reasons"])

    declared = dict(good)
    declared["sha"] = sha[:16]
    declared["sha_len"] = 16
    result = validate_receipt(declared, state=state_ok, root=tmp)
    ok("验收② 截断 sha 已声明 → 放行",
       result["verdict"] == "ACCEPT", result["reasons"])

    # 3 状态缓冲 -------------------------------------------------
    state_dup = {"tasks": {"T20": {"owner": "W20", "status": "done"},
                           "T21": {"owner": "W20", "status": "todo"}}}
    result = validate_receipt(good, state=state_dup, root=tmp)
    ok("验收③ 同一 owner 领两个任务 → 拒收",
       result["verdict"] == "REJECT"
       and any(x.startswith("state:owner_unique") for x in result["reasons"]),
       result["reasons"])

    state_owner = {"tasks": {"T20": {"owner": "W99", "status": "done"}}}
    result = validate_receipt(good, state=state_owner, root=tmp)
    ok("验收③ 回执 owner ≠ state.json owner → 拒收",
       result["verdict"] == "REJECT"
       and any(x.startswith("state:owner_match") for x in result["reasons"]),
       result["reasons"])

    state_todo = {"tasks": {"T20": {"owner": "W20", "status": "todo"}}}
    result = validate_receipt(good, state=state_todo, root=tmp)
    ok("状态缓冲: 声称 PASS 而 state.json 仍 todo → 拒收",
       result["verdict"] == "REJECT"
       and any(x.startswith("state:status_match") for x in result["reasons"]),
       result["reasons"])

    # 4 安全缓冲 -------------------------------------------------
    writes = dict(good)
    writes["writes"] = [str(tmp / "constitution.json")]
    result = validate_receipt(writes, state=state_ok, root=tmp, actor="DSH",
                              event_log=log)
    ok("验收④ 回执声明写宪法 → 拒收",
       result["verdict"] == "REJECT"
       and any(x.startswith("safe:no_protected_write")
               for x in result["reasons"]), result["reasons"])

    (tmp / "constitution.json").write_text("{}", encoding="utf-8")
    (tmp / "progress").mkdir(parents=True, exist_ok=True)
    (tmp / "progress" / "approvals.jsonl").write_text("", encoding="utf-8")

    g1 = guard_write(tmp / "constitution.json", "DSH", root=tmp, log_path=log)
    ok("验收④ DSH 直写宪法 → 拒收",
       g1["allowed"] is False and g1["reason"] == "PROTECTED_FOR_DSH", g1)

    g2 = guard_write("progress/approvals.jsonl", "DSH", root=tmp,
                     log_path=log)
    ok("验收④ DSH 直写审批 → 拒收",
       g2["allowed"] is False, g2)

    g3 = guard_write("ops/bus/tasks/T20.md", "DSH", root=tmp, log_path=log)
    ok("验收④ DSH 直写任务卡 → 拒收", g3["allowed"] is False, g3)

    rows = []
    if log.is_file():
        rows = [json.loads(x) for x in
                log.read_text(encoding="utf-8").splitlines() if x.strip()]
    ok("验收④ 拒收事件已落盘",
       sum(1 for r in rows if r.get("event") == "DSH_PROTECTED_WRITE_REJECTED")
       >= 3, "events=%d" % len(rows))

    g4 = guard_write("ops/buffer/out.txt", "DSH", root=tmp, log_path=log)
    ok("安全缓冲: 非保护路径放行", g4["allowed"] is True, g4)

    proposal = propose_change("ops/bus/state.json", action="set_status",
                              frm="todo", to="done", note="T20 完成",
                              evidence=str(artifact), actor="DSH", root=tmp,
                              proposal_dir=tmp / "proposals")
    ok("安全缓冲: 只能提案且不写目标",
       proposal["status"] == "PROPOSED"
       and Path(proposal["path"]).is_file()
       and not (tmp / "ops" / "bus" / "state.json").exists(),
       proposal.get("path", ""))

    total = len(checks)
    passed = sum(1 for c in checks if c["ok"])
    return {"checks": checks, "passed": passed, "total": total,
            "ok": passed == total, "tmp": str(tmp)}


def _print_checks(result):
    for item in result["checks"]:
        print("[%s] %s%s" % ("PASS" if item["ok"] else "FAIL",
                             item["check"],
                             ("  " + item["detail"]) if item["detail"] else ""))
    print("\n=== %d/%d PASS ===" % (result["passed"], result["total"]))
    return 0 if result["ok"] else 1


# ---------------------------------------------------------------- 报告
def build_report(self_result, facts=None, artifact_path=ARTIFACT):
    artifact_path = Path(artifact_path)
    artifact_sha = sha256_file(artifact_path)
    lines = []
    add = lines.append

    add("# T3 · DSH 缓冲层 校验报告")
    add("")
    add("- 生成时间: %s" % now_iso())
    add("- 生成器: `%s`" % ARTIFACT)
    add("- 产物: `%s`" % artifact_path)
    add("- 产物 sha256: `%s`" % artifact_sha)
    add("- 自检: **%d/%d PASS**" % (self_result["passed"],
                                    self_result["total"]))
    add("")
    add("## 一、结论")
    add("")
    if self_result["ok"]:
        add("四条链路已落地，%d 项自检全绿（级别 **L1 本地冒烟**）。"
            "四条验收均表现为“拒收”，不是“观察通过”。"
            % self_result["total"])
    else:
        add("自检未全绿，本报告不作为完成证据。")
    add("")
    if facts:
        add("| 对象 | 值 |")
        add("|---|---|")
        add("| 任务卡 | `%s`（%d 行 / 上限 %d，输入缓冲 %s） |"
            % (facts["card_path"], facts["card"]["lines"],
               facts["card"]["max_lines"],
               "PASS" if facts["card"]["ok"] else "REJECT"))
        add("| state.json | `%s`（本任务 status=%s） |"
            % (facts["state_path"], facts.get("state_status", "N/A")))
        add("")
        add("> 回执核验结果见 `ops/buffer/verify_T3.json` 与 `ops/bus/out/T3.json`。"
            "回执要绑定本报告 sha，故不能把回执结论写进本报告（避免自指）。")
        add("")

    add("## 二、四条链路")
    add("")
    add("| 链路 | 实现 | 触发的拒收码 |")
    add("|---|---|---|")
    add("| 1 输入缓冲 | `read_task_card()` / `handoff_to_dsh()` | "
        "`CARD_TOO_LONG`、`CARD_CARRIES_HISTORY`、`CARD_MISSING` |")
    add("| 2 输出缓冲 | `validate_receipt()` | "
        "`field:*`、`sha:*`、`claim:*`、`artifact:*` |")
    add("| 3 状态缓冲 | `validate_receipt()` + `owner_duplicates()` | "
        "`state:owner_unique`、`state:owner_match`、`state:status_match` |")
    add("| 4 安全缓冲 | `guard_write()` / `propose_change()` | "
        "`PROTECTED_FOR_DSH`、`safe:no_protected_write` |")
    add("")
    add("关键设计：`status` 只表示“本次产物可验”，不表示“任务已入账”。"
        "对 state.json 的声明必须单列 `state_claim` 并接受比对——"
        "避免“自述完成”直接冒充当板状态（NEG-A11 / NEG-J01）。")
    add("")

    add("## 三、验收四条（机器可判）")
    add("")
    add("| 验收 | 结果 | 自检项 |")
    add("|---|---|---|")
    wanted = ("验收①", "验收②", "验收③", "验收④")
    grouped = {w: [] for w in wanted}
    for item in self_result["checks"]:
        for w in wanted:
            if item["check"].startswith(w):
                grouped[w].append(item)
    labels = {
        "验收①": "伪造“已完成” → 拒收",
        "验收②": "sha 不符 → 拒收",
        "验收③": "同一任务两个 owner → 拒收",
        "验收④": "DSH 直写宪法/审批 → 拒收并记事件",
    }
    for w in wanted:
        items = grouped[w]
        good = bool(items) and all(i["ok"] for i in items)
        add("| %s %s | **%s** | %d 项 |"
            % (w, labels[w], "PASS" if good else "FAIL", len(items)))
    add("")

    add("## 四、自检明细")
    add("")
    add("| # | 检查 | 结果 | 证据 |")
    add("|---|---|---|---|")
    for index, item in enumerate(self_result["checks"], 1):
        add("| %d | %s | %s | `%s` |"
            % (index, item["check"],
               "PASS" if item["ok"] else "FAIL",
               item["detail"].replace("|", "/")[:120]))
    add("")

    add("## 五、未验证 / 开放项")
    add("")
    add("1. **state.json 未改动**：本窗口不写 `ops/bus/state.json`（那是 W0 的账）。"
        "T3 仍为 `todo`，推进提案已落 `ops/buffer/proposals/`，需 W0 或人写入。")
    add("2. **T3 任务卡 21 行 > 20 行**：输入缓冲按卡会拒收（本卡自身超限）。"
        "已作为输入侧缺陷记录，未改卡；请 W0 修剪到 ≤20 行。")
    add("3. **未接真实 DSH 会话**：本层是库+CLI，DSH 侧尚未强制走 `handoff_to_dsh()`。"
        "接入点与拒绝码已固定，联调属 UNVERIFIED。")
    add("4. **未改 DSH 配置**：按卡禁止，只提供调用入口。")
    add("")
    add("## 六、可推翻条件")
    add("")
    add("- `python ops\\bus\\check_handoff.py` 非 0；")
    add("- `python ops\\buffer\\dsh_buffer.py --self-test` 非 %d/%d；"
        % (self_result["total"], self_result["total"]))
    add("- 任一验收用例被放行（伪造完成 / sha 不符 / 双 owner / 直写受保护对象）；")
    add("- 产物 sha256 与回执不一致。")
    add("")
    add("## 七、复现")
    add("")
    add("```bat")
    add("python ops\\buffer\\dsh_buffer.py --self-test")
    add("python ops\\buffer\\dsh_buffer.py --report")
    add("python ops\\buffer\\dsh_buffer.py --verify T3 --out ops\\buffer\\verify_T3.json")
    add("python ops\\bus\\check_handoff.py")
    add("```")
    add("")
    return "\n".join(lines)


def write_report(path=None, task_id="T3"):
    result = self_test()
    target = Path(path or REPORT_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    card_path = BUS / "tasks" / ("%s.md" % task_id)
    card = read_task_card(card_path)
    state_path = BUS / "state.json"
    state_status = "N/A"
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state_status = ((state.get("tasks") or {}).get(task_id) or {}).get(
                "status", "N/A")
        except Exception:  # noqa: BLE001
            state_status = "PARSE_ERROR"
    facts = {"card_path": str(card_path),
             "card": {"lines": card["lines"],
                      "max_lines": card["max_lines"],
                      "ok": card["ok"],
                      "reasons": card["reasons"]},
             "state_path": str(state_path),
             "state_status": state_status}
    text = build_report(result, facts)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(target)
    return {"status": "WRITTEN", "path": str(target),
            "sha": sha256_file(target), "self_test": {
                "passed": result["passed"], "total": result["total"]}}


# ---------------------------------------------------------------- CLI
def main():
    parser = argparse.ArgumentParser(description="DSH 四段缓冲层（T3）")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--verify", metavar="TASK_ID")
    parser.add_argument("--out", default="")
    parser.add_argument("--report", nargs="?", const=str(REPORT_PATH))
    parser.add_argument("--guard-write", metavar="PATH")
    parser.add_argument("--propose", metavar="TARGET")
    parser.add_argument("--actor", default="DSH")
    parser.add_argument("--action", default="modify")
    parser.add_argument("--from", dest="frm", default="")
    parser.add_argument("--to", dest="to", default="")
    parser.add_argument("--note", default="")
    parser.add_argument("--evidence", default="")
    args = parser.parse_args()

    if args.self_test:
        return _print_checks(self_test())

    if args.guard_write:
        result = guard_write(args.guard_write, args.actor)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["allowed"] else 2

    if args.propose:
        result = propose_change(args.propose, action=args.action,
                                frm=args.frm, to=args.to, note=args.note,
                                evidence=args.evidence, actor=args.actor)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "PROPOSED" else 2

    if args.report is not None:
        result = write_report(args.report)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.verify:
        result = verify(args.verify)
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2)
                           + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["verdict"] == "ACCEPT" else 2

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
