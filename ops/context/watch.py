#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""T13 · 上下文巡检 + 资产保护钩子

只读扫描会话用量、ops/bus、reports/cases、data；超过阈值时生成
handoff.md、带 sha 的资产清单与可恢复快照。

硬约束：
  - 不自动删除任何文件
  - 不自动压缩任何文件
  - 不读取、不复制、不哈希疑似密钥文件（.env / secret / vault / token ...）

常用：
  python ops\\context\\watch.py --check
  python ops\\context\\watch.py --check --strict --json
  python ops\\context\\watch.py --simulate
  python ops\\context\\watch.py --verify-snapshot ops\\context\\snapshots\\snap-xxx
  python ops\\context\\watch.py --restore ops\\context\\snapshots\\snap-xxx
  python ops\\context\\watch.py --self-test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve()
CTX_DIR = HERE.parent
ROOT = CTX_DIR.parents[1]

COPY_LIMIT = 1 << 20          # 单文件超过 1 MiB 只记 sha，不复制
MAX_WALK_FILES = 50000
TIMEOUT_SECONDS = 20.0       # 巡检软截止，避免阻塞对话

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "snapshots", "restored", "handoffs", "dist", "build", ".idea",
}
SENSITIVE_MARKERS = (
    "secret", "password", "passwd", "vault", "credential", "token",
    "id_rsa", "private_key", "apikey", "api_key", "cookie", ".pem",
    ".pfx", ".p12", ".kdbx",
)
SENSITIVE_SUFFIX = (".key", ".pem", ".pfx", ".p12", ".kdbx")
RECEIPT_RE = re.compile(r"^T\d+\.json$")

DEFAULT_LIMITS = {
    "context_bytes": 262144,
    "data_bytes": 33554432,
    "cases_files": 200,
    "bus_todo": 8,
    "session_tokens_est": 200000,
    "out_receipts_without_rows": 0,
}

METRIC_LABELS = {
    "context_bytes": "上下文目录字节",
    "data_bytes": "data 目录字节",
    "cases_files": "案例文件数",
    "bus_todo": "总线未完成任务数",
    "session_tokens_est": "会话 token 估算（仅本地账本）",
    "out_receipts_without_rows": "缺 rows 的回执数",
}


# ---------------------------------------------------------------- 基础工具
def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def unique_path(base: Path, name: str, suffix: str = "") -> Path:
    """同名不覆盖：追加 -2/-3，绝不删除已有文件。"""
    p = base / name
    if not p.exists():
        return p
    i = 2
    while True:
        q = base / ("%s-%d%s" % (name, i, suffix))
        if not q.exists():
            return q
        i += 1


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def is_sensitive(name: str) -> bool:
    low = name.lower()
    if low == ".env" or low.startswith(".env."):
        return True
    if low.endswith(SENSITIVE_SUFFIX):
        return True
    return any(m in low for m in SENSITIVE_MARKERS)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def safe_size(path: Path) -> int:
    try:
        return int(path.stat().st_size)
    except OSError:
        return 0


def walk_files(base: Path, deadline: Optional[float] = None) -> List[Path]:
    """只读遍历；跳过敏感文件名/目录；不跟随符号链接。"""
    out: List[Path] = []
    if not base.exists():
        return out
    for dirpath, dirnames, filenames in os.walk(str(base)):
        if deadline is not None and time.monotonic() > deadline:
            break
        dirnames[:] = sorted(d for d in dirnames if d.lower() not in SKIP_DIRS)
        for fn in sorted(filenames):
            if is_sensitive(fn):
                continue
            p = Path(dirpath) / fn
            try:
                if p.is_symlink() or not p.is_file():
                    continue
            except OSError:
                continue
            out.append(p)
            if len(out) >= MAX_WALK_FILES:
                return out
    return out


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 指标
def load_limits(root: Path) -> Dict[str, float]:
    limits = dict(DEFAULT_LIMITS)
    p = root / "ops" / "context" / "thresholds.json"
    data = load_json(p, {})
    if isinstance(data, dict):
        for k, v in data.items():
            if k in limits and isinstance(v, (int, float)) and not isinstance(v, bool):
                limits[k] = v
    return limits


