from __future__ import annotations
from app.engine.measure import rule_registry as RR

RULE = "COLUMN_DETAIL_CELLS"
META_KEY = "column_detail_cells"
IN_MM = 25.4
MIN_VOTES = 3

def enabled() -> bool:
  return RR.on(RULE)

def _groups(notes: list) -> list:
  out = [(int(g["n"]), int(g["bar"])) for g in notes or [] if g.get("n") and g.get("bar")]
  return sorted(set(out), key=lambda g: (-g[0], -g[1]))

def _ties(steel: dict | None) -> str | None:
  ring = (steel or {}).get("ring") or {}
  if not ring.get("bar") or not ring.get("spacing_mm"):
    return None
  inches = float(ring["spacing_mm"]) / IN_MM
  return f'#{int(ring["bar"])}@{inches:g}"'

def _reasons(d: dict) -> list:
  if d.get("read") == "TEXT":
    return []
  votes = min(int(d.get("w_votes") or 0), int(d.get("h_votes") or 0))
  return [] if votes >= MIN_VOTES else ["OCR_LOW_CONFIDENCE"]

def cell_of(d: dict) -> dict | None:
  if not d.get("mark"):
    return None
  
  groups = _groups(d.get("bar_notes"))
  size = (float(d["w_in"]), float(d["h_in"])) if d.get("w_in") and d.get("h_in") else None
  return {"mark": str(d["mark"]).upper(), "state": "READ", "size_in": list(size) if size else None, "read": d.get("read"),
    "bars": {"count": sum(n for n, _b in groups), "text": " and ".join(f"{n}-#{b}" for n, b in groups), "groups": [list(g) for g in groups]} if groups else None,
    "ties": _ties(d.get("steel")), "reasons": _reasons(d), "anchor": [d["x"], d["y"]] if d.get("x") is not None and d.get("y") is not None else None}

def attrs_of(page: int, rec: dict) -> dict:
  a: dict = {"key": f"{rec['mark']}@p{page}"}
  if rec.get("size_in"):
    w, h = rec["size_in"]
    a.update(width_in=w, depth_in=h, size_mm=[round(w * IN_MM, 1), round(h * IN_MM, 1)])
  if rec.get("bars"):
    a.update(bar_count=rec["bars"]["count"], bars=rec["bars"]["text"])
  return a

def apply(rows: list) -> int:
  made = 0
  for row in rows:
    meta = row.get("meta")
    if meta is None:
      continue
    
    meta.pop(META_KEY, None)
    if not enabled():
      continue
    
    cells = [c for c in (cell_of(d) for d in meta.get("details") or []) if c]
    if cells:
      meta[META_KEY] = {"cells": cells}
      made += len(cells)
  mark_conflicts(rows)
  return made

SIZE_TOL_IN = 0.75

def _schedule_sizes(rows: list) -> dict:
  out: dict = {}
  for row in rows:
    sched = (((row.get("meta") or {}).get("structure_tables") or {}).get("column_schedule")) or {}
    for rec in sched.get("cells") or []:
      size = (rec.get("size") or {}).get("size_in") if rec.get("state") == "READ" else None
      if size:
        out.setdefault(rec["mark"], set()).add(tuple(sorted(size)))
  return out

def _agrees(a: tuple, b: tuple) -> bool:
  return all(abs(x - y) <= SIZE_TOL_IN for x, y in zip(a, b))

def mark_conflicts(rows: list) -> int:
  sizes = _schedule_sizes(rows)
  found = 0
  
  for row in rows:
    for rec in ((row.get("meta") or {}).get(META_KEY) or {}).get("cells") or []:
      printed = sizes.get(rec["mark"])
      if not printed or not rec.get("size_in"):
        continue
      mine = tuple(sorted(rec["size_in"]))
      if not any(_agrees(mine, p) for p in printed):
        rec["reasons"] = list(rec.get("reasons") or []) + ["CONFLICT_IN_DRAWING"]
        rec["schedule_in"] = sorted(printed)
        found += 1
  return found
