from __future__ import annotations
from app.modules.drawings_boq.takeoff.prep.details import norm_mark
from app.engine.measure.steel_grammar import steel_text

MM_IN = 25.4
MAX_LISTED = 200
DEPTH_SAME_MM = 1.0
BEAM_KIND_OF_PREFIX = {"PB": "PLINTH", "RB": "ROOF", "GB": "GRADE", "LB": "LINTEL", "TB": "TIE", "CB": "TIE"}
NOT_BEAMS = ("LINTEL",)
COLUMN_MARK, BEAM_DEPTH = "COLUMN_MARK", "BEAM_DEPTH"
KINDS = (COLUMN_MARK, BEAM_DEPTH)

NOTES = {
  "MARK_FROM_DETAIL_CHOSEN": ("info", "A person chose this mark from the marks whose column details match the size of these shapes. The plan prints no mark beside them."),
  "BEAM_DEPTH_CHOSEN": ("warning", "The section of this beam mark prints no depth that could be read. A person chose the depth from those printed for other beams of the same kind; check it against the drawing."),
}

def note(code: str, **extra) -> dict:
  sev, msg = NOTES[code]
  return {"code": code, "severity": sev, "message": msg, **extra}

def _mm(inches: float) -> float:
  return round(float(inches) * MM_IN, 1)

def column_detail_marks(sheets: list) -> dict:
  by: dict = {}
  for sh in sheets or []:
    for d in sh.get("details") or []:
      mark = norm_mark(d.get("mark") or "")
      if not mark:
        continue
    
      rec = by.setdefault(mark, {"pages": set(), "sizes": set(), "shown": mark})
      rec["pages"].add(sh.get("page_no"))
      if d.get("read") in ("TEXT", "TEXT_SQUARE", "OCR", "OCR_SQUARE") and d.get("w_in") and d.get("h_in"):
        rec["sizes"].add((min(d["w_in"], d["h_in"]), max(d["w_in"], d["h_in"])))
        
  out = {}
  for mark, r in sorted(by.items()):
    sizes = sorted(r["sizes"])
    out[mark] = {"mark": mark, "family": "COLUMN", "kind": "COLUMN", "pages": sorted(p for p in r["pages"] if p), "sizes_in": [list(s) for s in sizes],
      "disagree": len(sizes) > 1, "size_mm": [_mm(sizes[0][0]), _mm(sizes[0][1])] if len(sizes) == 1 else None}
  return out

def beam_detail_marks(sheets: list) -> dict:
  by: dict = {}
  for sh in sheets or []:
    for d in sh.get("details") or []:
      mark = norm_mark(d.get("mark") or "")
      if not mark or mark == "TIE" or d.get("kind") in NOT_BEAMS:
        continue
    
      rec = by.setdefault(mark, {"pages": set(), "kind": d.get("kind"), "depths": set(), "widths": set(), "steels": []})
      rec["pages"].add(sh.get("page_no"))
      if d.get("depth_in"):
        rec["depths"].add(float(d["depth_in"]))
      if d.get("width_in"):
        rec["widths"].add(float(d["width_in"]))
      if d.get("steel") and d["steel"] not in rec["steels"]:
        rec["steels"].append(d["steel"])
        
  out = {}
  for mark, r in sorted(by.items()):
    depths, widths = sorted(r["depths"]), sorted(r["widths"])
    steel = r["steels"][0] if len(r["steels"]) == 1 else None
    out[mark] = {"mark": mark, "family": "BEAM", "kind": r["kind"] or "BEAM", "pages": sorted(p for p in r["pages"] if p),
      "depth_mm": _mm(depths[0]) if len(depths) == 1 else None, "width_mm": _mm(widths[0]) if len(widths) == 1 else None, "disagree": len(depths) > 1 or len(r["steels"]) > 1,
      "steel_text": steel_text(steel) if steel else None}
  return out

def _norm_all(values) -> set:
  return {norm_mark(str(v)) for v in values or [] if v}

