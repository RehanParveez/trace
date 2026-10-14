from __future__ import annotations
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

SOURCE = "pdf_takeoff"
MAX_ROWS_PER_CANDIDATE = 2000

CATEGORY = {
  "COLUMN": {"ifc_type": "IfcColumn", "role": "COLUMN", "discipline": "STRUCTURAL", "material": "Reinforced concrete (assumed)"},
  "FOOTING": {"ifc_type": "IfcFooting", "role": "FOOTING", "discipline": "STRUCTURAL", "material": "Reinforced concrete (assumed)"},
  "BEAM": {"ifc_type": "IfcBeam", "role": "BEAM", "discipline": "STRUCTURAL", "material": "Reinforced concrete (assumed)"},
  "DOOR": {"ifc_type": "IfcDoor", "role": "DOOR", "discipline": "ARCHITECTURAL", "material": "Door (type not stated)"},
  "WINDOW": {"ifc_type": "IfcWindow", "role": "WINDOW", "discipline": "ARCHITECTURAL", "material": "Window (type not stated)"},
  "WALL": {"ifc_type": "IfcWall", "role": "WALL", "discipline": "ARCHITECTURAL", "material": "Brick masonry (assumed)"},
  "ROOM": {"ifc_type": "IfcSpace", "role": "SPACE", "discipline": "ARCHITECTURAL", "material": None},
}

MISSING_TEXT = {
  "height_mm": ("MISSING_HEIGHT", "The height is not on the drawing. Type it when you accept this item."),
  "depth_mm": ("MISSING_DEPTH", "The depth is not on the drawing. Type it when you accept this item."),
  "length_mm": ("MISSING_LENGTH", "The length is not available from the drawing or schedule. Confirm it before accepting this item."),
  "width_mm": ("MISSING_WIDTH", "The width is not available from the drawing or schedule. Confirm it before accepting this item."),
  "thickness_mm": ("MISSING_THICKNESS", "The thickness could not be established reliably from the drawing. Confirm it before measuring this item."),
  "size": ("MISSING_SIZE", "No size was found for this item."),
}

def _d(v, places: int = 4) -> Decimal:
  return Decimal(str(round(float(v), places)))

def row_id(sheet_id, ckey: str, index: int) -> UUID:
  return uuid5(NAMESPACE_URL, f"trace-pdf-register|{sheet_id}|{ckey}|{index}")

def global_id(ckey: str, index: int) -> str:
  return f"PDF:{ckey}:{index}"[:64]

def sheet_title(page_no: int, label: str | None) -> str:
  return f"Sheet {page_no}" + (f" · {label}" if label else "")

def _num(v):
  try:
    f = float(v)
  except (TypeError, ValueError):
    return None
  return f if f == f else None

def _issues(cand) -> tuple[list, str]:
  issues = [{"code": n.get("code"), "severity": n.get("severity", "info"), "message": n.get("message", "")} for n in (cand.notes or [])]
  if cand.decision != "ACCEPTED":
    for need in cand.missing or []:
      code, text = MISSING_TEXT.get(need, ("MISSING_VALUE", f"{need} is not on the drawing."))
      issues.append({"code": code, "severity": "warning", "message": text})
  sev = {i["severity"] for i in issues}
  status = "INVALID" if (cand.status == "INVALID" or "error" in sev) else "WARNING" if ("warning" in sev or cand.status == "WARNING") else "VALID"
  return issues, status

def _positions(cand, n: int) -> list:
  pts = (cand.geometry or {}).get("points") if cand.kind == "COUNT" else None
  mm = _num(cand.mm_per_pt)
  out = []
  for i in range(n):
    p = pts[i] if pts and i < len(pts) else None
    out.append([round(p[0] * mm, 1), round(p[1] * mm, 1)] if (p and mm) else None)
  return out

