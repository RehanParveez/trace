from __future__ import annotations
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5
from app.modules.drawings_boq.takeoff.evidence import evidence_for
from app.modules.drawings_boq.takeoff.levels import view_level_id
from app.modules.drawings_boq.takeoff import stair_twins
from app.modules.drawings_boq.takeoff import placement as PL
from app.modules.drawings_boq.takeoff.extract import slab_openings as SO

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
  "SLAB": {"ifc_type": "IfcSlab", "role": "SLAB", "discipline": "STRUCTURAL", "material": "Reinforced concrete (assumed)"},
  "LINTEL": {"ifc_type": "IfcBeam", "role": "LINTEL", "discipline": "STRUCTURAL", "material": "Reinforced concrete (assumed)"},
  "STAIR": {"ifc_type": "IfcStair", "role": "STAIR", "discipline": "STRUCTURAL", "material": "Reinforced concrete (assumed)"},
}

SITE_SPEC = {
  "OHWT": {"ifc_type": "IfcTank", "role": "TANK", "discipline": "STRUCTURAL", "material": "Reinforced concrete (assumed)", "type_name": "Over head water tank"},
  "UGWT": {"ifc_type": "IfcTank", "role": "TANK", "discipline": "STRUCTURAL", "material": "Reinforced concrete (assumed)", "type_name": "Underground water tank"},
  "SEPTIC": {"ifc_type": "IfcTank", "role": "TANK", "discipline": "STRUCTURAL", "material": "Reinforced concrete (assumed)", "type_name": "Septic tank"},
  "BOUNDARY_WALL": {"ifc_type": "IfcWall", "role": "WALL", "discipline": "ARCHITECTURAL", "material": "Brick masonry (assumed)", "type_name": "Boundary wall"},
  "GATE": {"ifc_type": "IfcDoor", "role": "GATE", "discipline": "ARCHITECTURAL", "material": "Gate (type not stated)", "type_name": "Gate"},
  "PORCH_RAMP": {"ifc_type": "IfcRamp", "role": "RAMP", "discipline": "ARCHITECTURAL", "material": "Reinforced concrete (assumed)", "type_name": "Porch ramp"},
}

def _spec(cand):
  """The IFC type, role, discipline and material of the row of an item. An item outside the building has one per kind (a tank, the boundary wall, the gate)."""
  if cand.category == "SITE":
    return SITE_SPEC.get((cand.facts or {}).get("site_kind"))
  return CATEGORY.get(cand.category)

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
  if cand.category == "SLAB":
    return [None] * n
  pts = (cand.geometry or {}).get("points") if cand.kind == "COUNT" else None
  mm = _num(cand.mm_per_pt)
  out = []
  for i in range(n):
    p = pts[i] if pts and i < len(pts) else None
    out.append([round(p[0] * mm, 1), round(p[1] * mm, 1)] if (p and mm) else None)
  return out

def _slab_text(cand, page_no: int, measurement) -> str:
  p, facts, codes = cand.params or {}, cand.facts or {}, {n.get("code") for n in (cand.notes or [])}
  pages = ", ".join(str(x) for x in (facts.get("area_pages") or []))
  parts = [f"Covered area of the floor from the area table{' on sheet ' + pages if pages else ''}"]
  parts.append("length x width printed with it" if facts.get("dims_mm") else "length and width not printed")
  if (facts.get("projections") or {}).get("applied"):
    parts.append(f"plus roof projections printed on the floor plan ({facts.get('projection_area_m2', 0):.2f} m2)")
  if facts.get("openings"):
    n_big = sum(1 for o in facts["openings"] if o.get("deduct"))
    parts.append(f"less {facts.get('openings_area_m2', 0):.2f} m2 of openings ({n_big} bigger than 0.1 m2: stair well, shaft or duct found on the plans)" if n_big else
      "openings found on the plans are 0.1 m2 or smaller, not deducted")
  if p.get("depth_mm") is None:
    parts.append("thickness needed")
  elif facts.get("thickness_source") == "OTHER_SHEET":
        
    parts.append("thickness printed on another sheet")
  elif facts.get("thickness_source") == "TYPED":
    parts.append("thickness typed")
  elif facts.get("thickness_source") == "CHOSEN":
    parts.append("thickness chosen by you between the ones the drawing prints")
  elif facts.get("thickness_source") == "POLICY":
    parts.append("thickness picked by the policy between the ones the drawing prints")
  elif facts.get("thickness_source") == "SECTION_LABEL":
    parts.append("thickness labelled on the sections of the drawing (the plan's general slab note prints a different one)")
  elif "SLAB_THICKNESS_DISAGREES" in codes:
    parts.append(f"thickness from the slab note on sheet {page_no} (another sheet prints a different one)")
  else:
    parts.append(f"thickness from the slab note on sheet {page_no}")
  if cand.decision == "ACCEPTED" and measurement is not None:
    parts.append("measured, " + ("confirmed" if measurement.get("status") == "CONFIRMED" else "draft"))
  else:
    parts.append("found, not measured yet")
  return " · ".join(parts)
