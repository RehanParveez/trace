from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract import read_status as RS
from app.modules.drawings_boq.takeoff.extract import conflicts as CF

CONFLICT = "CONFLICT"
SHOWN = (RS.READ, RS.UNSURE, RS.NOT_READ, CONFLICT)
NOT_RUN = "NOT_RUN"
NOTHING_EXPECTED = "NOTHING_EXPECTED"
ITEM_CLASSES = ("GRID", "COLUMN", "FOOTING_STRIP", "FOOTING_PAD", "PLINTH_BEAM", "BEAM", "SLAB_PANEL", "SLAB_BAR_CALLOUT", "WALL", "ROOM", "DOOR", "WINDOW", "STAIR", "LINTEL_TYPE",
  "ELECTRICAL_POINT", "DISTRIBUTION_BOARD", "PLUMBING_FIXTURE", "PIPE_RUN", "DRAIN_POINT", "COLUMN_SCHEDULE_CELL", "NOTE_FACT", "OTHER")
MISREAD_KINDS = ("WRONG_VALUE", "WRONG_CLASS", "WRONG_POSITION", "INVENTED", "MISSED", "OTHER")
INPUT_NAMES = {
  "depth_mm": "Depth (mm)", "height_mm": "Height (mm)", "wall_height_mm": "Wall height (mm)", "column_height_mm": "Column height (mm)", "thickness_mm": "Thickness (mm)",
  "waist_mm": "Stair waist (mm)", "width_mm": "Width (mm)", "length_mm": "Length (mm)", "grade": "Concrete grade", "cover_mm": "Cover (mm)", "bearing_mm": "Bearing (mm)",
}

def _f(v) -> float | None:
  return None if v is None else float(v)

JOIN_KEYS = ("schedule_join", "section_join", "footing_section_join")

def join_conflict(f: dict) -> str | None:
  for key in JOIN_KEYS:
    j = f.get(key)
    if not isinstance(j, dict):
      continue
    reason = str(j.get("reason") or "")
    if j.get("conflict") or "different" in reason or "disagree" in reason:
      return reason[:1].upper() + reason[1:] + "."
  return None

def conflicting(c) -> bool:
  f = c.facts or {}
  mms = sorted(float(o["mm"]) for o in f.get("thickness_options") or [] if o.get("mm") is not None)
  if len(mms) >= 2 and mms[-1] - mms[0] > CF.SUBSTANTIVE_MM:
    return True
  return bool((f.get(CF.CHOICE_KEY) or {}).get("kind")) or join_conflict(f) is not None

def shown_status(c) -> str:
  return CONFLICT if conflicting(c) else RS.status_of(c)

def points_of(c) -> list:
  pts = (c.geometry or {}).get("points") or []
  return [[round(float(p[0]), 2), round(float(p[1]), 2)] for p in pts if isinstance(p, (list, tuple)) and len(p) >= 2]

def box_of(points: list) -> list | None:
  if not points:
    return None
  xs, ys = [p[0] for p in points], [p[1] for p in points]
  return [min(xs), min(ys), max(xs), max(ys)]

def item_row(c) -> dict:
  f = c.facts or {}
  cls = RS.class_of(c) or "OTHER"
  pts = points_of(c)
  return {"id": c.id, "ckey": c.ckey, "class": cls, "category": c.category, "kind": c.kind, "label": c.label, "mark": c.tag, "status": shown_status(c),
    "reasons": RS.reasons_of(c), "source": c.source, "confidence": _f(c.confidence), "count": int(c.count or 1), "decision": c.decision, "valid": c.status,
    "points": pts, "box": box_of(pts), "missing": list(c.missing or []), "joins": _joins(f), "conflict": _conflict_text(c) if conflicting(c) else None}

def _joins(f: dict) -> list:
  out = []
  for key in JOIN_KEYS:
    j = f.get(key)
    if isinstance(j, dict) and j.get("status"):
      to = j.get("to") or {}
      out.append({"kind": key.replace("_join", ""), "status": j.get("status"), "with": to.get("key") and f"{to.get('key')} (page {to.get('sheet')})" if to else None, "note": j.get("reason")})
  return out

def _conflict_text(c) -> str:
  f = c.facts or {}
  opts = sorted({round(float(o["mm"]) / 25.4, 2) for o in f.get("thickness_options") or [] if o.get("mm") is not None})
  if len(opts) >= 2:
    return "Printed values differ: " + " / ".join(f"{v:g} in" for v in opts)
  return join_conflict(f) or "Two printed values disagree; a choice was recorded."

