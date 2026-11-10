from __future__ import annotations
import os
import yaml
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.engine.catalogue import loader as CL

HERE = os.path.dirname(os.path.abspath(__file__))
WRONG, MISSING = "WRONG", "MISSING"
OUT_OF_10, NO_REASON = "OUTSIDE_10_PERCENT", "NO_REASON_GIVEN"
FIND, READ, JOIN, MEASURE, BILL = "FIND", "READ", "JOIN", "MEASURE", "BILL"
STAGES = (FIND, READ, JOIN, MEASURE, BILL)
SKIP = tuple(LG.INFO_REASONS)

def read_yaml(name: str) -> dict:
  with open(os.path.join(HERE, name), encoding="utf-8") as fh:
    return yaml.safe_load(fh) or {}

def first_reason(reasons: list) -> str | None:
  for r in reasons:
    code = str(r).split(":")[0]
    if code in SKIP or code.startswith("OWNER_") or code in (LG.METHOD_DEFAULT,):
      continue
    return code
  return None

def failure_of(row: dict) -> tuple | None:
  state, has_answer = row["state"], row["answer_qty"] not in (None, 0)
  if state == LG.NOT_READ:
    return LG.NOT_READ, first_reason(row["reasons"]) or NO_REASON
  if state in (LG.MEASURED, LG.ASSUMED) and row["answer_qty"] is not None and row["trace_qty"] is not None and not row["within_10"]:
    return WRONG, first_reason(row["reasons"]) or OUT_OF_10
  if state in (LG.ASKED, LG.NOT_APPLICABLE) and has_answer:
    return MISSING, first_reason(row["reasons"]) or NO_REASON
  return None

def stage_of(state: str, reason: str, table: dict | None = None) -> tuple:
  table = read_yaml("stages.yaml") if table is None else table
  got, basis = (table.get("by_reason") or {}).get(reason), "reason"
  if got is None:
    got, basis = (table.get("by_state") or {}).get(state), "state"
  if got not in STAGES:
    raise ValueError(f"stages.yaml gives no stage for {state} / {reason}")
  return got, basis

def class_of(element: str) -> str:
  item = CL.get(element)
  return item.member_class if item is not None and item.member_class else "UNKNOWN"

def key_of(row: dict) -> str | None:
  f = failure_of(row)
  if f is None:
    return None
  return f"{stage_of(f[0], f[1])[0]} / {class_of(row['element'])} / {f[1]}"

def rate_of(element: str, rates: dict) -> float | None:
  v = (rates.get("per_item_unit") or {}).get(element)
  if isinstance(v, dict):
    v = v.get("rate")
  return None if v is None else float(v)

def money_of(rows: list, rates: dict) -> tuple:
  by: dict = {}
  for r in rows:
    by.setdefault((r["set"], r["element"]), []).append(r)
  total, priced, unpriced = 0.0, 0, 0
  for (_s, element), rs in sorted(by.items()):
    whole = [r for r in rs if r["floor"] == LG.ALL]
    use = whole or rs
    qty = sum(r["answer_qty"] or 0.0 for r in use)
    rate = rate_of(element, rates)
    if not qty:
      continue
    if rate is None:
      unpriced += 1
    else:
      total += qty * rate
      priced += 1
  return (round(total, 2) if priced else None), priced, unpriced

def pack_of(element: str, owners: dict, depth: int = 0) -> str | None:
  item = CL.get(element)
  if item is None or not item.owner_pack:
    return None
  owner = item.owner_pack
  if owner in (owners.get("follow_source") or []) and depth < 5:
    src = (item.derived or {}).get("from") or []
    for sid in ([src] if isinstance(src, str) else list(src)):
      got = pack_of(sid, owners, depth + 1)
      if got:
        return got
  return (owners.get("alias") or {}).get(owner, owner)

def owner_of(rows: list, owners: dict, reason: str) -> str:
  count: dict = {}
  for r in rows:
    p = pack_of(r["element"], owners)
    if p:
      count[p] = count.get(p, 0) + 1
  if count:
    return sorted(count.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
  return (owners.get("by_reason") or {}).get(reason) or owners.get("default") or "UNASSIGNED"

def groups(rows: list, rates: dict | None = None, owners: dict | None = None) -> list:
  rates = read_yaml("rates.yaml") if rates is None else rates
  owners = read_yaml("owners.yaml") if owners is None else owners
  table = read_yaml("stages.yaml")
  names = {it.id: it.name for it in CL.items()}
  by: dict = {}
  for r in rows:
    f = failure_of(r)
    if f is None:
      continue
    
    stage, basis = stage_of(f[0], f[1], table)
    by.setdefault((stage, class_of(r["element"]), f[1]), []).append((r, f[0], basis))
  out = []
  for (stage, cls, reason), found in by.items():
    rs = [x[0] for x in found]
    offices = sorted({r["office"] for r in rs if r["office"] != "?"})
    sets = sorted({r["set"] for r in rs})
    items = sorted({r["element"] for r in rs})
    money, priced, unpriced = money_of(rs, rates)
    
    pages = []
    for r in sorted(rs, key=lambda x: (x["set"], x["element"], x["floor"])):
      if any(p["set"] == r["set"] for p in pages) or len(pages) >= 5:
        continue
      
      for p in (r.get("pages") or [])[:1]:
        pages.append({"set": r["set"], "pdf": p["pdf"], "page": p["page"]})
    out.append({"key": f"{stage} / {cls} / {reason}", "stage": stage, "class": cls, "reason": reason, "states": sorted({x[1] for x in found}), "stage_basis": {b: sum(1 for x in found if x[2] == b) for b in ("reason", "state")},
      "sections": sorted({r["section"] for r in rs}), "sets": len(sets), "offices": len(offices), "office_letters": offices,
      "set_names": sets, "items": items, "item_names": [names.get(i, i) for i in items], "rows": len(rs), "money_at_risk": money, "priced_items": priced, "unpriced_items": unpriced,
      "money": "unpriced" if money is None else ("partly priced" if unpriced else "priced"), "example_pages": pages,
      "by_office": {o: {"sets": len({r["set"] for r in rs if r["office"] == o}), "items": len({r["element"] for r in rs if r["office"] == o})} for o in offices},
      "suggested_owner": owner_of(rs, owners, reason)})
  return sorted(out, key=lambda g: (-g["offices"], -(g["money_at_risk"] or 0.0), -g["sets"], -len(g["items"]), g["key"]))