def _lintel_text(cand, page_no: int, measurement) -> str:
  p, facts = cand.params or {}, cand.facts or {}
  parts = [f"Opening marks counted on sheet {page_no}"]
  parts.append("section from the lintel table, length = opening width + bearing each end (bearing assumed)" if p.get("depth_mm") is not None else "span wider than the lintel table, section needed")
  if cand.decision == "ACCEPTED" and measurement is not None:
    parts.append("measured, " + ("confirmed" if measurement.get("status") == "CONFIRMED" else "draft"))
  else:
    parts.append("found, not measured yet")
  return " · ".join(parts)

def _beam_text(cand, page_no: int, measurement) -> str:
  p, facts = cand.params or {}, cand.facts or {}
  if facts.get("from_strips"):
    depth = "depth from the section " + str(facts["section_mark"]) if facts.get("section_mark") else "depth typed" if p.get("depth_mm") is not None else "depth needed"
    parts = [f"Hatched beam strips measured on sheet {page_no}", f"{facts.get('strip_count', 0)} strips, {facts.get('length_m', 0):g} m along their centre line, {(facts.get('beam_width_mm') or 0) / 25.4:g} in wide", depth]
  else:
    role = {"PLINTH": "plinth beam", "BAND": "tie band at lintel level"}.get(facts.get("beam_role"), "roof beam")
    parts = [f"Brick walls measured on sheet {page_no}", f"{role} laid over {facts.get('wall_count', 0)} walls of {(facts.get('wall_thickness_mm') or 0) / 25.4:g} in, as wide as the wall",
      "depth typed" if p.get("depth_mm") is not None else "depth needed"]
  if cand.decision == "ACCEPTED" and measurement is not None:
    parts.append("measured, " + ("confirmed" if measurement.get("status") == "CONFIRMED" else "draft"))
  else:
    parts.append("found, not measured yet")
  return " · ".join(parts)

def _stair_text(cand, page_no: int, measurement) -> str:
  p, facts = cand.params or {}, cand.facts or {}
  parts = [f"Stair named on the plan of sheet {page_no}"]
  width = f", {(facts.get('stair_width_mm') or 0) / 25.4:g} in wide as printed beside the flight" if facts.get("width_source") == "PRINTED_BESIDE" else ""
  parts.append(f"{facts.get('steps')} steps{width}, plan run x width x equivalent thickness (waist {'printed' if facts.get('waist_source') == 'PRINTED' else 'assumed'})" if p.get("depth_mm") is not None else "stair details incomplete")
  if facts.get("landings"):
    parts.append(f"plus {len(facts['landings'])} landing{'s' if len(facts['landings']) > 1 else ''} printed beside it ({facts.get('landings_area_m2', 0):.2f} m2, flat slab of the waist thickness)")
  if cand.decision == "ACCEPTED" and measurement is not None:
    parts.append("measured, " + ("confirmed" if measurement.get("status") == "CONFIRMED" else "draft"))
  else:
    parts.append("found, not measured yet")
  return " · ".join(parts)