def pieces(items: list) -> int:
  return sum(max(1, int(i.get("count") or 1)) for i in items)

def count_by_status(items: list) -> dict:
  out = {s: 0 for s in SHOWN}
  for i in items:
    out[i["status"]] = out.get(i["status"], 0) + max(1, int(i.get("count") or 1))
  return out

def _bars(cov_classes: list, items: list) -> list:
  per: dict = {}
  for i in items:
    per.setdefault(i["class"], []).append(i)
  rows = []
  seen = set()
  for r in cov_classes or []:
    cls = r["class"]
    seen.add(cls)
    its = per.get(cls, [])
    rows.append({"class": cls, "expected": bool(r.get("expected", True)), "status": r.get("status"), "reasons": list(r.get("reasons") or []), "no_reader": bool(r.get("no_reader")),
      "count": int(r.get("count") or 0), "by_status": count_by_status(its)})
    
  for cls, its in sorted(per.items()):
    if cls in seen:
      continue
    rows.append({"class": cls, "expected": False, "status": RS.READ if any(i["status"] == RS.READ for i in its) else RS.UNSURE, "reasons": sorted({r for i in its for r in i["reasons"]}),
      "no_reader": False, "count": sum(max(1, i["count"]) for i in its), "by_status": count_by_status(its)})
  return rows

def sheet_card(sheet, ext, cands: list, overrides: int = 0, misreads: int = 0, with_items: bool = False) -> dict:
  meta = sheet.prep_meta or {}
  ident = meta.get("identity") or {}
  cov = ((ext.stats or {}).get("coverage") if ext is not None else None) or {}
  items = [item_row(c) for c in cands if c.decision != "REJECTED"]
  role = cov.get("role") or RS.role_of(ident)
  plan_kind = cov.get("plan_kind") or (RS.plan_kind_of(ident) if role == "PLAN" else None)
  text_type = cov.get("text_type") or None
  bars = _bars(cov.get("classes") or [], items)
  reasons = sheet_reasons(sheet, ext, items, cov, role)
  status = NOT_RUN if ext is None else sheet_status(cov, items, role)
  
  card = {"sheet_id": sheet.id, "page_no": sheet.page_no, "title": sheet.label or ident.get("title"), "role": role, "plan_kind": plan_kind, "floor": ident.get("floor"),
    "discipline": ident.get("discipline"), "scale_text": sheet.scale_text, "scale": scale_state(sheet, ext), "text_type": text_type, "status": status, "ran": ext is not None,
    "width_pt": _f(sheet.width_pt), "height_pt": _f(sheet.height_pt), "rotation": sheet.rotation, "items": pieces(items), "by_status": count_by_status(items), "classes": bars,
    "reasons": reasons, "held": cov.get("held"), "overrides": overrides, "misreads": misreads, "extract_version": None if ext is None else ext.extract_version}
  if with_items:
    card["item_rows"] = items
  return card

def sheet_status(cov: dict, items: list, role: str | None) -> str:
  verdict = cov.get("status")
  if verdict is None:
    return NOTHING_EXPECTED if (role is not None and not items and not cov.get("classes")) else _rollup(items)
  if verdict == RS.NOT_READ and any(i["status"] == RS.READ for i in items):
    return RS.UNSURE
  return verdict

def _rollup(items: list) -> str | None:
  if not items:
    return RS.NOT_READ
  states = {i["status"] for i in items}
  return RS.READ if states == {RS.READ} else RS.NOT_READ if states == {RS.NOT_READ} else RS.UNSURE

def scale_state(sheet, ext) -> str:
  if ext is None:
    return "UNKNOWN"
  if ext.mm_per_pt is None:
    return "MISSING"
  return "UNVERIFIED" if ext.scale_unverified else "SET"