def _measured_text(cand, page_no: int, measurement) -> str:
  p, facts, codes = cand.params or {}, cand.facts or {}, {n.get("code") for n in (cand.notes or [])}
  parts = []
  from_label = cand.category == "ROOM" and facts.get("outline_from") == "LABEL"
  parts.append(f"Marks counted on sheet {page_no}" if cand.source == "TAG_SCAN" else f"Room label on sheet {page_no}" if from_label else f"Drawn outline on sheet {page_no}")
  cat = cand.category
  
  if cat in ("COLUMN", "FOOTING"):
    parts.append("size from schedule" if "SIZE_FROM_SCHEDULE" in codes else "size from drawing" if facts.get("size_used_mm") else "size not found")
  elif cat == "WALL":
    parts.append("concrete wall (solid fill), centre line x thickness" if facts.get("construction") == "RCC" else "centre line x thickness")
    if facts.get("enclosure") == "TANK":
      parts.append("tank wall")
      
  elif cat == "ROOM":
    parts.append("area inside the wall faces" if facts.get("outline_from") == "WALLS" else "size printed in the label" if from_label else "area of the drawn outline")
  elif cat in ("DOOR", "WINDOW") and facts.get("size_schedule_mm"):
    parts.append("ventilator, size from schedule" if facts.get("opening_kind") == "VENTILATOR" else "size from schedule")
    
  if cat in ("COLUMN", "FOOTING", "WALL"):
    has = p.get("height_mm" if cat == "WALL" else "depth_mm") is not None
    if has and "HEIGHT_FROM_NOTE" in codes:
      parts.append("height from drawing note")
    elif has:
      parts.append("height typed" if cat != "FOOTING" else "depth typed")
    else:
      parts.append("height needed" if cat != "FOOTING" else "depth needed")
  if cat == "WALL" and measurement is None and ("WALL_OPENINGS_INCLUDED" in codes or (facts.get("openings") or {}).get("count")):
    opened = (facts.get("openings") or {})
    parts.append(f"{opened['count']} marked opening{'s' if opened['count'] != 1 else ''} ({opened['area_m2']:.2f} m²) deducted when measured" if opened.get("count") else "openings not yet deducted")
  if cand.decision == "ACCEPTED" and measurement is not None:
    parts.append("measured, " + ("confirmed" if measurement.get("status") == "CONFIRMED" else "draft"))
  else:
    parts.append("found, not measured yet")
  return " · ".join(parts)

def _quantity(cand, n: int, measurement) -> tuple:
  comp = (measurement or {}).get("computed") or {}
  q, unit = _num(comp.get("quantity")), comp.get("unit")
  if measurement is not None and q is not None and unit:
    return _d(q / max(n, 1)), unit, "PDF_MEASURED"
  p, facts, cat = cand.params or {}, cand.facts or {}, cand.category
  if cat in ("COLUMN", "FOOTING"):
    a, b, h = _num(p.get("length_mm")), _num(p.get("width_mm")), _num(p.get("depth_mm"))
    if a and b and h:
      return _d(a * b * h / 1e9), "m3", "PDF_DRAWN"
    return Decimal("1"), "nos", "PDF_COUNT"

  if cat == "WALL":
    length, t, h = _num(facts.get("length_cc_m")), _num(p.get("thickness_mm")), _num(p.get("height_mm"))
    if length and t and h:
      return _d(length * (t / 1000.0) * (h / 1000.0)), "m3", "PDF_DRAWN"
    return _d(length or 0), "m", "PDF_DRAWN"
  if cat == "ROOM":
    return _d(facts.get("area_m2") or 0), "m2", "PDF_DRAWN"
  return Decimal("1"), "nos", "PDF_COUNT"

def _sizes(cand) -> dict:
  p, facts, cat = cand.params or {}, cand.facts or {}, cand.category
  out: dict = {}
  if cat in ("COLUMN", "FOOTING"):
    out = {"length_mm": _num(p.get("length_mm")), "width_mm": _num(p.get("width_mm")), "height_mm": _num(p.get("depth_mm"))}
    if all(out.values()):
      out["volume_mm3"] = out["length_mm"] * out["width_mm"] * out["height_mm"]
      
  elif cat == "WALL":
    length = _num(facts.get("length_cc_m"))
    out = {"length_mm": length * 1000.0 if length else None, "thickness_mm": _num(p.get("thickness_mm")), "height_mm": _num(p.get("height_mm"))}
    if out["length_mm"] and out["thickness_mm"] and out["height_mm"]:
      out["volume_mm3"] = out["length_mm"] * out["thickness_mm"] * out["height_mm"]
      
  elif cat in ("DOOR", "WINDOW"):
    s = facts.get("size_schedule_mm")
    if s and len(s) >= 2:
      w, h = _num(s[0]), _num(s[1])
      out = {"width_mm": w, "height_mm": h, "area_mm2": (w * h) if (w and h) else None}
  elif cat == "ROOM":
    a = _num(facts.get("area_m2"))
    out = {"area_mm2": a * 1e6 if a else None}
  return {k: _d(v, 3) for k, v in out.items() if v}

def _name(cand, i: int, n: int) -> str:
  if cand.category == "ROOM":
    return (cand.facts or {}).get("name") or "Room (no name found)"
  if cand.category == "WALL":
    return cand.label
  base = cand.tag or cand.label
  return f"{base} ({i + 1} of {n})" if n > 1 else base