def _site_text(cand, page_no: int, measurement) -> str:
  p, facts = cand.params or {}, cand.facts or {}
  kind = facts.get("site_kind")
  parts = [f"{SITE_SPEC.get(kind, {}).get('type_name', 'Site item')} named on sheet {page_no}"]
  
  if kind in ("OHWT", "UGWT", "SEPTIC"):
    parts.append("concrete of the walls, top slab and bottom slab (outside length x width x equivalent depth)" if p.get("depth_mm") is not None else "outside sizes and wall thickness needed")
  elif kind == "BOUNDARY_WALL":
    got = [w for w, v in (("length", p.get("length_mm")), ("height", p.get("depth_mm")), ("thickness", p.get("width_mm"))) if v is None]
    parts.append("length x height x thickness" + (", gate taken out" if facts.get("gate_deducted") else "") + (f", {' and '.join(got)} needed" if got else ""))
  elif kind == "GATE":
    parts.append("width x height of the gate piece of the boundary wall elevation" if p.get("width_mm") is not None else "gate height needed")
  elif kind == "PORCH_RAMP":
    parts.append("length x width x thickness of the ramp slab" if p.get("depth_mm") is not None else "length, width and thickness needed")
  if cand.decision == "ACCEPTED" and measurement is not None:
    parts.append("measured, " + ("confirmed" if measurement.get("status") == "CONFIRMED" else "draft"))
  else:
    parts.append("found, not measured yet")
  return " · ".join(parts)

def _measured_text(cand, page_no: int, measurement) -> str:
  if cand.category == "SITE":
    return _site_text(cand, page_no, measurement)
  if cand.category == "STAIR":
    return _stair_text(cand, page_no, measurement)
  if cand.category == "SLAB":
    return _slab_text(cand, page_no, measurement)
  if cand.category == "LINTEL":
    return _lintel_text(cand, page_no, measurement)
  if _wall_beam(cand):
    return _beam_text(cand, page_no, measurement)
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
    if has and "HEIGHT_FROM_SECTION" in codes:
      parts.append("height from the building section")
    elif has and "HEIGHT_FROM_NOTE" in codes:
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
  if cat == "SITE":
    a, b, h = _num(p.get("length_mm")), _num(p.get("width_mm")), _num(p.get("depth_mm"))
    if facts.get("site_kind") == "GATE":
      return (_d(a * b / 1e6), "m2", "PDF_DRAWN") if a and b else (Decimal("1"), "nos", "PDF_COUNT")
    if a and b and h:
      return _d(a * b * h / 1e9), "m3", "PDF_DRAWN"
    return Decimal("1"), "nos", "PDF_COUNT"

  if cat in ("COLUMN", "FOOTING", "LINTEL", "STAIR") or _wall_beam(cand):
    a, b, h = _num(p.get("length_mm")), _num(p.get("width_mm")), _num(p.get("depth_mm"))
    if a and b and h:
      more = SO.landing_m3(facts, facts.get("waist_mm")) if cat == "STAIR" else 0.0
      return _d(a * b * h / 1e9 + more), "m3", "PDF_DRAWN"
    if _wall_beam(cand):
      return _d((a or 0) / 1000.0), "m", "PDF_DRAWN"
    return Decimal("1"), "nos", "PDF_COUNT"

  if cat == "WALL":
    length, t, h = _num(facts.get("length_cc_m")), _num(p.get("thickness_mm")), _num(p.get("height_mm"))
    from_section = any(n.get("code") == "HEIGHT_FROM_SECTION" for n in (cand.notes or []))
    if length and t and h and not from_section:
      return _d(length * (t / 1000.0) * (h / 1000.0)), "m3", "PDF_DRAWN"
    return _d(length or 0), "m", "PDF_DRAWN"
  if cat == "ROOM":
    return _d(facts.get("area_m2") or 0), "m2", "PDF_DRAWN"
  if cat == "SLAB":
    a, b, t = _num(p.get("length_mm")), _num(p.get("width_mm")), _num(p.get("depth_mm"))
    if a and b and t:
      return _d(SO.net_slab_m3(a * b * t / 1e9, facts, t)), "m3", "PDF_DRAWN"
    return _d(facts.get("area_m2") or 0), "m2", "PDF_DRAWN"
  return Decimal("1"), "nos", "PDF_COUNT"

