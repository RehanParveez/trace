from __future__ import annotations
import hashlib
import json
import os
import re
import yaml
from app.modules.drawings_boq.takeoff.proof.bench import report as RP
from app.modules.drawings_boq.takeoff.proof.bench import sets as ST
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.ai_reader import cache as CACHE
from app.modules.drawings_boq.takeoff.ai_reader import cost as COST
from app.engine.measure import rule_registry as RR
from app.modules.drawings_boq.takeoff.proof.bench import offices as OFF
from app.modules.drawings_boq.takeoff.proof.bench import failures as FL
from app.modules.drawings_boq.takeoff.proof import gate17 as G17

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "measure.yaml")
GATE = re.compile(r"\(gate (\d+)\)")

def load(path: str = PATH) -> dict:
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def read_json(path: str) -> dict | None:
  if not os.path.isfile(path):
    return None
  with open(path, encoding="utf-8") as fh:
    return json.load(fh)

def bench_rows(folder: str | None) -> list | None:
  path = os.path.join(folder or "", "rows.jsonl")
  if not folder or not os.path.isfile(path):
    return None
  with open(path, encoding="utf-8") as fh:
    return [json.loads(line) for line in fh if line.strip()]

def file_sha(path: str) -> str | None:
  if not os.path.isfile(path):
    return None
  with open(path, "rb") as fh:
    return hashlib.sha256(fh.read()).hexdigest()

def side(rows: list | None, run: str, pick) -> dict | None:
  mine = [r for r in rows or [] if r["run"] == run and pick(r)]
  return RP.stats(mine) if mine else None

def pair(before: dict | None, after: dict | None) -> dict:
  both = before is not None and after is not None and before["coverage"] is not None and after["coverage"] is not None
  return {"before": before, "after": after, "coverage_change": round(after["coverage"] - before["coverage"], 1) if both else None}

def bench_pairs(before: list | None, after: list | None, groups: list) -> dict:
  sets = sorted({r["set"] for rows in (before, after) for r in rows or []})
  sections = sorted({r["section"] for rows in (before, after) for r in rows or []})
  by_set, by_group, by_section = [], [], []
  
  for run in (RP.PRODUCT, RP.PROOF):
    for name in sets:
      by_set.append({"set": name, "run": run, **pair(side(before, run, lambda r: r["set"] == name), side(after, run, lambda r: r["set"] == name))})
      for g in groups:
        by_group.append({"set": name, "group": g, "run": run, **pair(side(before, run, lambda r: r["set"] == name and r["group"] == g), side(after, run, lambda r: r["set"] == name and r["group"] == g))})
    for sec in sections:
      by_section.append({"section": sec, "run": run, **pair(side(before, run, lambda r: r["section"] == sec), side(after, run, lambda r: r["section"] == sec))})
  return {"by_set": by_set, "by_group": by_group, "by_section": by_section}

def cost_rows(sets_doc: dict, root: str = CIO.HERE) -> dict:
  rows, unpriced = [], set()
  for name in sorted(sets_doc.get("sets") or {}):
    entries = CACHE.read_all(os.path.join(root, name))
    for task in sorted({str(e.get("task") or "-") for e in entries}):
      c = COST.summarise([e for e in entries if str(e.get("task") or "-") == task])
      unpriced.update(c["unpriced_models"])
      rows.append({"set": name, "task": task, "requests": c["requests"], "input_tokens": c["input_tokens"], "output_tokens": c["output_tokens"], "usd": c["usd"], "pkr": c["pkr"]})
      
  tasks = {}
  for r in rows:
    t = tasks.setdefault(r["task"], {"requests": 0, "usd": 0.0, "pkr": 0.0})
    t["requests"] += r["requests"]
    t["usd"] = round(t["usd"] + r["usd"], 6)
    t["pkr"] = round(t["pkr"] + r["pkr"], 4)
  return {"rows": rows, "by_task": tasks, "requests": sum(r["requests"] for r in rows), "usd": round(sum(r["usd"] for r in rows), 6), "pkr": round(sum(r["pkr"] for r in rows), 4), "unpriced_models": sorted(unpriced)}

def overrides_left(root: str = CIO.HERE) -> list:
  out = []
  for name in sorted(os.listdir(root)):
    folder = os.path.join(root, name)
    if os.path.isdir(folder) and os.path.isfile(os.path.join(folder, RR.OVERRIDES_FILE)):
      for e in CIO.load_override_entries(folder):
        out.append({"set": name, "rule": str(e["rule"]), "value": str(e["value"]), "until": str(e["until"]), "date": str(e["date"]), "reason": " ".join(str(e["reason"]).split())})
  return out

def gate17_exceptions() -> int:
  return len(G17.load_allow()[0])

def first_sight(sets_doc: dict, reg: dict, history: list, after: list | None, floor: float) -> list:
  groups = list((sets_doc.get("section_groups") or {}).keys())
  out = []
  for name, row in sorted((sets_doc.get("sets") or {}).items()):
    if name not in reg["set_log"]:
      continue
    first = OFF.first_score(name, history)
    now = side(after, RP.PRODUCT, lambda r: r["set"] == name)
    cover = None if first is None or first["coverage_pct"] in ("", "-") else float(first["coverage_pct"])
    out.append({"set": name, "office": row.get("office"), "labels": {g: ST.split_of(row.get("office"), g, None, row) for g in groups}, "first": first, "now": now, "below_floor": cover is not None and cover < floor})
  return out

def open_groups(after: list | None, run: str, top: int) -> dict:
  groups = FL.groups([r for r in after or [] if r["run"] == run])
  owners = {}
  for g in groups:
    owners[g["suggested_owner"]] = owners.get(g["suggested_owner"], 0) + 1
  return {"run": run, "groups": len(groups), "shown": groups[:top], "by_owner": dict(sorted(owners.items(), key=lambda kv: (-kv[1], kv[0])))}

def gates(check: dict | None, required: list) -> dict:
  by: dict = {}
  for r in (check or {}).get("results") or []:
    m = GATE.search(r["name"])
    if m:
      slot = by.setdefault(int(m.group(1)), {"ok": True, "checks": 0, "notes": []})
      slot["ok"] = slot["ok"] and bool(r["ok"])
      slot["checks"] += 1
      if not r["ok"]:
        slot["notes"].append(f"{r['name']}: {r['note']}" if r.get("note") else r["name"])
  results = (check or {}).get("results") or []
  
  return {"found": check is not None, "passed": bool((check or {}).get("passed")), "checks": len(results), "failed": sum(1 for r in results if not r["ok"]), "by_gate": dict(sorted(by.items())),
    "missing": [g for g in required if g not in by], "red": [g for g in required if g in by and not by[g]["ok"]], "green": check is not None and all(g in by and by[g]["ok"] for g in required)}

def split_hash(doc: dict, split: str) -> str:
  ids = sorted(f"{o['id']}|{o['outcome']}" for o in doc.get("outcomes") or [] if str(o["split"]).lower() == split)
  return hashlib.sha256("\n".join(ids).encode()).hexdigest()[:8]

def reading_rows(doc: dict | None, splits: list) -> dict:
  if not doc:
    return {}
  by = {str(k).lower(): v for k, v in ((doc.get("metrics") or {}).get("by_split") or {}).items()}
  return {"hash": str(doc.get("hash") or "")[:8], "splits": {s: {"truth": by[s]["truth"], "matched": by[s]["matched"], "recall": by[s]["recall"], "silent_wrong": by[s]["silent_wrong"], "hash": split_hash(doc, s)} for s in splits if s in by}}