def compute_metrics(root: Path) -> Dict[str, Any]:
    t0 = time.monotonic()
    deadline = t0 + TIMEOUT_SECONDS

    context_files = walk_files(root / ".context", deadline)
    context_bytes = sum(safe_size(p) for p in context_files)

    data_files = walk_files(root / "data", deadline)
    data_bytes = sum(safe_size(p) for p in data_files)

    case_files = walk_files(root / "reports" / "cases", deadline)

    state = load_json(root / "ops" / "bus" / "state.json", {}) or {}
    tasks = state.get("tasks", {}) if isinstance(state, dict) else {}
    todo = 0
    for t in tasks.values():
        if isinstance(t, dict) and str(t.get("status", "")).lower() in ("todo", "doing", "in_progress", "running"):
            todo += 1

    out_dir = root / "ops" / "bus" / "out"
    receipts = sorted(p for p in out_dir.glob("T*.json") if RECEIPT_RE.match(p.name)) if out_dir.exists() else []
    missing_rows = 0
    for rp in receipts:
        d = load_json(rp, {})
        rows = d.get("rows") if isinstance(d, dict) else None
        if isinstance(rows, bool) or not isinstance(rows, int) or rows <= 0:
            missing_rows += 1

    usage = load_json(root / "data" / "usage_counters.json", {}) or {}
    session_launches = usage.get("launch", 0) if isinstance(usage, dict) else 0
    try:
        session_launches = int(session_launches or 0)
    except (TypeError, ValueError):
        session_launches = 0

    in_tok = out_tok = usage_lines = 0
    logp = root / "data" / "usage_log.jsonl"
    if logp.exists():
        try:
            with logp.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if not line.strip():
                        continue
                    usage_lines += 1
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    if isinstance(row, dict):
                        try:
                            in_tok += int(row.get("in", 0) or 0)
                            out_tok += int(row.get("out", 0) or 0)
                        except (TypeError, ValueError):
                            pass
        except OSError:
            pass

    metrics = {
        "context_bytes": context_bytes,
        "data_bytes": data_bytes,
        "cases_files": len(case_files),
        "bus_todo": todo,
        "session_tokens_est": in_tok + out_tok + context_bytes // 4,
        "out_receipts_without_rows": missing_rows,
        "context_files": len(context_files),
        "data_files": len(data_files),
        "out_receipts": len(receipts),
        "session_launches": session_launches,
        "usage_log_lines": usage_lines,
        "scan_seconds": round(time.monotonic() - t0, 3),
    }
    return metrics


def evaluate(metrics: Dict[str, Any], limits: Dict[str, float]) -> List[Dict[str, Any]]:
    breaches: List[Dict[str, Any]] = []
    for key, limit in limits.items():
        actual = metrics.get(key)
        if actual is None:
            continue
        try:
            if float(actual) > float(limit):
                breaches.append({
                    "key": key,
                    "label": METRIC_LABELS.get(key, key),
                    "actual": actual,
                    "limit": limit,
                    "over_by": round(float(actual) - float(limit), 3),
                })
        except (TypeError, ValueError):
            continue
    return breaches


# ---------------------------------------------------------------- 资产清单与快照
def collect_assets(root: Path) -> List[Path]:
    files: List[Path] = []
    seen = set()

    def add(p: Path) -> None:
        try:
            if not p.is_file() or p.is_symlink() or is_sensitive(p.name):
                return
            r = str(p.resolve())
        except OSError:
            return
        if r not in seen:
            seen.add(r)
            files.append(p)

    globs = [
        (root / ".context", "**/*"),
        (root / "ops" / "bus" / "tasks", "*.md"),
        (root / "ops" / "bus" / "out", "*.json"),
        (root / "reports" / "cases", "**/*"),
        (root / "data", "*.json"),
        (root / "data", "*.jsonl"),
    ]
    for base, pattern in globs:
        if base.exists():
            for p in base.glob(pattern):
                add(p)

    for single in (
        root / "ops" / "bus" / "state.json",
        root / "AGENTS.md",
        root / "constitution.json",
        root / "ops" / "context" / "watch.py",
    ):
        add(single)

    files.sort(key=lambda p: rel(p, root))
    return files


