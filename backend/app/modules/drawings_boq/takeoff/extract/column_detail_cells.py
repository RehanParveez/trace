from __future__ import annotations
from app.engine.measure import rule_registry as RR

RULE = "COLUMN_DETAIL_CELLS"
META_KEY = "column_detail_cells"
IN_MM = 25.4
MIN_VOTES = 3

def _bars_text(groups: list) -> str:
  if len(groups) == 1:
    return f"{groups[0][0]}-#{groups[0][1]}"
  return "+".join(f"{n}#{b}" for n, b in sorted(groups, key=lambda g: -g[1]))

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

def _label_ring(d: dict) -> str | None:
  ring = d.get("label_ring")
  if not ring:
    return None
  return f'#{int(ring["bar"])}@{float(ring["spacing_mm"]) / IN_MM:g}"c/c'

def cell_of(d: dict) -> dict | None:
  if not d.get("mark"):
    return None
  
  groups = _groups(d.get("bar_notes")) or _groups([{"n": n, "bar": b} for n, b in d.get("label_bars") or []])
  size = (float(d["w_in"]), float(d["h_in"])) if d.get("w_in") and d.get("h_in") else None
  overall = None
  
  if d.get("label_size_in"):
    printed = tuple(float(x) for x in d["label_size_in"])
    if size and size != printed and size[0] == size[1] and printed[0] == printed[1] and size[0] > printed[0]:
      overall = size[0]
    size = printed
  return {"mark": str(d["mark"]).upper(), "state": "READ", "size_in": list(size) if size else None, "read": d.get("read"),
    "bars": {"count": sum(n for n, _b in groups), "text": _bars_text(groups), "groups": [list(g) for g in groups]} if groups else None,
    "ties": _ties(d.get("steel")) or _label_ring(d), "reasons": [] if d.get("label_size_in") else _reasons(d), "anchor": [d["x"], d["y"]] if d.get("x") is not None and d.get("y") is not None else None,
    "overall_in": overall, "brick_in": round((overall - size[0]) / 2.0, 2) if overall and size and d.get("label_brick") else None}

def attrs_of(page: int, rec: dict) -> dict:
  a: dict = {"key": f"{rec['mark']}@p{page}"}
  if rec.get("size_in"):
    w, h = rec["size_in"]
    a.update(width_in=w, depth_in=h, size_mm=[round(w * IN_MM, 1), round(h * IN_MM, 1)])
  if rec.get("bars"):
    a.update(bar_count=rec["bars"]["count"], bars=rec["bars"]["text"])
  if rec.get("ties") and str(rec["ties"]).endswith("c/c"):
    a["ring"] = rec["ties"]
  if rec.get("overall_in"):
    a["overall_in"] = rec["overall_in"]
  if rec.get("brick_in"):
    a["cladding_brick_in"] = rec["brick_in"]
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