def rows_for_candidate(cand, *, sheet, level_id, level_name: str | None, measurement=None, also_on=()) -> list:

  spec = CATEGORY.get(cand.category)
  if spec is None or cand.decision == "REJECTED":
    return []
  n = 1 if cand.category in ("WALL", "ROOM") else max(1, min(int(cand.count or 1), MAX_ROWS_PER_CANDIDATE))
  issues, status = _issues(cand)
  also_on = sorted(set(also_on))
  
  if also_on:
    issues.append({"code": "SAME_MARK_ON_OTHER_SHEET", "severity": "info",
      "message": "This mark is also on sheet " + ", ".join(str(x) for x in also_on) + ". It is listed once here. Measure it once, not on every sheet."})
  qty, unit, qsrc = _quantity(cand, n, measurement)
  sizes = _sizes(cand)
  measured = measurement is not None and cand.decision == "ACCEPTED"
  title = sheet_title(sheet.page_no, getattr(sheet, "label", None))
  text = _measured_text(cand, sheet.page_no, measurement)
  
  if also_on:
    text += " · also marked on sheet " + ", ".join(str(x) for x in also_on)
  pos = _positions(cand, n)
  out = []
  
  for i in range(n):
    props = {"source": SOURCE, "_pdf": {
      "candidate_id": str(cand.id), "ckey": cand.ckey, "sheet_id": str(sheet.id), "page_no": sheet.page_no, "sheet": title,
      "level_name": level_name, "instance": i + 1, "instances": n, "review": cand.decision, "mode": "PDF_MEASURED" if measured else "PDF_FOUND",
      "measured_as": text, "work_item": cand.suggested_work_item, "tag": cand.tag, "position_mm": pos[i],
      "measurement_id": str(measurement["id"]) if measured else None,
      "measurement_status": measurement.get("status") if measured else None,
      "missing": [] if cand.decision == "ACCEPTED" else list(cand.missing or []), "also_on_sheets": also_on,
    }}
    
    if cand.category == "ROOM":
      props["_pdf"]["perimeter_m"] = (cand.facts or {}).get("perimeter_m")
    opening_kind = (cand.facts or {}).get("opening_kind") if cand.category in ("DOOR", "WINDOW") else None
    if opening_kind:
      props["_pdf"]["opening_kind"] = opening_kind
    row = {
      "id": row_id(sheet.id, cand.ckey, i), "ifc_global_id": global_id(cand.ckey, i), "ifc_type": spec["ifc_type"],
      "name": _name(cand, i, n)[:500], "raw_material_text": "Reinforced concrete wall (retaining)" if (cand.facts or {}).get("construction") == "RCC" else spec["material"], "unit": unit, "quantity": qty, "properties": props,
      "discipline": spec["discipline"], "structural_role": spec["role"], "classification_source": "PDF_EXTRACT",
      "classification_confidence": _d(cand.confidence or 0), "quantity_source": qsrc, "level_id": level_id,
      "geometry_kind": None, "normalization_status": status, "normalization_issues": issues,
      "type_mark": cand.tag, "type_name": "Ventilator" if opening_kind == "VENTILATOR" else None, "level_name": level_name or title,
    }
    row.update(sizes)
    out.append(row)
  return out

SHARED_MARKS = ("COLUMN", "FOOTING", "BEAM", "DOOR", "WINDOW") 

def _primary(candidates, sheets: dict) -> tuple:
  groups: dict = {}
  for c in candidates:
    if c.category in SHARED_MARKS and c.tag and c.decision != "REJECTED" and c.sheet_id in sheets:
      groups.setdefault((c.category, c.tag.strip().upper(), getattr(sheets[c.sheet_id], "level_id", None)), []).append(c)
  also, hidden = {}, set()
  for items in groups.values():
    if len(items) < 2:
      continue
  
    items.sort(key=lambda c: (c.decision != "ACCEPTED", -int(c.count or 0), len(c.missing or []), sheets[c.sheet_id].page_no))
    owner = items[0]
    also[owner.id] = [sheets[c.sheet_id].page_no for c in items[1:] if sheets[c.sheet_id].page_no != sheets[owner.sheet_id].page_no]
    hidden.update(c.id for c in items[1:])
  return also, hidden

def build_rows(candidates, sheets: dict, measurements: dict, levels: dict) -> list:
  
  also, hidden = _primary(candidates, sheets)
  out = []
  for cand in candidates:
    sheet = sheets.get(cand.sheet_id)
    if sheet is None or cand.id in hidden:
      continue
    m = measurements.get(cand.measurement_id) if cand.measurement_id else None
    lvl = getattr(sheet, "level_id", None)
    out.extend(rows_for_candidate(cand, sheet=sheet, level_id=lvl, level_name=levels.get(lvl) if lvl else None, measurement=m,
      also_on=also.get(cand.id, ())))
  return out

def is_pdf_row(row) -> bool:
  return ((getattr(row, "properties", None) or {}).get("source")) == SOURCE

def pdf_meta(row) -> dict:
  return ((getattr(row, "properties", None) or {}).get("_pdf")) or {}