def asset_manifest(root: Path, assets: Iterable[Path]) -> Dict[str, Any]:
    rows = []
    for p in assets:
        try:
            st = p.stat()
            rows.append({
                "path": rel(p, root),
                "sha256": sha256_file(p),
                "size": int(st.st_size),
                "mtime": datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec="seconds"),
            })
        except OSError:
            continue
    return {
        "task_id": "T13",
        "generated_at": now_iso(),
        "root": str(root),
        "count": len(rows),
        "policy": "只读扫描；跳过 .env/secret/vault/token 等敏感文件；不删除、不压缩；sha256 用于校验与恢复",
        "assets": rows,
    }


def write_assets_manifest(root: Path, manifest: Dict[str, Any], path: Optional[Path] = None) -> Path:
    path = path or (root / "ops" / "context" / "assets_sha.json")
    write_json(path, manifest)
    return path


def write_snapshot(root: Path, metrics: Dict[str, Any], breaches: List[Dict[str, Any]],
                   manifest: Dict[str, Any], trigger: str) -> Path:
    snap_root = root / "ops" / "context" / "snapshots"
    snap_root.mkdir(parents=True, exist_ok=True)
    snapdir = unique_path(snap_root, "snap-" + stamp())
    snapdir.mkdir(parents=True, exist_ok=False)
    files_dir = snapdir / "files"

    copied = 0
    entries = []
    for row in manifest.get("assets", []):
        relp = row["path"]
        src = root / relp
        entry = dict(row)
        entry["copied"] = False
        if row.get("size", 0) <= COPY_LIMIT:
            dst = files_dir / relp
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(dst))
                actual = sha256_file(dst)
                if actual == row["sha256"]:
                    entry["copied"] = True
                    entry["snapshot_path"] = "files/" + relp
                    copied += 1
                else:
                    entry["copy_error"] = "sha 不一致，已保留副本但不计入可恢复"
            except OSError as e:
                entry["copy_error"] = "%s: %s" % (type(e).__name__, e)
        entries.append(entry)

    data = {
        "task_id": "T13",
        "snapshot_id": snapdir.name,
        "created_at": now_iso(),
        "trigger": trigger,
        "root": str(root),
        "policy": "不删除、不压缩；>1MiB 资产只记 sha；敏感文件不进入快照",
        "metrics": metrics,
        "breaches": breaches,
        "copied_files": copied,
        "assets": entries,
        "restore": {
            "default_dest": "ops/context/restored/" + snapdir.name,
            "command": "python ops\\context\\watch.py --restore %s" % rel(snapdir, root),
            "note": "恢复到新目录；目标已存在且 sha 不同则拒绝覆盖（需 --force），绝不删除原文件",
        },
    }
    write_json(snapdir / "manifest.json", data)
    return snapdir


def verify_snapshot(snapdir: Path) -> Dict[str, Any]:
    res = {"snapshot": str(snapdir), "ok": False, "checked": 0, "errors": []}
    manp = snapdir / "manifest.json"
    data = load_json(manp, None)
    if not isinstance(data, dict):
        res["errors"].append("manifest.json 缺失或不可解析")
        return res

    for row in data.get("assets", []):
        if not row.get("copied"):
            continue
        relp = row.get("snapshot_path") or ("files/" + str(row.get("path")))
        p = snapdir / relp
        res["checked"] += 1
        if not p.exists():
            res["errors"].append("快照缺失: %s" % relp)
            continue
        actual = sha256_file(p)
        if actual != row.get("sha256"):
            res["errors"].append("sha 不符: %s" % relp)

    res["ok"] = not res["errors"]
    return res


