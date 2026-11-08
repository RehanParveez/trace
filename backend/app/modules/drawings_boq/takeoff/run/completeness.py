from __future__ import annotations
from app.modules.drawings_boq.takeoff.run import plain as PL
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.modules.drawings_boq.takeoff.extract import read_status as RS
from app.engine.catalogue import loader as CAT
from app.modules.drawings_boq.takeoff.completeness import facts as F

OUTLINED = ("OUTLINED", "PARTIAL")
SHEET_SHIFT = 1000

def plain_read(read) -> dict:
  return {"items": [PL.plain(i) for i in read.items], "pages": {str(k): PL.plain(v) for k, v in read.pages.items()}}

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
  role_of_page = {int(k): (p.get("register") or {}).get("role") for k, p in plain["pages"].items()}
  watched, fields = SCK.read_classes(), SCK.read_fields()

  seen: dict = {}
  
  for i in plain["items"]:
    base = f"p{i['sheet']}:{i['mark'] or i['cls'].lower()}"
    seen[base] = seen.get(base, 0) + 1
    reasons = list(i.get("reasons") or [])
    missing = list(dict.fromkeys(LG.REASON_INPUT[r] for r in reasons if r in LG.REASON_INPUT))
    ev["members"].append({"id": f"{base}#{seen[base]}", "cls": i["cls"], "mark": i.get("mark"), "floor": _floor_of(floor_of_page.get(i["sheet"]), i.get("join")), "status": i["status"], "reasons": reasons, "missing": missing})
    if i["cls"] in watched:
      got = i.get("attrs") or {}
      ev["observed"].append({"id": f"{base}#{seen[base]}", "sheet": i["sheet"], "cls": i["cls"], "mark": i.get("mark"), "floor": ev["members"][-1]["floor"], "role": role_of_page.get(i["sheet"]),
        "attrs": {k: got[k] for k in sorted(fields) if isinstance(got.get(k), (int, float)) and not isinstance(got.get(k), bool)}})

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

def run_set(plain: dict, storeys: list | None = None, lines: list | None = None, decisions: dict | None = None, conventions: list | None = None, methods: dict | None = None, answers: dict | None = None) -> dict:
  facts = F.project_facts(page_rows(plain), decisions, storeys, join_floors_of(plain))
  evidence = evidence_of(plain, lines)
  entries = LG.build(CAT.items(), facts, evidence, conventions, methods, answers)
  return {"facts": facts, "evidence": evidence, "ledger": entries, "summary": LG.summary(entries), "scope": F.scope_of(facts), "conventions": list(conventions or []), "methods": dict(methods or {}), "answers": dict(answers or {})}
