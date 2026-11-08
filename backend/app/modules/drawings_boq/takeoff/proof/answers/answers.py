from __future__ import annotations
import os
import yaml
from app.engine.catalogue import loader as CL
from app.engine.catalogue import vocabulary as V
from app.modules.drawings_boq.lab.aliases import SOFTWARE_UNIT, bill_quantity

FILE = "answers.yaml"
SOURCES = ("QS_BOQ", "CHECKED_DRAFT")
MAPPERS = ("AI", "PERSON", "CATALOGUE", "VOCAB")
ITEM_KEYS = ("element", "floor", "quantity", "unit", "qs_line", "sheet", "rows", "mapped_by", "confirmed")
WITHIN_PCT = 10.0

class Flow(dict):
  pass

def _flow(dumper, data):
  return dumper.represent_mapping("tag:yaml.org,2002:map", data, flow_style=True)

yaml.SafeDumper.add_representer(Flow, _flow)

def read_yaml(path: str):
  if not os.path.isfile(path):
    return None
  with open(path, encoding="utf-8") as fh:
    return yaml.safe_load(fh)

def write_yaml(path: str, doc) -> None:
  with open(path, "w", encoding="utf-8", newline="\n") as fh:
    yaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True, width=100000, default_flow_style=False)

def document(case_name: str, imp: dict, qs_id: str, res: dict) -> dict:
  from app.modules.drawings_boq.takeoff.proof.answers import qs_import as QI


  mapped = sum(1 for _ in res["items"])
  return {"answers": {
    "set": case_name, "source": "QS_BOQ", "workbook": imp["workbook"], "workbook_sha256": imp["sha256"], "qs": qs_id,
    "counts": {**QI.counts(imp), "items": mapped, "unmapped_lines": len(res["unmapped_lines"])},
    "totals_check": [{k: (round(v, 6) if isinstance(v, float) else v) for k, v in d.items()} for d in QI.totals_check(imp)],
    "summary_check": res["summary_check"],
    "items": [Flow(i) for i in res["items"]],
    "unmapped_lines": [Flow(u) for u in res["unmapped_lines"]],
  }}

def load(folder: str) -> dict | None:
  doc = read_yaml(os.path.join(folder, FILE))
  return (doc or {}).get("answers") if doc else None

def problems(doc: dict) -> list:
  out = []
  if doc.get("source") not in SOURCES:
    out.append(f"source must be one of {', '.join(SOURCES)}")
  ids = {i.id for i in CL.items()}
  for n, it in enumerate(doc.get("items") or [], 1):
    for k in ITEM_KEYS:
      if k not in it:
        out.append(f"item {n}: `{k}` is missing")
    if it.get("element") not in ids:
      out.append(f"item {n}: {it.get('element')} is not a catalogue item")
    if not isinstance(it.get("quantity"), (int, float)):
      out.append(f"item {n}: quantity is not a number")
    if it.get("mapped_by") not in MAPPERS:
      out.append(f"item {n}: mapped_by must be one of {', '.join(MAPPERS)}")
  for n, u in enumerate(doc.get("unmapped_lines") or [], 1):
    if not u.get("reason"):
      out.append(f"unmapped line {n}: no reason")
  return out

def ledger_line(element_id: str, unit) -> str | None:
  it = CL.get(element_id)
  if it is None or not unit:
    return None
  si = bill_quantity("", str(unit), 1.0)[1]
  for b in it.billing.PRIVATE_QS:
    if SOFTWARE_UNIT.get(b.line) == si:
      return b.line
  return None

def entries_of(doc: dict) -> tuple:
  groups: dict = {}
  no_number = []
  for it in doc.get("items") or []:
    line = ledger_line(it["element"], it.get("unit"))
    if line is None:
      no_number.append(it)
      continue
    k = (line, it.get("floor"), it.get("unit"))
    g = groups.setdefault(k, {"items": [], "qs": 0.0})
    g["items"].append(it)
    g["qs"] += float(it["quantity"])
  entries = []
  for (line, floor, unit), g in sorted(groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1]), str(kv[0][2]))):
    entries.append({"key": f"{line}/{floor or 'ALL'}", "item": f"{line} {floor or 'all floors'}", "unit": unit, "qs": g["qs"], "drawing": g["qs"], "class": "DRAWING", "tolerance_pct": WITHIN_PCT,
      "note": "", "family": line, "floor": floor, "kind": "MEASURED", "_items": len(g["items"]), "_confirmed": sum(1 for i in g["items"] if i.get("confirmed"))})
  return entries, no_number

def view(doc: dict, scored_lines: list, entries: list, no_number: list) -> dict:
  by_key = {s["key"]: s for s in scored_lines}
  items = len(doc.get("items") or [])
  within = not_read = unit_bad = 0
  split = {True: {"items": 0, "within_10": 0, "not_read": 0}, False: {"items": 0, "within_10": 0, "not_read": 0}}
  rows = []
  for e in entries:
    s = by_key.get(e["key"])
    n = e["_items"]
    sure = e.get("_confirmed", 0) == n
    split[sure]["items"] += n
    if s is None:
      continue
    if s["trace"] is None:
      if "unit" in (s.get("why") or ""):
        unit_bad += n
      else:
        not_read += n
        split[sure]["not_read"] += n

    elif s["diff_pct_qs"] is not None and abs(s["diff_pct_qs"]) <= WITHIN_PCT:
      within += n
      split[sure]["within_10"] += n
    rows.append({"key": e["key"], "unit": e["unit"], "qs": round(s["qs"], 3) if s["qs"] is not None else None, "trace": None if s["trace"] is None else round(s["trace"], 3),
      "diff_pct": None if s["diff_pct_qs"] is None else round(s["diff_pct_qs"], 2), "status": s["status"], "items": n, "confirmed": sure})
  scored = sum(1 for r in rows if r["trace"] is not None)
  return {"items": items, "confirmed": split[True], "unconfirmed": split[False], "lines": len(entries), "lines_with_a_number": scored, "items_within_10": within, "items_not_read": not_read, "items_no_trace_number": len(no_number) + unit_bad,
    "items_unmapped_lines": len(doc.get("unmapped_lines") or []), "table": rows}

def line_of(v: dict) -> str:
  c, u = v["confirmed"], v["unconfirmed"]
  return (f"answers: {v['items']} items in {v['lines']} lines; confirmed {c['items']} items ({c['within_10']} within 10%, {c['not_read']} NOT_READ), unconfirmed {u['items']} items ({u['within_10']} within 10%, {u['not_read']} NOT_READ); "
    f"{v['items_no_trace_number']} with no Trace number; {v['items_unmapped_lines']} workbook lines unmapped")