def plan_marks(rows: list, strip_tags: list | None = None) -> dict:
  col, beam = set(), set()
  for r in rows or []:
    f = r.facts or {}
    
    cat = r.category
    if cat == "COLUMN" and r.tag:
      col.add(norm_mark(r.tag))
    elif cat == "BEAM":
      beam |= _norm_all([r.tag, f.get("section_mark"), f.get("beam_mark")])
    elif cat == "WALL":
      beam |= _norm_all((f.get("beam_marks") or {}).values())
  beam |= _norm_all(strip_tags)
  return {"COLUMN": col, "BEAM": beam}

def column_heights(rows: list) -> list:
  hs = set()
  for r in rows or []:
    if r.category == "COLUMN" and r.decision != "REJECTED":
      try:
        h = float((r.params or {}).get("depth_mm"))
      except (TypeError, ValueError):
        continue
      if h > 0:
        hs.add(round(h, 1))
  return sorted(hs)

def column_per_piece(size_mm, heights: list) -> dict | None:
  if not size_mm:
    return None
  a, b = float(size_mm[0]), float(size_mm[1])
  area, perimeter = a * b / 1e6, 2.0 * (a + b) / 1000.0
  out = {"section_m2": round(area, 4), "perimeter_m": round(perimeter, 3), "heights_mm": [heights[0], heights[-1]] if heights else None, "concrete_m3": None, "formwork_m2": None}
  if heights:
    lo, hi = heights[0] / 1000.0, heights[-1] / 1000.0
    out["concrete_m3"] = [round(area * lo, 4), round(area * hi, 4)]
    out["formwork_m2"] = [round(perimeter * lo, 3), round(perimeter * hi, 3)]
  return out

def beam_per_metre(width_mm, depth_mm) -> dict | None:
  if not width_mm or not depth_mm:
    return None
  w, d = float(width_mm) / 1000.0, float(depth_mm) / 1000.0
  return {"concrete_m3": round(w * d, 4), "formwork_m2": round(w + 2.0 * d, 3)}

def _is_unmarked_shape_row(r) -> bool:
  f = r.facts or {}
  return r.category == "COLUMN" and bool(f.get("from_shapes")) and not r.tag and r.decision == "NEW"

def column_proposals(mark: str, rows: list, page_of: dict) -> list:
  out = []
  for r in rows or []:
    if not _is_unmarked_shape_row(r):
      continue
    f = r.facts or {}
    tags = [t for t in f.get("candidate_tags") or [] if t]
    if mark not in _norm_all(tags):
      continue
    out.append({"candidate_id": r.id, "sheet_id": r.sheet_id, "page_no": page_of.get(r.sheet_id), "ckey": r.ckey, "count": int(r.count or 0),
      "size_mm": list(f.get("size_used_mm") or []), "level": f.get("level_hint"), "points": [list(p) for p in (r.geometry or {}).get("points") or []][:60],
      "offered": [t for t in tags], "other_marks": [t for t in tags if norm_mark(t) != mark]})
  return sorted(out, key=lambda p: (p["page_no"] or 0, p["ckey"]))

def column_items(details: dict, plan: set, rows: list, page_of: dict) -> list:
  heights = column_heights(rows)
  out = []
  for mark, d in details.items():
    if mark in plan:
      continue
    props = column_proposals(mark, rows, page_of)
    reason = "NO_PLAN_INSTANCE"
    out.append({"mark": mark, "family": "COLUMN", "kind": "COLUMN", "reason": reason, "detail_pages": d["pages"], "size_mm": d["size_mm"], "sizes_in": d["sizes_in"],
      "detail_disagree": d["disagree"], "size_read": bool(d["size_mm"]), "per_piece": column_per_piece(d["size_mm"], heights), "proposals": props})
  return out

