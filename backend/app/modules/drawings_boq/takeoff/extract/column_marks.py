from __future__ import annotations
import re
from app.modules.drawings_boq.takeoff.prep.details import norm_mark
from app.modules.drawings_boq.takeoff.extract import config as C

def _size(c) -> tuple | None:
  p = c.params or {}
  if not p.get("length_mm") or not p.get("width_mm"):
    return None
  a, b = sorted((round(p["length_mm"] / 25.4), round(p["width_mm"] / 25.4)))
  return (a, b)

def _number(mark: str) -> int:
  m = re.search(r"(\d+)", mark)
  return int(m.group(1)) if m else 0

def _text(size) -> str:
  return f"{size[0]}×{size[1]} in"

def findings(cands: list, details: dict | None) -> list:
  plan: dict = {}
  loose: dict = {}
  
  for c in cands:
    if c.category != "COLUMN" or (c.facts or {}).get("neck_of") or (c.facts or {}).get("from_shapes") or ((c.facts or {}).get("view") or {}).get("foundation") or _size(c) is None:
      continue
    if c.tag:
      plan.setdefault(norm_mark(c.tag), set()).add(_size(c))
    else:
      loose[_size(c)] = loose.get(_size(c), 0) + int(c.count or 0)
      
  det = {m: {tuple(round(x) for x in s) for s in rec["sizes_in"]} for m, rec in (details or {}).items() if rec.get("sizes_in")}
  free = lambda size: sorted((m for m, ss in det.items() if m not in plan and size in ss and (m, size) not in taken), key=lambda m: (len(det[m]) < 2, _number(m), m))
  taken: set = set()
  
  out = []
  for mark in sorted(plan, key=lambda m: (_number(m), m)):
    if mark in det or len(plan[mark]) != 1:
      continue
  
    size = next(iter(plan[mark]))
    opts = free(size)
    if opts:
      taken.add((opts[0], size))
      twice = len(det[opts[0]]) > 1
      out.append({"kind": "NO_DETAIL", "mark": mark, "detail": opts[0], "size_in": list(size), "text": f"No column detail is captioned {mark}. The {_text(size)} detail captioned {opts[0]} is proposed for it"
        + (f" ({opts[0]} is captioned twice, with different sizes, so one of its two details may be this one's)" if twice else "") + ". Check it."})
      
  for size in sorted(loose):
    opts = free(size)
    n = loose[size]
    if len(opts) == 1:
      taken.add((opts[0], size))
      out.append({"kind": "BY_SIZE", "mark": None, "detail": opts[0], "size_in": list(size), "count": n, "text": f"{n} square{'s' if n != 1 else ''} of {_text(size)} on the plan have no mark. "
        f"The detail captioned {opts[0]} is the only detail of that size that no plan mark uses, and is proposed for them. Check it."})
    elif opts:
      out.append({"kind": "BY_SIZE", "mark": None, "detail": None, "size_in": list(size), "count": n, "options": opts, "text": f"{n} square{'s' if n != 1 else ''} of {_text(size)} on the plan have no mark. "
        f"These details have that size and no plan mark: {', '.join(opts)}. Say which applies."})
  rest = [(m, s) for m in sorted(det, key=lambda m: (_number(m), m)) if m not in plan for s in sorted(det[m]) if (m, s) not in taken]
  if rest:
    out.append({"kind": "NO_PLAN_MARK", "mark": None, "detail": None, "text": "No framing plan marks or draws a column for: " + ", ".join(f"{m} ({_text(s)})" for m, s in rest)
      + ". Check whether these details belong to a column of this job."})
  return out

CODES = {"NO_DETAIL": "COLUMN_MARK_NO_DETAIL", "BY_SIZE": "COLUMN_MARK_BY_SIZE", "NO_PLAN_MARK": "COLUMN_DETAIL_NO_PLAN_MARK"}

def apply(cands: list, found: list, status) -> None:
  cols = [c for c in cands if c.category == "COLUMN" and not (c.facts or {}).get("neck_of") and not (c.facts or {}).get("from_shapes")]
  for chk in found:
    if chk["kind"] == "NO_DETAIL":
      hit = [c for c in cols if c.tag and norm_mark(c.tag) == chk["mark"]]
    elif chk["kind"] == "BY_SIZE":
      hit = [c for c in cols if not c.tag and _size(c) == tuple(chk["size_in"])]
    else:
      hit = cols[:1]
    for c in hit:
      n = C.note(CODES[chk["kind"]])
      n["message"] = chk["text"]
      c.notes.append(n)
      c.facts = {**(c.facts or {}), "mark_check": [*((c.facts or {}).get("mark_check") or []), {k: v for k, v in chk.items()}]}
      c.status = status(c.notes)
