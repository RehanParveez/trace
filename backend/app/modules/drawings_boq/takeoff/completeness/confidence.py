from __future__ import annotations
from app.engine.catalogue import confidence as CF
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.modules.drawings_boq.takeoff.completeness import self_check as SC

def member_conditions(checks: list) -> dict:
  fails, passes = set(), set()
  for r in checks or []:
    if r["result"] == SC.NOT_CHECKABLE:
      continue
    if r["result"] == SC.FAIL:
      fails.update(r["items"])
    passes.update(r.get("agreed") or [])
  return {**{i: CF.CHECKS_PASS for i in passes}, **{i: CF.CHECK_FAILS for i in fails}}

def element_conditions(checks: list) -> dict:
  out: dict = {}
  for r in checks or []:
    if r["result"] == SC.FAIL:
      for e in r.get("elements") or []:
        out[e] = CF.CHECK_FAILS
  return out

def of_entry(entry: dict, class_of: dict, by_member: dict, by_element: dict, table: dict | None = None) -> tuple:
  table = CF.doc() if table is None else table
  if entry["state"] == LG.ASSUMED:
    return CF.LOW, "assumed"
  if entry["state"] != LG.MEASURED:
    return None, "unread"
  bands = []
  
  for mid in entry.get("members") or []:
    cond = by_member.get(mid, CF.NO_CHECK)
    if by_element.get(entry["element"]) == CF.CHECK_FAILS:
      cond = CF.CHECK_FAILS
    bands.append(CF.band(class_of.get(mid) or "", cond, table))
  if not bands:
    return CF.LOW, "assumed"
  worst = CF.lowest([b for b, _ in bands])
  return worst, next(w for b, w in bands if b == worst)

def of_entries(entries: list, evidence: dict, checks: list, table: dict | None = None) -> dict:
  table = CF.doc() if table is None else table
  class_of = {m["id"]: m["cls"] for m in evidence.get("members") or []}
  by_member, by_element = member_conditions(checks), element_conditions(checks)
  out: dict = {}
  for e in entries:
    band, why = of_entry(e, class_of, by_member, by_element, table)
    if band is None:
      continue
    got = out.get(e["element"])
    if got is None or CF.ORDER.index(band) < CF.ORDER.index(got["band"]):
      out[e["element"]] = {"band": band, "why": CF.text(why) if why in table["text"] else why}
  return out

def line_band(elements: list, by_element: dict, assumed_share: float = 0.0) -> tuple:
  got = [by_element[e] for e in elements if e in by_element]
  if not got:
    return None, None
  worst = min(got, key=lambda g: CF.ORDER.index(g["band"]))
  band, why = worst["band"], worst["why"]
  if assumed_share and assumed_share > 0:
    cap = CF.LOW if assumed_share >= 0.5 else CF.MEDIUM
    if CF.ORDER.index(cap) < CF.ORDER.index(band):
      band, why = cap, CF.text("line_assumed")
  return band, why

def high_share(rows: list) -> float | None:
  total = sum(a for _b, a in rows if a)
  return None if not total else round(sum(a for b, a in rows if a and b == CF.HIGH) / total * 100.0, 1)
