from __future__ import annotations
import json
import os
import yaml
from app.engine.catalogue import conventions as CV
from app.engine.catalogue import loader as CAT
from app.modules.drawings_boq.takeoff.completeness import facts as F
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.modules.drawings_boq.takeoff.extract import read_status as RS
from app.modules.drawings_boq.takeoff.proof import case_io as CIO
from app.modules.drawings_boq.takeoff.proof.reading import intake as IN

OUTLINED = ("OUTLINED", "PARTIAL")
SHEET_SHIFT = 1000

def plain_read(read) -> dict:
  return {"items": [IN.plain(i) for i in read.items], "pages": {str(k): IN.plain(v) for k, v in read.pages.items()}}

def merge(plains: list) -> dict:
  out: dict = {"items": [], "pages": {}}
  for n, plain in enumerate(plains):
    shift = n * SHEET_SHIFT
    for i in plain["items"]:
      out["items"].append({**i, "sheet": i["sheet"] + shift})
    for key, p in plain["pages"].items():
      sheet = int(p.get("sheet") or key) + shift
      out["pages"][str(sheet)] = {**p, "sheet": sheet, "register": {**(p.get("register") or {}), "sheet": sheet}}
  return out

def page_rows(plain: dict) -> list:
  rows = []
  for key, p in plain["pages"].items():
    reg = p.get("register") or {}
    rows.append({"page": int(p.get("sheet") or key), "role": reg.get("role"), "plan_kind": reg.get("plan_kind"), "floor": reg.get("floor"), "discipline": reg.get("discipline"), "title": reg.get("title"), "scale_basis": reg.get("scale_basis")})
  return sorted(rows, key=lambda r: r["page"])

def sheet_key(row: dict) -> str | None:
  if row["role"] == "PLAN":
    return f"PLAN/{row['plan_kind']}" if row["plan_kind"] else "PLAN"
  return row["role"]

def storeys_of(case: str, root: str = CIO.HERE) -> list:
  path = os.path.join(root, case, "storeys.yaml")
  if not os.path.isfile(path):
    return []
  with open(path, encoding="utf-8") as fh:
    raw = yaml.safe_load(fh) or []
  return [str(r["floor"]).upper() for r in raw if isinstance(r, dict) and r.get("floor")]

def join_floors_of(plain: dict) -> list:
  out = set()
  for i in plain["items"]:
    j = i.get("join") or {}
    if isinstance(j, dict) and j.get("floor"):
      out.add(str(j["floor"]).upper())
  return sorted(out)

def _floor_of(plain_floor, join) -> str | None:
  f = (join or {}).get("floor") if isinstance(join, dict) else None
  f = str(f or plain_floor or "").upper()
  return f if f and f not in F.NOT_FLOORS else None

def evidence_of(plain: dict, lines: list | None = None) -> dict:
  ev = LG.empty_evidence()
  floor_of_page = {int(k): (p.get("register") or {}).get("floor") for k, p in plain["pages"].items()}
  seen: dict = {}
  
  for i in plain["items"]:
    base = f"p{i['sheet']}:{i['mark'] or i['cls'].lower()}"
    seen[base] = seen.get(base, 0) + 1
    reasons = list(i.get("reasons") or [])
    missing = list(dict.fromkeys(LG.REASON_INPUT[r] for r in reasons if r in LG.REASON_INPUT))
    ev["members"].append({"id": f"{base}#{seen[base]}", "cls": i["cls"], "mark": i.get("mark"), "floor": _floor_of(floor_of_page.get(i["sheet"]), i.get("join")), "status": i["status"], "reasons": reasons, "missing": missing})
  rows = page_rows(plain)
  
  ev["sheets"] = sorted({k for k in (sheet_key(r) for r in rows) if k})
  ev["no_reader"] = list(RS.NO_READER)
  for key, p in plain["pages"].items():
    reg = p.get("register") or {}
    why = RS.LABELS_OUTLINED if reg.get("text_type") in OUTLINED else RS.NO_SYMBOLS
    for cls, status in sorted((p.get("coverage") or {}).items()):
      if status == RS.NOT_READ:
        ev["gaps"].append({"cls": cls, "page": int(p.get("sheet") or key), "floor": _floor_of(reg.get("floor"), None), "reasons": [why]})
  ev["lines"] = [dict(ln) for ln in lines or [] if ln.get("family") and ln.get("value") is not None]
  return ev

def lines_of(score_dir: str | None, case: str) -> list:
  if not score_dir:
    return []
  
  path = os.path.join(score_dir, case, "score.json")
  if not os.path.isfile(path):
    return []
  
  with open(path, encoding="utf-8") as fh:
    doc = json.load(fh)
    
  out = []
  for ln in doc.get("lines") or []:
    parts = str(ln.get("key") or "").split("/")
    floor = parts[1].split("@")[0].upper() if len(parts) > 1 else None
    if ln.get("trace") is not None and parts[0]:
      out.append({"family": parts[0], "floor": floor if floor in F.FLOOR_ORDER else None, "value": ln["trace"], "unit": ln.get("unit")})
  return out

def run_set(plain: dict, storeys: list | None = None, lines: list | None = None, decisions: dict | None = None, conventions: list | None = None, methods: dict | None = None, answers: dict | None = None) -> dict:
  facts = F.project_facts(page_rows(plain), decisions, storeys, join_floors_of(plain))
  evidence = evidence_of(plain, lines)
  entries = LG.build(CAT.items(), facts, evidence, conventions, methods, answers)
  return {"facts": facts, "evidence": evidence, "ledger": entries, "summary": LG.summary(entries), "scope": F.scope_of(facts), "conventions": list(conventions or []), "methods": dict(methods or {}), "answers": dict(answers or {})}

def show(result: dict, name: str = "") -> str:
  v = F.values(result["facts"])
  head = f"{name}: type {v['type']}, structure {v['structure']}, floors {','.join(v['floors']) or '-'}, basement {v['basement']}, sets {','.join(v['sets_present']) or '-'}, scope {result['scope']}"
  s = result["summary"]
  return head + "\n  " + ", ".join(f"{k} {n}" for k, n in s["by_state"].items()) + "\n  reasons: " + ", ".join(f"{k} {n}" for k, n in s["by_reason"].items())

def main(argv: list | None = None) -> int:
  import argparse
  ap = argparse.ArgumentParser(description="Print the project facts and the five-state completeness ledger for one project: the reading dumps (JSON) of its PDFs.")
  ap.add_argument("dumps", nargs="+")
  ap.add_argument("--storeys", help="a case folder name whose storeys.yaml gives the floors")
  ap.add_argument("--full", action="store_true", help="print every ledger entry")
  ap.add_argument("--conventions", action="store_true", help="switch every Pakistan convention on, as a company can")
  ap.add_argument("--method", action="append", default=[], help="a decided method, name=OPTION")
  args = ap.parse_args(argv)
  
  plains = []
  for path in args.dumps:
    with open(path, encoding="utf-8") as fh:
      plains += list(json.load(fh).values())
  on = CV.ids() if args.conventions else []
  res = run_set(merge(plains), storeys_of(args.storeys) if args.storeys else None, conventions=on, methods=dict(m.split("=", 1) for m in args.method))
  print(show(res, ", ".join(os.path.basename(p) for p in args.dumps)))
  if args.full:
    for e in res["ledger"]:
      print(f"  {e['element']:6} {e['floor']:9} {e['state']:15} {','.join(e['reasons'])}")
  return 0

if __name__ == "__main__":
  raise SystemExit(main())
