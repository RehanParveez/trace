from __future__ import annotations
from app.modules.drawings_boq.takeoff.flow import sitting as SIT
from app.modules.drawings_boq.takeoff.completeness import ledger as LG

DATA = SIT.DATA
STATES = DATA["line_states"]
LIMITS = DATA["limits"]
TEXT = DATA["text"]
OPEN = "OPEN"
COUNTED = (LG.MEASURED, LG.ASSUMED, LG.ASKED, LG.NOT_READ)

def line_state(share) -> str:
  share = float(share or 0)
  if share <= 0:
    return "MEASURED"
  return "ASSUMED" if share >= 1 else "PART_ASSUMED"

def pct_of(value, amount) -> float | None:
  if value is None or not amount:
    return None
  return round((float(value) - float(amount)) / float(amount) * 100.0, 1)

def open_touching(elements: list, rows: list) -> int:
  have = set(elements)
  return sum(1 for r in rows if r.get("state") == OPEN and have & set(r.get("touches") or []))

def line_marks(billed_lines: list, priced: list, rows: list) -> list:
  out = []
  for b, p in zip(billed_lines, priced):
    elements = sorted({s[0] for s in b.sources})
    amount = p.amount
    share = p.assumed_share
    out.append({"state": line_state(share), "label": STATES[line_state(share)], "priced": amount is not None,
      "measured_amount": None if amount is None else float(round(amount * (1 - share), 2)),
      "assumed_amount": None if amount is None else float(round(amount * share, 2)),
      "low_pct": pct_of(p.low, amount), "high_pct": pct_of(p.high, amount), "elements": elements, "open_rows": open_touching(elements, rows)})
  return out

def coverage(entries: list) -> list:
  by: dict = {}
  for e in entries:
    if e["state"] not in COUNTED:
      continue
    row = by.setdefault(e["section"], {"section": e["section"], **{s: 0 for s in COUNTED}})
    row[e["state"]] += 1
  out = []
  for row in by.values():
    total = sum(row[s] for s in COUNTED)
    out.append({**row, "total": total, "with_quantity_pct": round((row[LG.MEASURED] + row[LG.ASSUMED]) / total * 100.0, 1) if total else 0.0})
  return sorted(out, key=lambda r: r["section"])

def assumptions(entries: list) -> list:
  by: dict = {}
  
  for e in entries:
    for a in e.get("assumptions") or []:
      row = by.setdefault((a["input"], a.get("rule")), {"input": a["input"], "rule": a.get("rule"), "value": a.get("value"), "unit": a.get("unit"), "range": a.get("range"), "source": a.get("source"), "items": set(), "floors": set()})
      row["items"].add(e["element"])
      if e["floor"] not in (None, LG.ALL):
        row["floors"].add(e["floor"])
  return sorted(({**r, "items": sorted(r["items"]), "floors": sorted(r["floors"])} for r in by.values()), key=lambda r: (-len(r["items"]), r["input"]))

def banner(totals: dict, open_rows: int) -> list:
  out = []
  if open_rows:
    out.append(TEXT["draft_open"].format(n=open_rows))
  if totals.get("unpriced"):
    out.append(TEXT["draft_unpriced"].format(n=totals["unpriced"]))
  grand = float(totals.get("grand") or 0)
  if grand and totals.get("assumed"):
    out.append(TEXT["draft_assumed"].format(pct=round(float(totals["assumed"]) / grand * 100.0, 1)))
  return out