def restore_snapshot(snapdir: Path, dest: Path, force: bool = False) -> Dict[str, Any]:
    ver = verify_snapshot(snapdir)
    if not ver["ok"]:
        return {"ok": False, "errors": ver["errors"], "restored": 0, "dest": str(dest)}

    data = load_json(snapdir / "manifest.json", {}) or {}
    restored = skipped = 0
    errors: List[str] = []
    for row in data.get("assets", []):
        if not row.get("copied"):
            continue
        relp = row.get("snapshot_path") or ("files/" + str(row.get("path")))
        src = snapdir / relp
        target = dest / str(row["path"])
        if target.exists():
            if target.is_file() and sha256_file(target) == row["sha256"]:
                skipped += 1
                continue
            if not force:
                errors.append("目标已存在且 sha 不同，拒绝覆盖: %s" % target)
                continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(target))
        if sha256_file(target) != row["sha256"]:
            errors.append("恢复后 sha 不符: %s" % target)
        else:
            restored += 1

    report = {
        "ok": not errors,
        "snapshot": str(snapdir),
        "dest": str(dest),
        "restored": restored,
        "skipped_same_sha": skipped,
        "errors": errors,
        "restored_at": now_iso(),
        "policy": "只复制到新目录；未删除任何原文件",
    }
    if dest.exists():
        write_json(dest / "restore_report.json", report)
    return report


