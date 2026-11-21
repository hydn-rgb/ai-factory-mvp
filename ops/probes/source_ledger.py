#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""source_ledger.py — 信源探针：可达性实测 + 量化评分

方法（可复核，不发明）：
  1) Admiralty / NATO AJP-2.1：来源可靠性 A-F × 信息可信度 1-6，两轴独立
     https://en.wikipedia.org/wiki/Admiralty_code
  2) 7 维价值模型：相关性/可靠性/时效/影响/新颖/交叉/可行动
     本脚本取其中 5 维做可计算子集：可靠性、可信度、时效、交叉、可行动
  3) 硬门槛：D/E 来源、可信度 4-6、未授权/非公开 => 只能当线索，不作证据

用法：
  python ops\probes\source_ledger.py --self-test
  python ops\probes\source_ledger.py --probe
  python ops\probes\source_ledger.py --probe --only pccz,sf-taobao
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTDIR = ROOT / "reports" / "sources"
REGISTRY = HERE / "sources.json"

REL = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.35, "E": 0.10, "F": 0.40}
CRED = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.35, 5: 0.10, 6: 0.40}
LEGAL_OK = ("public", "authorized", "public_readonly")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 "
      "AIFactorySourceProbe/1.0")


def score(rel, cred, age_days, half_life, independent, actionability, legal):
    """返回 0-100 分、等级、是否可作证据、各分项。"""
    relv = REL.get(str(rel).upper(), 0.40)
    try:
        credv = CRED.get(int(cred), 0.40)
    except (TypeError, ValueError):
        credv = 0.40
    half = max(float(half_life or 30), 1.0)
    fresh = 0.5 ** (max(float(age_days or 0), 0.0) / half)
    corr = min(max(int(independent or 0), 0) / 3.0, 1.0)
    act = max(0.0, min(float(actionability or 0), 1.0))
    raw = 100.0 * (0.35 * relv + 0.25 * credv + 0.15 * fresh +
                   0.15 * corr + 0.10 * act)

    gates = []
    if relv < 0.60:
        gates.append("来源 D/E：不作证据")
    if credv < 0.60:
        gates.append("可信度 4-6：不作证据")
    if str(legal) not in LEGAL_OK:
        gates.append("未授权/非公开：不作证据")
    eligible = not gates

    if not eligible:
        grade = "UNVERIFIED"
    elif relv >= 1.0 and credv >= 0.80:
        grade = "A"
    elif relv >= 0.80:
        grade = "B"
    else:
        grade = "C"

    tier = "P1" if raw >= 75 else "P2" if raw >= 60 else "P3" if raw >= 40 else "P4"
    return {
        "total": round(raw if eligible else 0.0, 1),
        "potential": round(raw, 1),
        "tier": tier,
        "grade": grade,
        "eligible": eligible,
        "gates": gates,
        "parts": {
            "reliability": round(relv, 2),
            "credibility": round(credv, 2),
            "freshness": round(fresh, 2),
            "corroboration": round(corr, 2),
            "actionability": round(act, 2),
        },
    }


def probe(url, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Range": "bytes=0-131071",
    })
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(131072)
            return {
                "ok": True,
                "status": getattr(r, "status", None),
                "final_url": r.geturl(),
                "content_type": r.headers.get("content-type", ""),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "elapsed_ms": int((time.time() - t0) * 1000),
                "error": None,
            }
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read(8192)
        except Exception:
            pass
        return {
            "ok": False, "status": e.code, "final_url": url,
            "content_type": e.headers.get("content-type", "") if e.headers else "",
            "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
            "elapsed_ms": int((time.time() - t0) * 1000),
            "error": "HTTP %s" % e.code,
        }
    except Exception as e:
        return {
            "ok": False, "status": None, "final_url": url, "content_type": "",
            "bytes": 0, "sha256": "", "elapsed_ms": int((time.time() - t0) * 1000),
            "error": "%s: %s" % (type(e).__name__, str(e)[:180]),
        }