def beam_items(sections: dict, plan: set) -> list:
  out = []
  for mark, s in sections.items():
    if mark in plan:
      continue
    out.append({"mark": mark, "family": "BEAM", "kind": s["kind"], "reason": "NO_PLAN_INSTANCE", "detail_pages": s["pages"], "depth_mm": s["depth_mm"], "width_mm": s["width_mm"],
      "detail_disagree": s["disagree"], "steel_text": s["steel_text"], "depth_read": s["depth_mm"] is not None, "per_metre": beam_per_metre(s["width_mm"], s["depth_mm"])})
  return out

def beam_kind(mark: str) -> str:
  prefix = "".join(ch for ch in norm_mark(mark) if ch.isalpha())
  return BEAM_KIND_OF_PREFIX.get(prefix, "BEAM")

def beam_row_marks(r) -> list:
  f = r.facts or {}
  return sorted(_norm_all([r.tag, f.get("section_mark"), f.get("beam_mark")]))

def depth_options(mark: str, sections: dict) -> list:
  kind = beam_kind(mark)
  by: dict = {}
  for m, s in sections.items():
    if m == mark or s["disagree"] or not s["depth_mm"] or (s["kind"] or beam_kind(m)) != kind:
      continue
    key = next((k for k in by if abs(k - s["depth_mm"]) <= DEPTH_SAME_MM), None)
    by.setdefault(s["depth_mm"] if key is None else key, []).append(m)
  return [{"depth_mm": k, "marks": sorted(v)} for k, v in sorted(by.items())]

def _needs_depth(r) -> bool:
  return r.category == "BEAM" and r.decision != "REJECTED" and (r.params or {}).get("depth_mm") in (None, "") and "depth_mm" in (r.missing or [])

def depth_gaps(sections: dict, rows: list, page_of: dict) -> list:
  by: dict = {}
  for r in rows or []:
    if not _needs_depth(r):
      continue
    marks = beam_row_marks(r)
    if not marks:
      continue
    by.setdefault(marks[0], []).append(r)
    
  out = []
  for mark, rs in sorted(by.items()):
    own = sections.get(mark)
    if own and own["depth_mm"]:
      continue
    opts = depth_options(mark, sections)
    items, total = [], 0.0
    width = None
    
    for r in rs:
      f, p = r.facts or {}, r.params or {}
      length = float(f.get("length_m") or 0.0) or (float(p.get("length_mm")) / 1000.0 if p.get("length_mm") else 0.0)
      w = p.get("width_mm") or f.get("beam_width_mm")
      width = width or w
      total += length * float(r.count or 1)
      items.append({"candidate_id": r.id, "sheet_id": r.sheet_id, "page_no": page_of.get(r.sheet_id), "decision": r.decision, "length_m": round(length, 3), "width_mm": w,
        "chosen": bool(f.get("depth_choice"))})
      
    stake = None
    if opts and width and total > 0:
      lo, hi = opts[0]["depth_mm"], opts[-1]["depth_mm"]
      stake = {"length_m": round(total, 3), "width_mm": width, "concrete_m3": [round(total * float(width) / 1000.0 * lo / 1000.0, 3), round(total * float(width) / 1000.0 * hi / 1000.0, 3)]}
    out.append({"mark": mark, "kind": beam_kind(mark), "has_section": own is not None, "section_pages": own["pages"] if own else [], "options": opts, "rows": items, "stake": stake})
  return out

def _set(row, **kw) -> None:
  for k, v in kw.items():
    setattr(row, k, v)

def apply_column_mark(row, mark: str, decision_id: str) -> bool:
  f = dict(row.facts or {})
  offered = [t for t in f.get("candidate_tags") or [] if t]
  shown = next((t for t in offered if norm_mark(t) == norm_mark(mark)), None)
  
  if row.category != "COLUMN" or not f.get("from_shapes") or row.decision != "NEW" or shown is None:
    return False
  if row.tag and norm_mark(row.tag) == norm_mark(shown) and (f.get("mark_from_detail") or {}).get("decision_id") == decision_id:
    return False
  if row.tag and not f.get("mark_from_detail"):
    return False

  f["tag"] = shown
  notes = [n for n in (row.notes or []) if n.get("code") != "MARK_FROM_DETAIL_CHOSEN"]
  notes.append(note("MARK_FROM_DETAIL_CHOSEN", mark=shown, offered=offered))
  label, before = row.label or "", (f.get("mark_from_detail") or {}).get("mark")
  f["mark_from_detail"] = {"mark": shown, "decision_id": decision_id, "offered": offered}
  if before and label.startswith(before):
    label = shown + label[len(before):]
  elif "Columns (no mark)" in label:
    label = label.replace("Columns (no mark)", shown, 1)
  _set(row, tag=shown, facts=f, notes=notes, label=label[:200])
  return True