# ---------------------------------------------------------------- 交接文档
def render_handoff(root: Path, result: Dict[str, Any]) -> str:
    metrics = result["metrics"]
    breaches = result["breaches"]
    limits = result["limits"]
    trigger = result["trigger"]
    state = load_json(root / "ops" / "bus" / "state.json", {}) or {}
    tasks = state.get("tasks", {}) if isinstance(state, dict) else {}
    todo_rows = []
    for tid, t in sorted(tasks.items()):
        if isinstance(t, dict) and str(t.get("status", "")).lower() in ("todo", "doing", "in_progress", "running"):
            todo_rows.append((tid, t.get("owner", "-"), t.get("status", "-")))

    lines: List[str] = []
    lines.append("# T13 · 上下文交接（handoff）")
    lines.append("")
    lines.append("- 生成时间: %s" % result["generated_at"])
    lines.append("- 触发: %s" % trigger)
    lines.append("- 结论: %s" % ("超过阈值，需要交接 %d 项" % len(breaches) if breaches else "未超阈值，仅刷新资产清单"))
    lines.append("- 巡检耗时: %ss（软截止 %ss，不阻塞对话）" % (metrics.get("scan_seconds"), TIMEOUT_SECONDS))
    lines.append("")
    lines.append("## 1. 指标与阈值")
    lines.append("")
    lines.append("| 指标 | 实际 | 阈值 | 状态 |")
    lines.append("|---|---:|---:|---|")
    over_keys = {b["key"] for b in breaches}
    for key, limit in limits.items():
        actual = metrics.get(key)
        status = "**超限**" if key in over_keys else "OK"
        lines.append("| %s (`%s`) | %s | %s | %s |" % (
            METRIC_LABELS.get(key, key), key, actual, limit, status))
    lines.append("")
    if breaches:
        lines.append("### 超限明细")
        lines.append("")
        for b in breaches:
            lines.append("- **%s**: 实际 %s > 阈值 %s（超出 %s）" % (
                b["label"], b["actual"], b["limit"], b["over_by"]))
        lines.append("")
    lines.append("## 2. 提炼（只保留可执行部分）")
    lines.append("")
    lines.append("- 上下文目录 %s 个文件 / %s 字节；data %s 个文件 / %s 字节。" % (
        metrics.get("context_files"), metrics.get("context_bytes"),
        metrics.get("data_files"), metrics.get("data_bytes")))
    lines.append("- 回执 %s 份，缺 rows %s 份；总线未完成 %s 个。" % (
        metrics.get("out_receipts"), metrics.get("out_receipts_without_rows"),
        metrics.get("bus_todo")))
    lines.append("- 会话 token 估算 %s（来自本地 usage 账本，未调用模型）。" % (
        metrics.get("session_tokens_est")))
    lines.append("- 资产 sha 清单: `%s`（%s 项）。" % (
        result.get("assets_path") or "ops/context/assets_sha.json", result.get("assets_count", 0)))
    if result.get("snapshot"):
        lines.append("- 快照: `%s`（复制 %s 个可恢复文件，大文件只记 sha）。" % (
            result["snapshot"], result.get("copied_files", 0)))
        lines.append("- 恢复: `python ops\\context\\watch.py --restore %s`（恢复到新目录，不覆盖原文件）。" % result["snapshot"])
    lines.append("")
    lines.append("## 3. 任务交接")
    lines.append("")
    if todo_rows:
        lines.append("| 任务 | owner | 状态 |")
        lines.append("|---|---|---|")
        for tid, owner, status in todo_rows[:30]:
            lines.append("| %s | %s | %s |" % (tid, owner, status))
        if len(todo_rows) > 30:
            lines.append("")
            lines.append("（另有 %d 个未完成任务，见 state.json）" % (len(todo_rows) - 30))
    else:
        lines.append("总线无未完成任务。")
    lines.append("")
    lines.append("## 4. 下一步（最多 3 条）")
    lines.append("")
    actions = [
        "先处理超限项中最接近业务风险的一项；未超限项保持观察。",
        "把本文件指针交给下一窗口：只传路径 + sha，不复制全文。",
        "若快照校验失败，先人工比对 `assets_sha.json`，不要自动覆盖或删除。",
    ]
    for i, a in enumerate(actions, 1):
        lines.append("%d. %s" % (i, a))
    lines.append("")
    lines.append("## 5. 合规声明")
    lines.append("")
    lines.append("- 未删除任何文件；未自动压缩；未写回 `ops/bus/state.json`。")
    lines.append("- 未读取或复制 `.env`、`secret`、`vault`、`token`、`*.key` 等敏感文件。")
    lines.append("- 巡检为本地只读扫描，不调用外部模型/网络；有软截止，不阻塞对话。")
    lines.append("- 可推翻条件: 若 `assets_sha.json` 与快照校验不一致，或 `--self-test` 少于全部通过，则本交接结论作废。")
    lines.append("")
    return "\n".join(lines)


def write_handoff(root: Path, result: Dict[str, Any]) -> Path:
    ctx = root / "ops" / "context"
    ctx.mkdir(parents=True, exist_ok=True)
    text = render_handoff(root, result)
    canonical = ctx / "handoff.md"
    canonical.write_text(text, encoding="utf-8")
    arch_dir = ctx / "handoffs"
    arch_dir.mkdir(parents=True, exist_ok=True)
    arch = unique_path(arch_dir, "handoff-" + stamp(), ".md")
    arch.write_text(text, encoding="utf-8")
    return canonical