def sheet_reasons(sheet, ext, items: list, cov: dict, role: str | None) -> list:
  out: list = []
  if sheet.prep_status != "READY":
    out.append({"code": "SHEET_NOT_PREPARED", "text": "The sheet has not been prepared yet, so nothing was read from it."})
  if ext is None:
    out.append({"code": "NOT_READ", "text": "The reader has not run on this sheet."})
    return out
  if ext.mm_per_pt is None:
    out.append({"code": "NO_SCALE", "text": "There is no usable scale, so lengths and areas cannot be worked out."})
  elif ext.scale_unverified:
    out.append({"code": "SCALE_UNVERIFIED", "text": "The scale was taken from the sheet text and has not been checked against a known length."})
  if role is None:
    out.append({"code": "ROLE_UNKNOWN", "text": "The sheet's role (plan, schedule, notes, section) was not recognised."})
  if cov.get("text_type") in RS.OUTLINED_TYPES:
    out.append({"code": RS.LABELS_OUTLINED, "text": "The labels on this sheet are drawn as outlines, not text. Marks were read from the outlines."})
  elif cov.get("text_type") == "RASTER":
    out.append({"code": "RASTER_SHEET", "text": "The sheet is a picture, not vector drawing."})
  held = cov.get("held")
  if held:
    unsure = sum((held.get("unsure") or {}).values())
    parts = [f"{held['items']} item(s) of a kind this sheet is not expected to carry were set aside" if held.get("items") else None, f"{unsure} other item(s) are marked unsure for the same reason" if unsure else None]
    out.append({"code": RS.ROLE_BY, "text": "; ".join(p for p in parts if p) + "."})
  not_read = [r for r in cov.get("classes") or [] if r.get("status") == RS.NOT_READ]
  for r in not_read:
    code = (r.get("reasons") or [RS.NO_SYMBOLS])[0]
    out.append({"code": code, "class": r["class"], "text": ("No reader exists for " if r.get("no_reader") else "Nothing was found for ") + r["class"].replace("_", " ").lower() + "."})
  if not items and not not_read:
    if role is not None and not cov.get("classes"):
      out.append({"code": "NOTHING_EXPECTED", "text": f"The reader expects no items from a {role.lower()} sheet, and found none."})
    else:
      out.append({"code": "NO_ITEMS", "text": "The reader ran and found no items on this sheet."})
  return out

def build_report(drawing_id, sheets: list, extractions: dict, cands: dict, overrides: dict, misreads: dict, with_items: bool = False) -> dict:
  cards = [sheet_card(s, extractions.get(s.id), cands.get(s.id, []), overrides.get(s.id, 0), misreads.get(s.id, 0), with_items) for s in sheets]
  total = {s: 0 for s in SHOWN}
  for c in cards:
    for k, v in c["by_status"].items():
      total[k] = total.get(k, 0) + v
  return {"drawing_id": drawing_id, "sheets": cards, "totals": {"sheets": len(cards), "ran": sum(1 for c in cards if c["ran"]), "items": sum(c["items"] for c in cards), "by_status": total,
    "empty_sheets": [c["page_no"] for c in cards if c["items"] == 0]}}

def completeness(cands: list) -> dict:
  by_cat: dict = {}
  for c in cands:
    if c.decision == "REJECTED":
      continue
    e = by_cat.setdefault(c.category, {"element": c.category, "items": 0, "complete": 0, "accepted": 0, "inputs": {}, "work_items": set()})
    e["items"] += 1
    miss = [m for m in (c.missing or []) if m]
    if c.decision == "ACCEPTED":
      e["accepted"] += 1
    if not miss:
      e["complete"] += 1
    if c.suggested_work_item:
      e["work_items"].add(c.suggested_work_item)
    for m in miss:
      i = e["inputs"].setdefault(m, {"input": m, "label": INPUT_NAMES.get(m, m.replace("_", " ")), "state": "MISSING", "items": 0, "marks": []})
      i["items"] += 1
      if c.tag and c.tag not in i["marks"] and len(i["marks"]) < 8:
        i["marks"].append(c.tag)
        
  elements = []
  blocking = []
  for cat in sorted(by_cat):
    e = by_cat[cat]
    inputs = sorted(e["inputs"].values(), key=lambda i: (-i["items"], i["input"]))
    elements.append({"element": cat, "items": e["items"], "complete": e["complete"], "accepted": e["accepted"], "inputs": inputs, "work_items": sorted(e["work_items"]),
      "state": "COMPLETE" if not inputs else "PARTLY" if e["complete"] else "BLOCKED"})
    for i in inputs:
      blocking.append({"element": cat, **i, "blocks": sorted(e["work_items"])})
  blocking.sort(key=lambda b: (-b["items"], b["element"], b["input"]))
  return {"elements": elements, "blocking": blocking, "items": sum(e["items"] for e in elements), "complete": sum(e["complete"] for e in elements)}