def run_probe(registry, only=None, timeout=15):
    rows = []
    for src in registry:
        if only and src["id"] not in only:
            continue
        p = probe(src["url"], timeout=timeout)
        age = 0.0
        if src.get("last_verified"):
            try:
                d = datetime.strptime(src["last_verified"], "%Y-%m-%d")
                age = max((datetime.now() - d).days, 0)
            except ValueError:
                age = 0.0
        s = score(src.get("reliability", "F"), src.get("credibility", 6),
                  age, src.get("half_life_days", 30),
                  src.get("independent", 1), src.get("actionability", 0.2),
                  src.get("legal", "public"))
        if not p["ok"]:
            s["grade"] = "UNVERIFIED"
            s["eligible"] = False
            s["total"] = 0.0
            s["gates"] = list(s["gates"]) + ["探测失败：不可达/被拦"]
        rows.append(dict(src=src, probe=p, score=s))
        print("%-16s %-6s %-9s %s" % (src["id"], p["status"] or "ERR", s["grade"],
                                       ("%.1f" % s["total"])))
    return rows


def write_outputs(rows):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "method": "Admiralty A-F x 1-6 + freshness + corroboration + actionability",
        "rows": rows,
    }
    jp = OUTDIR / ("probe_%s.json" % stamp)
    jp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = [
        "# 信源探针实测 %s" % payload["generated_at"],
        "",
        "评分 = 0.35×可靠性 + 0.25×可信度 + 0.15×时效 + 0.15×交叉 + 0.10×可行动。",
        "硬门槛：D/E、可信度 4-6、未授权 => `UNVERIFIED`，只能当线索，不作证据。",
        "",
        "| ID | 信源 | 层级 | HTTP | 分数 | 等级 | 可作证据 | 延迟ms | 备注 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        s, p, src = r["score"], r["probe"], r["src"]
        note = src.get("note", "")
        if s["gates"]:
            note = (note + "；" if note else "") + "；".join(s["gates"])
        score_txt = "%.1f" % s["total"] if s["eligible"] else "0（潜在 %.1f）" % s["potential"]
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %d | %s |" % (
            src["id"], src["name"].replace("|", "/"), src.get("layer", ""),
            p["status"] or "ERR", score_txt, s["grade"],
            "Y" if s["eligible"] else "N", p["elapsed_ms"],
            note.replace("|", "/")[:80]))
    lines += ["", "## 明细", ""]
    for r in rows:
        s, p, src = r["score"], r["probe"], r["src"]
        lines += [
            "### %s · %s" % (src["id"], src["name"]),
            "- URL: %s" % src["url"],
            "- 最终 URL: %s" % p.get("final_url"),
            "- HTTP: %s / %s bytes / %s ms / sha256 `%s`" % (
                p.get("status"), p.get("bytes"), p.get("elapsed_ms"), (p.get("sha256") or "")[:16]),
            "- 评分: %.1f (%s) / 等级 %s / 可作证据 %s / 潜在分 %.1f" % (
                s["total"], s["tier"], s["grade"], "Y" if s["eligible"] else "N", s["potential"]),
            "- 分项: %s" % json.dumps(s["parts"], ensure_ascii=False),
        ]
        if p.get("error"):
            lines.append("- 错误: %s" % p["error"])
        lines.append("")
    mp = OUTDIR / ("probe_%s.md" % stamp)
    mp.write_text("\n".join(lines), encoding="utf-8")
    return jp, mp


def self_test():
    ok = []

    def chk(name, cond):
        ok.append(bool(cond))
        print(("PASS " if cond else "FAIL ") + name)

    a1 = score("A", 1, 0, 30, 3, 1.0, "public")
    chk("A1 新鲜+三源+可行动 => P1/可证据", a1["tier"] == "P1" and a1["eligible"])
    d2 = score("D", 2, 0, 30, 3, 1.0, "public")
    chk("D2 即使新鲜也不作证据", (not d2["eligible"]) and d2["grade"] == "UNVERIFIED")
    stale = score("A", 1, 365, 30, 3, 1.0, "public")
    fresh = score("A", 1, 0, 30, 3, 1.0, "public")
    chk("时效衰减：旧 < 新", stale["total"] < fresh["total"])
    illegal = score("A", 1, 0, 30, 3, 1.0, "private")
    chk("未授权 => 不作证据", not illegal["eligible"])
    fail = score("A", 1, 0, 30, 1, 0.1, "public")
    chk("单源+低可行动 < 三源+高可行动", fail["total"] < a1["total"])
    print("self_test %d/%d" % (sum(ok), len(ok)))
    return 0 if all(ok) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--timeout", type=int, default=15)
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.probe:
        ap.print_help()
        return 0
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    only = set(x.strip() for x in a.only.split(",") if x.strip()) or None
    rows = run_probe(registry, only=only, timeout=a.timeout)
    jp, mp = write_outputs(rows)
    print("JSON", jp)
    print("MD  ", mp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