def undo_column_mark(row, decision_id: str) -> bool:
  f = dict(row.facts or {})
  mine = f.get("mark_from_detail") or {}
  if mine.get("decision_id") != decision_id or row.decision != "NEW":
    return False

  shown = row.tag
  f["tag"] = None
  f.pop("mark_from_detail", None)
  label = row.label or ""
  label = label.replace(shown, "Columns (no mark)", 1) if shown and label.startswith(shown) else label
  _set(row, tag=None, facts=f, notes=[n for n in (row.notes or []) if n.get("code") != "MARK_FROM_DETAIL_CHOSEN"], label=label[:200])
  return True

def apply_beam_depth(row, mark: str, depth_mm: float, decision_id: str, from_marks: list) -> bool:
  if not _needs_depth(row) or row.decision != "NEW" or norm_mark(mark) not in beam_row_marks(row):
    return False

  f, p = dict(row.facts or {}), dict(row.params or {})
  p["depth_mm"] = float(depth_mm)
  f["depth_choice"] = {"mm": float(depth_mm), "mark": norm_mark(mark), "from": list(from_marks), "decision_id": decision_id}
  notes = [n for n in (row.notes or []) if n.get("code") != "BEAM_DEPTH_CHOSEN"]
  notes.append(note("BEAM_DEPTH_CHOSEN", depth_mm=float(depth_mm), from_marks=list(from_marks)))
  from app.modules.drawings_boq.takeoff.extract.pipeline import _status
  _set(row, params=p, facts=f, notes=notes, missing=[m for m in (row.missing or []) if m != "depth_mm"], status=_status(notes))
  return True

def undo_beam_depth(row, decision_id: str) -> bool:
  f = dict(row.facts or {})
  if (f.get("depth_choice") or {}).get("decision_id") != decision_id or row.decision != "NEW":
    return False

  p = dict(row.params or {})
  p.pop("depth_mm", None)
  f.pop("depth_choice", None)
  notes = [n for n in (row.notes or []) if n.get("code") != "BEAM_DEPTH_CHOSEN"]
  from app.modules.drawings_boq.takeoff.extract.pipeline import _status
  _set(row, params=p, facts=f, notes=notes, missing=[*(row.missing or []), "depth_mm"] if "depth_mm" not in (row.missing or []) else list(row.missing), status=_status(notes))
  return True

def report(column_sheets: list, beam_sheets: list, rows: list, page_of: dict, strip_tags: list | None = None) -> dict:
  cols, secs = column_detail_marks(column_sheets), beam_detail_marks(beam_sheets)
  plan = plan_marks(rows, strip_tags)
  
  citems = column_items(cols, plan["COLUMN"], rows, page_of)
  bitems = beam_items(secs, plan["BEAM"])
  gaps = depth_gaps(secs, rows, page_of)
  cut = max(0, len(citems) + len(bitems) - MAX_LISTED)
  citems, bitems = citems[:MAX_LISTED], bitems[:max(0, MAX_LISTED - len(citems))]
  return {"columns": citems, "beams": bitems, "depth_gaps": gaps,
    "summary": {"detail_only": len(citems) + len(bitems), "columns": len(citems), "beams": len(bitems), "with_place": sum(1 for c in citems if c["proposals"]),
      "depth_gaps": len(gaps), "cut": cut, "column_marks_with_detail": len(cols), "beam_marks_with_section": len(secs)}}