def _sizes(cand) -> dict:
  p, facts, cat = cand.params or {}, cand.facts or {}, cand.category
  out: dict = {}
  if cat == "SITE":
    kind, a, b, h = facts.get("site_kind"), _num(p.get("length_mm")), _num(p.get("width_mm")), _num(p.get("depth_mm"))
    sz = facts.get("sizes_mm") or {}
    if kind == "GATE":
      out = {"width_mm": a, "height_mm": b, "area_mm2": (a * b) if (a and b) else None}
    elif kind == "BOUNDARY_WALL":
      out = {"length_mm": a, "thickness_mm": b, "height_mm": h}
      if a and b and h:
        out["volume_mm3"] = a * b * h
    elif kind == "PORCH_RAMP":
      out = {"length_mm": a, "width_mm": b, "thickness_mm": h}
      if a and b and h:
        out["volume_mm3"] = a * b * h
    else:
      out = {"length_mm": a, "width_mm": b, "height_mm": _num(sz.get("height_mm")), "thickness_mm": _num(sz.get("thickness_mm"))}
      if a and b and h:
        out["volume_mm3"] = a * b * h
  elif cat in ("COLUMN", "FOOTING", "LINTEL", "STAIR") or _wall_beam(cand):
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
  elif cat == "SLAB":
    a, b, t = _num(p.get("length_mm")), _num(p.get("width_mm")), _num(p.get("depth_mm"))
    area = _num(facts.get("area_m2"))
    out = {"length_mm": a, "width_mm": b, "thickness_mm": t, "area_mm2": (a * b) if (a and b) else (area * 1e6 if area else None)}
    if a and b and t:
      out["volume_mm3"] = a * b * t
  return {k: _d(v, 3) for k, v in out.items() if v}

def _wall_beam(cand) -> bool:
  return cand.category == "BEAM" and ((cand.facts or {}).get("derived_from") == "WALLS" or bool((cand.facts or {}).get("from_strips")))

def _name(cand, i: int, n: int) -> str:
  if cand.category == "ROOM":
    return (cand.facts or {}).get("name") or "Room (no name found)"
  if cand.category in ("WALL", "SLAB", "SITE") or _wall_beam(cand):
    return cand.label
  base = cand.tag or cand.label
  return f"{base} ({i + 1} of {n})" if n > 1 else base