# ---------------------------------------------------------------- 主流程
def run_check(root: Path, simulate: bool = False, write: bool = True,
              limits: Optional[Dict[str, float]] = None,
              trigger: Optional[str] = None) -> Dict[str, Any]:
    t0 = time.monotonic()
    metrics = compute_metrics(root)
    limits = dict(limits or load_limits(root))
    if simulate:
        # 强制所有指标越线，用于验收演练；不改真实阈值文件。
        limits = {k: -1 for k in limits}

    breaches = evaluate(metrics, limits)
    result: Dict[str, Any] = {
        "task_id": "T13",
        "generated_at": now_iso(),
        "trigger": trigger or ("模拟超阈值" if simulate else "定时巡检"),
        "simulated": bool(simulate),
        "metrics": metrics,
        "limits": limits,
        "breaches": breaches,
        "handoff": None,
        "snapshot": None,
        "assets_path": None,
        "assets_count": 0,
        "copied_files": 0,
    }

    if not write:
        result["elapsed_seconds"] = round(time.monotonic() - t0, 3)
        return result

    assets = collect_assets(root)
    manifest = asset_manifest(root, assets)
    assets_path = write_assets_manifest(root, manifest)
    result["assets_path"] = rel(assets_path, root)
    result["assets_count"] = manifest["count"]
    result["asset_manifest"] = manifest

    if breaches:
        snap = write_snapshot(root, metrics, breaches, manifest, result["trigger"])
        snap_manifest = load_json(snap / "manifest.json", {}) or {}
        result["snapshot"] = rel(snap, root)
        result["copied_files"] = int(snap_manifest.get("copied_files", 0) or 0)
        result["handoff"] = rel(write_handoff(root, result), root)

    result["elapsed_seconds"] = round(time.monotonic() - t0, 3)
    return result