def rows_for_candidate(cand, *, sheet, level_id, level_name: str | None, measurement=None, also_on=(), frame_positions=None, floors=None, floor_key=None, footing=None) -> list:

  spec = _spec(cand)
  if spec is None or cand.decision == "REJECTED" or (cand.facts or {}).get("foundation_item"):
    return []
  n = 1 if cand.category in ("WALL", "ROOM", "SLAB") else max(1, min(int(cand.count or 1), MAX_ROWS_PER_CANDIDATE))
  issues, status = _issues(cand)
  also_on = sorted(set(also_on))
  
  if also_on and cand.category == "STAIR":
    issues.append({"code": "STAIR_DRAWN_ON_OTHER_SHEET", "severity": "info",
      "message": "This staircase is also drawn as a DN flight on sheet " + ", ".join(str(x) for x in also_on) + ". It is one stair, listed once here. Measure it once."})
  elif also_on:
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
  evidence = evidence_for(cand)
  zr = PL.z_of(cand, floors or {}, floor_key, footing)
  out = []
  
  for i in range(n):
    props = {"source": SOURCE, "_pdf": {
      "candidate_id": str(cand.id), "ckey": cand.ckey, "sheet_id": str(sheet.id), "page_no": sheet.page_no, "sheet": title,
      "level_name": level_name, "instance": i + 1, "instances": n, "review": cand.decision, "mode": "PDF_MEASURED" if measured else "PDF_FOUND",
      "measured_as": text, "work_item": cand.suggested_work_item, "tag": cand.tag, "position_mm": pos[i],
      "measurement_id": str(measurement["id"]) if measured else None,
      "measurement_status": measurement.get("status") if measured else None,
      "missing": [] if cand.decision == "ACCEPTED" else list(cand.missing or []), "also_on_sheets": also_on, "evidence": evidence,
    }}
    
    placed = (frame_positions or {}).get((str(measurement["id"]), i)) if measured else None
    if placed:
      props["_pdf"]["frame"] = {"view": placed["view"], "position_mm": placed["position_mm"], "grade": placed["grade"], "method": placed["method"]}
    where = PL.fields(cand, sizes, placed, zr, floor_key)
    props["_pdf"].update(where["meta"])
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
      "type_mark": cand.tag, "type_name": spec.get("type_name") if cand.category == "SITE" else "Ventilator" if opening_kind == "VENTILATOR" else "Lintel" if cand.category == "LINTEL" else "Staircase" if cand.category == "STAIR" else ("Beam" if (cand.facts or {}).get("from_strips") else "Beam over walls") if _wall_beam(cand) else None, "level_name": level_name or title,
    }
    row.update(sizes)
    row.update(where["row"])
    out.append(row)
  return out

def level_of(cand, sheet):
  """The level of an item: the floor of the drawing it was read from on a sheet that shows several floors, otherwise the sheet's own level."""
  return view_level_id(cand) or getattr(sheet, "level_id", None)

SHARED_MARKS = ("COLUMN", "FOOTING", "BEAM", "DOOR", "WINDOW", "SLAB", "LINTEL", "SITE")

def _primary(candidates, sheets: dict) -> tuple:
  groups: dict = {}
  for c in candidates:
    if c.category in SHARED_MARKS and c.tag and c.decision != "REJECTED" and c.sheet_id in sheets:
      groups.setdefault((c.category, c.tag.strip().upper(), None if c.category == "SITE" else level_of(c, sheets[c.sheet_id])), []).append(c)
  also, hidden = {}, set()
  for items in groups.values():
    if len(items) < 2:
      continue
  
    items.sort(key=lambda c: (c.decision != "ACCEPTED", -int(c.count or 0), len(c.missing or []), not (c.facts or {}).get("tank_drawings"), sheets[c.sheet_id].page_no))
    owner = items[0]
    also[owner.id] = [sheets[c.sheet_id].page_no for c in items[1:] if sheets[c.sheet_id].page_no != sheets[owner.sheet_id].page_no]
    hidden.update(c.id for c in items[1:])
  return also, hidden

def build_rows(candidates, sheets: dict, measurements: dict, levels: dict, frame_positions: dict | None = None, floors: dict | None = None,
  floor_of: dict | None = None, footing=None) -> list:
  
  also, hidden = _primary(candidates, sheets)
  stair_also, stair_hidden = stair_twins.twins(candidates, sheets)
  for k, v in stair_also.items():
    also[k] = sorted(set(also.get(k, [])) | set(v))
  hidden |= stair_hidden
  out = []
  for cand in candidates:
    sheet = sheets.get(cand.sheet_id)
    if sheet is None or cand.id in hidden:
      continue
    m = measurements.get(cand.measurement_id) if cand.measurement_id else None
    lvl = level_of(cand, sheet)
    out.extend(rows_for_candidate(cand, sheet=sheet, level_id=lvl, level_name=levels.get(lvl) if lvl else None, measurement=m,
      also_on=also.get(cand.id, ()), frame_positions=frame_positions, floors=floors, floor_key=(floor_of or {}).get(lvl) if lvl else None, footing=footing))
  return out

def is_pdf_row(row) -> bool:
  return ((getattr(row, "properties", None) or {}).get("source")) == SOURCE

def pdf_meta(row) -> dict:
  return ((getattr(row, "properties", None) or {}).get("_pdf")) or {}