def cmd_self_test() -> int:
    checks: List[Tuple[str, bool, str]] = []

    def check(name: str, cond: bool, detail: Any = "") -> None:
        checks.append((name, bool(cond), "" if cond else str(detail)[:300]))

    def build_root(with_handoff_target: bool = True) -> Path:
        import tempfile
        root = Path(tempfile.mkdtemp(prefix="t13_watch_"))
        (root / ".context").mkdir(parents=True)
        (root / ".context" / "LESSONS.md").write_text("# 教训\n不要删资产\n", encoding="utf-8")
        (root / "ops" / "bus" / "tasks").mkdir(parents=True)
        (root / "ops" / "bus" / "tasks" / "T1.md").write_text("# T1\n", encoding="utf-8")
        (root / "ops" / "bus" / "out").mkdir(parents=True)
        (root / "ops" / "bus" / "out" / "T1.json").write_text(
            json.dumps({"task_id": "T1", "owner": "W1", "status": "PASS", "artifact": "x",
                        "sha": "0" * 16, "rows": 3}, ensure_ascii=False), encoding="utf-8")
        state = {"tasks": {
            "T%d" % i: {"owner": "W%d" % i, "status": "todo"} for i in range(1, 10)
        }}
        (root / "ops" / "bus" / "state.json").write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8")
        (root / "reports" / "cases").mkdir(parents=True)
        (root / "reports" / "cases" / "c1.md").write_text("case\n", encoding="utf-8")
        (root / "data").mkdir(parents=True)
        (root / "data" / "a.json").write_text('{"ok": true}\n', encoding="utf-8")
        (root / "data" / "usage_counters.json").write_text('{"launch": 3}\n', encoding="utf-8")
        (root / "data" / "usage_log.jsonl").write_text(
            '{"in": 10, "out": 5}\n', encoding="utf-8")
        (root / "data" / "secrets.vault").write_text("TOPSECRET-DO-NOT-TOUCH\n", encoding="utf-8")
        (root / ".env").write_text("API_KEY=TOPSECRET-DO-NOT-TOUCH\n", encoding="utf-8")
        (root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
        (root / "ops" / "context").mkdir(parents=True)
        (root / "ops" / "context" / "watch.py").write_text("# copy\n", encoding="utf-8")
        if with_handoff_target:
            (root / "ops" / "context" / "handoff.md").unlink(missing_ok=True)
        return root

    t_start = time.monotonic()
    root = build_root()
    try:
        before_sha = {}
        for p in (root / ".context").rglob("*"):
            if p.is_file():
                before_sha[rel(p, root)] = sha256_file(p)
        for p in (root / "data").rglob("*"):
            if p.is_file() and not is_sensitive(p.name):
                before_sha[rel(p, root)] = sha256_file(p)

        # 1) 扫描基础指标
        m = compute_metrics(root)
        check("扫描出案例数与总线待办", m["cases_files"] == 1 and m["bus_todo"] == 9, m)

        # 2) 低于阈值不触发
        high = {k: 10 ** 12 for k in DEFAULT_LIMITS}
        r_ok = run_check(root, write=True, limits=high, trigger="自检-未超限")
        check("未超阈值不生成 handoff", r_ok["breaches"] == [] and not (root / "ops" / "context" / "handoff.md").exists(), r_ok)

        # 3) 模拟超阈值触发
        r_sim = run_check(root, simulate=True, write=True)
        check("模拟超阈值触发交接", len(r_sim["breaches"]) == len(DEFAULT_LIMITS) and r_sim["handoff"], r_sim["breaches"])

        # 4) handoff 存在且包含提炼/合规
        hp = root / "ops" / "context" / "handoff.md"
        htext = hp.read_text(encoding="utf-8") if hp.exists() else ""
        check("handoff.md 存在且含关键段落",
              hp.exists() and "提炼" in htext and "不阻塞对话" in htext and "未删除" in htext, htext[:120])

        # 5) 资产 sha 清单
        ap = root / "ops" / "context" / "assets_sha.json"
        am = load_json(ap, {})
        check("assets_sha.json 有 sha 清单", ap.exists() and am.get("count", 0) >= 5, am.get("count"))

        # 6) 快照存在且有 manifest
        snap = root / r_sim["snapshot"] if r_sim.get("snapshot") else None
        check("快照 manifest 存在", bool(snap) and (snap / "manifest.json").exists(), r_sim.get("snapshot"))

        # 7) 快照可校验
        ver = verify_snapshot(snap) if snap else {"ok": False, "errors": ["无快照"]}
        check("快照 sha 校验通过", ver.get("ok") and ver.get("checked", 0) > 0, ver)

        # 8) 快照可恢复
        dest = root / "restored_test"
        rep = restore_snapshot(snap, dest) if snap else {"ok": False, "errors": ["无快照"]}
        check("快照可恢复且恢复后 sha 一致", rep.get("ok") and rep.get("restored", 0) > 0, rep)

        # 9) 敏感文件未被收集/哈希/复制
        paths = [a["path"] for a in am.get("assets", [])]
        joined = "\n".join(paths)
        snap_blob = ""
        if snap:
            snap_blob = (snap / "manifest.json").read_text(encoding="utf-8", errors="replace")
        check("敏感文件被排除",
              "secrets.vault" not in joined and ".env" not in joined
              and "TOPSECRET" not in htext and "TOPSECRET" not in snap_blob, joined)

        # 10) 不删除、不改源文件
        after = {}
        for p in (root / ".context").rglob("*"):
            if p.is_file():
                after[rel(p, root)] = sha256_file(p)
        for p in (root / "data").rglob("*"):
            if p.is_file() and not is_sensitive(p.name):
                after[rel(p, root)] = sha256_file(p)
        check("未删除/未修改源资产", all(after.get(k) == v for k, v in before_sha.items()), before_sha)

        # 11) 不自动压缩
        archives = []
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".zip", ".gz", ".7z", ".rar", ".tar", ".bz2", ".xz"):
                archives.append(rel(p, root))
        check("未生成压缩包", not archives, archives)

        # 12) 篡改检测
        tamper_ok = False
        if snap:
            tamper = root / "tamper_copy"
            shutil.copytree(str(snap), str(tamper))
            copied = [a for a in load_json(tamper / "manifest.json", {}).get("assets", []) if a.get("copied")]
            if copied:
                victim = tamper / copied[0]["snapshot_path"]
                victim.write_text("tampered", encoding="utf-8")
                tamper_ok = not verify_snapshot(tamper)["ok"]
        check("篡改快照能被识别", tamper_ok, "verify 仍通过")

        # 13) 缺 rows 能计数
        (root / "ops" / "bus" / "out" / "T2.json").write_text(
            json.dumps({"task_id": "T2", "owner": "W2"}, ensure_ascii=False), encoding="utf-8")
        m2 = compute_metrics(root)
        check("缺 rows 回执被计数", m2["out_receipts_without_rows"] >= 1, m2)

        # 14) 软截止/非阻塞
        elapsed = time.monotonic() - t_start
        check("巡检耗时低于 20s 软截止", elapsed < 20.0, elapsed)
    finally:
        # 仅清理自检临时目录，不触碰业务目录
        shutil.rmtree(str(root), ignore_errors=True)

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else " :: %s" % detail))
    print("self_test %d/%d" % (passed, len(checks)))
    return 0 if passed == len(checks) else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="T13 上下文巡检 + 资产保护钩子（只读、不删、不压缩）")
    ap.add_argument("--check", action="store_true", help="巡检并刷新资产清单；超阈值时生成 handoff.md + 快照")
    ap.add_argument("--simulate", action="store_true", help="模拟所有指标超阈值，演练交接（不改真实阈值）")
    ap.add_argument("--dry-run", action="store_true", help="只计算，不写任何文件")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--strict", action="store_true", help="超阈值时返回退出码 2（默认始终 0，避免阻塞调度）")
    ap.add_argument("--verify-snapshot", metavar="DIR", help="校验快照 sha")
    ap.add_argument("--restore", metavar="DIR", help="把快照恢复到新目录")
    ap.add_argument("--dest", metavar="DIR", help="恢复目标目录（默认 ops/context/restored/<snapshot>）")
    ap.add_argument("--force", action="store_true", help="恢复时允许覆盖 sha 不同的目标文件")
    ap.add_argument("--list-snapshots", action="store_true", help="列出快照")
    ap.add_argument("--self-test", action="store_true", help="运行 14 项自检")
    args = ap.parse_args(argv)

    if args.self_test:
        return cmd_self_test()

    if args.verify_snapshot:
        res = verify_snapshot(Path(args.verify_snapshot))
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["ok"] else 1

    if args.restore:
        snap = Path(args.restore)
        dest = Path(args.dest) if args.dest else (CTX_DIR / "restored" / snap.name)
        res = restore_snapshot(snap, dest, force=args.force)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["ok"] else 1

    if args.list_snapshots:
        base = CTX_DIR / "snapshots"
        rows = []
        if base.exists():
            for d in sorted(base.glob("snap-*")):
                man = load_json(d / "manifest.json", {}) or {}
                rows.append({
                    "snapshot": d.name,
                    "created_at": man.get("created_at"),
                    "trigger": man.get("trigger"),
                    "breaches": len(man.get("breaches", [])),
                    "copied_files": man.get("copied_files", 0),
                })
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    if not (args.check or args.simulate):
        ap.print_help()
        return 0

    try:
        result = run_check(ROOT, simulate=args.simulate, write=not args.dry_run)
    except Exception as e:
        err = {"task_id": "T13", "ok": False, "error": "%s: %s" % (type(e).__name__, e), "generated_at": now_iso()}
        print(json.dumps(err, ensure_ascii=False, indent=2))
        return 0  # 巡检失败不阻塞对话；详情在输出里

    # 不把完整资产清单塞进终端，只给指针
    public = {k: v for k, v in result.items() if k != "asset_manifest"}
    if args.json:
        print(json.dumps(public, ensure_ascii=False, indent=2))
    else:
        print("T13 %s" % ("超阈值，已交接" if result["breaches"] else "未超阈值"))
        print("指标: %s" % json.dumps({k: result["metrics"].get(k) for k in DEFAULT_LIMITS}, ensure_ascii=False))
        if result["breaches"]:
            for b in result["breaches"]:
                print("  超限 %s: %s > %s" % (b["key"], b["actual"], b["limit"]))
        print("资产清单: %s (%s 项)" % (result.get("assets_path"), result.get("assets_count")))
        if result.get("handoff"):
            print("交接: %s" % result["handoff"])
            print("快照: %s (复制 %s 个)" % (result["snapshot"], result["copied_files"]))
        print("耗时: %ss" % result["elapsed_seconds"])

    if args.strict and result["breaches"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
