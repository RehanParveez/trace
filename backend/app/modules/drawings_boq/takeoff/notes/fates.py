from __future__ import annotations
from app.modules.drawings_boq.takeoff.prep import printed_params as PP

USED, GRADE, CHECKED, LISTED, CONFLICT, NOT_MADE = "USED", "GRADE", "CHECKED", "LISTED", "CONFLICT", "NOT_MADE"
FATES = (USED, GRADE, CHECKED, LISTED, CONFLICT, NOT_MADE)
FATE_TEXT = {USED: "Used in the calculation", GRADE: "Given to members as their grade", CHECKED: "Compared with the drawing, nothing changed", LISTED: "Listed only, no quantity uses it",
  CONFLICT: "Not applied, the drawing disagrees with it", NOT_MADE: "No item is made from it"}

TOL_MM = 10.0
SAME_MM = 1.0
MM_INCH = 25.4
MM_FOOT = 304.8

PARAM_TEXT = {"steel_cover_slab_mm": "steel cover of slabs", "steel_cover_beam_mm": "steel cover of beams", "steel_cover_column_mm": "steel cover of columns",
  "steel_cover_footing_mm": "steel cover of footings", "steel_cover_wall_mm": "steel cover of walls", PP.PCC_PARAM: "thickness of the plain concrete bed",
  PP.FILL_PARAM: "thickness of a compacted fill layer", PP.PLASTER_PARAM: "plaster thickness", PP.DPC_PARAM: "damp-proof course thickness",
  PP.SOIL_DEPTH_PARAM: "depth of soil stabilisation", PP.SOIL_CEMENT_PARAM: "cement in the stabilised soil", PP.STAB_PRINTED_PARAM: "soil stabilisation printed",
  PP.STAB_ON_PARAM: "soil stabilisation switched on", PP.LAP_PARAM: "lap of bars"}
KIND_PARAM = {"FILL_LAYER": (PP.FILL_PARAM, None), "PLASTER_THICKNESS": (PP.PLASTER_PARAM, "cement mortar plaster"), "DPC_THICKNESS": (PP.DPC_PARAM, None),
  "PCC_THICKNESS": (PP.PCC_PARAM, "pcc bed")}
NO_QUANTITY = {"BEARING_CAPACITY": "It is a design figure for the footings. The footings measured are the ones drawn, so no quantity depends on it.",
  "COMPACTION_PCT": "It is a quality requirement for the filling. The filling is measured by volume, so no quantity depends on it.",
  "BRICK_COLUMN": "No item takes its size from this note. The columns measured are the ones on the plans.",
  "DEPRESSED_SLAB": "The slab is lowered in an area that the drawing does not give a size to, so no slab area or depth is changed by it. Check the bath and toilet slabs against it.",
  "FLOOR_DROP": "It lowers the finished floor (the tiling level) of the rooms it names. The floor finishes are measured by area, so no quantity depends on it."}

def inch_text(mm: float) -> str:
  eighths = round(float(mm) / MM_INCH * 8)
  whole, rest = divmod(eighths, 8)
  frac = ""
  if rest:
    g = 4 if rest % 4 == 0 else 2 if rest % 2 == 0 else 1
    frac = f"{rest // g}/{8 // g}"
  return f'{whole} {frac}"' if whole and frac else f'{frac}"' if frac else f'{whole}"'

def foot_text(mm: float) -> str:
  eighths = round(float(mm) / MM_INCH * 8)
  feet, left = divmod(eighths, 96)
  whole, rest = divmod(left, 8)
  frac = ""
  if rest:
    g = 4 if rest % 4 == 0 else 2 if rest % 2 == 0 else 1
    frac = f" {rest // g}/{8 // g}"
  return f"{feet}'-{whole}{frac}\""

def _pages(rows: list) -> list:
  return sorted({int(p) for r in rows for p in (r.get("pages") or [])})

def _row(it: dict, fate: str, why: str, param: str | None = None, **extra) -> dict:
  return {"kind": it.get("kind"), "text": it.get("text"), "pages": sorted(it.get("pages") or []), "count": int(it.get("count", 1)), "value_mm": it.get("value_mm"),
    "value": it.get("value"), "scope": it.get("scope"), "heading": it.get("heading"), "fate": fate, "param": param, "param_text": PARAM_TEXT.get(param) if param else None, "why": why, **extra}

def _flag(code: str, severity: str, title: str, message: str, pages: list) -> dict:
  return {"code": code, "severity": severity, "title": title, "message": message, "pages": sorted({int(p) for p in pages})}

def _param_row(it: dict, name: str, params: dict, clash: set) -> dict:
  if name in clash:
    return _row(it, CONFLICT, "The drawing prints this with different values, so none is applied. Type the value you want.", name)
  if name in params:
    return _row(it, USED, f"Set the {PARAM_TEXT.get(name, name)} for the calculation.", name)
  return _row(it, LISTED, "It does not reach the calculation.", name)

def _cover(it: dict, params: dict, clash: set) -> dict:
  scope = str(it.get("scope") or "")
  name = PP.COVER_PARAM_OF.get(scope)
  where = str(it.get("where") or "")
  if name is None:
    return _row(it, LISTED, f"The calculation has no cover for '{scope}'.")
  if scope == "slab" and "top" in where and "bottom" not in where:
    return _row(it, LISTED, "The calculation has one cover for a slab, the bottom cover. The top cover is not used.", name)
  return _param_row(it, name, params, clash)

def _soil(it: dict, params: dict, clash: set) -> dict:
  kind = it["kind"]
  if kind == "SOIL_STAB_NOTE":
    return _row(it, USED, "Soil stabilisation is printed, so it is listed with its cement.", PP.STAB_PRINTED_PARAM)
  if kind == "SOIL_STAB_CONDITION":
    on = PP.STAB_ON_PARAM in params
    return _row(it, USED if on else LISTED, "Stabilisation is switched on." if on else "The note is conditional, so stabilisation stays off until you switch it on.", PP.STAB_ON_PARAM)
  if kind == "STAB_CEMENT_PCT":
    return _param_row(it, PP.STAB_CEMENT_PARAM, params, clash)

  name = PP.SOIL_CEMENT_PARAM
  fate = _param_row(it, name, params, clash)
  if it.get("value_mm") is not None and PP.SOIL_DEPTH_PARAM in params and fate["fate"] == USED:
    fate["param"], fate["param_text"] = PP.SOIL_DEPTH_PARAM, PARAM_TEXT[PP.SOIL_DEPTH_PARAM]
  return fate

def _walls(rows: list, cands: list, flags: list) -> list:
  walls = [c for c in cands if c.get("category") == "WALL" and (c.get("facts") or {}).get("construction") == "RCC"]
  drawn = sorted(float(c["facts"]["thickness_mm"]) for c in walls if c["facts"].get("thickness_mm"))
  used = sorted({round(float(c["facts"]["thickness_used_mm"]), 1) for c in walls if c["facts"].get("thickness_used_mm")})

  out = []
  for it in rows:
    v = float(it["value_mm"])
    if not drawn:
      out.append(_row(it, LISTED, "No concrete wall has been read yet, so there is nothing to compare it with."))
      continue
    near = [d for d in drawn if abs(d - v) <= TOL_MM]
    span = f"{drawn[0]:g} to {drawn[-1]:g} mm" if drawn[0] != drawn[-1] else f"{drawn[0]:g} mm"
    if near:
      at = ", ".join(f"{u:g} mm" for u in used)
      out.append(_row(it, CHECKED, f"{len(near)} of {len(drawn)} concrete walls are drawn within {TOL_MM:g} mm of it ({span}). They are measured at {at}."))
    else:
      msg = f"The concrete walls are drawn {span} thick; the note says {inch_text(v)} ({v:g} mm). They are measured at {', '.join(f'{u:g} mm' for u in used)}."
      out.append(_row(it, CONFLICT, msg))
      flags.append(_flag("RCC_WALL_NOTE_DIFFERS", "warning", "Concrete wall thickness", msg, it.get("pages") or []))
  return out

def _stairs(rows: list, cands: list, flags: list) -> list:
  stairs = [c for c in cands if c.get("category") == "STAIR" and (c.get("facts") or {}).get("stair_width_mm")]
  noted = [float(r["value_mm"]) for r in rows]
  out = []
  for it in rows:
    v = float(it["value_mm"])
    same = [c for c in stairs if abs(float(c["facts"]["stair_width_mm"]) - v) <= SAME_MM]
    if same:
      out.append(_row(it, USED, f"{sum(int(c.get('count', 1)) for c in same)} stair items take this width."))
    elif stairs:
      out.append(_row(it, CONFLICT, "No stair is measured at this width."))
    else:
      out.append(_row(it, LISTED, "No stair has been read yet."))
  if rows:
    by: dict = {}
    for c in stairs:
      w = round(float(c["facts"]["stair_width_mm"]), 1)
      if any(abs(w - n) <= SAME_MM for n in noted):
        continue

      by.setdefault((c.get("page_no"), w, str(c["facts"].get("width_source") or "")), 0)
      by[(c.get("page_no"), w, str(c["facts"].get("width_source") or ""))] += int(c.get("count", 1))
    printed_on = _pages(rows)
    said = " and ".join(f"'{r.get('text')}'" for r in rows)
    for (page, w, source), n in sorted(by.items(), key=lambda kv: (kv[0][0] or 0, kv[0][1])):
      how = {"PRINTED_BESIDE": "the width printed beside it", "STAIR_DETAIL": "the stair detail", "DRAWN": "the width drawn"}.get(source, "its own reading")
      flags.append(_flag("STAIR_WIDTH_DIFFERS", "info" if source == "PRINTED_BESIDE" else "warning", "Stair width",
        f"{'A stair' if n == 1 else f'{n} stair items'} on page {page} {'is' if n == 1 else 'are'} measured at {foot_text(w)} ({w:g} mm) from {how}, while the drawing prints {said} on page {', '.join(map(str, printed_on))}.",
        [page or 0] + printed_on))
  return out

def _slabs(rows: list, cands: list, flags: list) -> list:
  slabs = [c for c in cands if c.get("category") == "SLAB" and (c.get("facts") or {}).get("thickness_mm")]
  used = sorted({round(float(c["facts"]["thickness_mm"]), 1) for c in slabs})
  warned = any("SLAB_THICKNESS_DISAGREES" in (c.get("codes") or ()) for c in slabs)

  out = []
  for it in rows:
    v = float(it["value_mm"])
    if not slabs:
      out.append(_row(it, LISTED, "No slab has been read yet."))
    elif any(abs(u - v) <= SAME_MM for u in used):
      out.append(_row(it, USED, "The slab items are measured at this thickness."))
    else:
      at = ", ".join(f"{u:g} mm" for u in used)
      msg = f"The drawing prints a slab {inch_text(v)} ({v:g} mm) thick ({it.get('scope')}, page {', '.join(map(str, it.get('pages') or []))}); the slab items are measured at {at}." + (
        " The slab item carries a warning about it." if warned else "")
      out.append(_row(it, CONFLICT, msg))
      flags.append(_flag("SLAB_NOTE_NOT_USED", "warning", "Slab thickness", msg, it.get("pages") or []))
  return out

ROOF_HEADINGS = ("TERRACE", "ROOF", "PORCH_ROOF", "MUMTY")
NO_ROOF_ITEM = "The layers under a roof heading go on the roof treatment item, which is made from a roof slab read on a framing plan. No roof slab has been read, so no item is made. It is not in the bill unless you measure it yourself."

def _roof_sets(cands: list) -> list:
  out: list = []
  for c in cands:
    f = c.get("facts") or {}
    if not f.get("roof_floor"):
      continue
    if f.get("layer_sets"):
      out.extend(s for s in f["layer_sets"] if isinstance(s, dict))
    elif f.get("layers_defined"):
      out.append({"heading": f.get("layers_heading"), "layers": f.get("layers") or [], "waterproof": f.get("layers_waterproof") or []})
  return out

def _has_roof_item(cands: list) -> bool:
  return any((c.get("facts") or {}).get("roof_floor") for c in cands)

def _layer(it: dict, cands: list) -> dict:
  name, mm, under = it.get("layer"), float(it.get("value_mm") or 0.0), str(it.get("under") or "").upper()

  if under in ROOF_HEADINGS:
    for s in _roof_sets(cands):
      if s.get("heading") == it.get("heading") and any(isinstance(l, dict) and l.get("layer") == name and abs(float(l.get("value_mm") or 0.0) - mm) <= 0.5 for l in s.get("layers") or []):
        return _row(it, USED, "It is on the roof treatment item.", layer=name)
    return _row(it, LISTED if _has_roof_item(cands) else NOT_MADE, "The roof treatment item does not carry it." if _has_roof_item(cands) else NO_ROOF_ITEM, layer=name)
  made = [c for c in cands if (c.get("facts") or {}).get("layer") == name and (c.get("facts") or {}).get("derived_from") == "ROOMS"]
  hit = [c for c in made if abs(float(c["facts"].get("thickness_mm") or 0.0) - mm) <= 0.5]
  if hit:
    return _row(it, USED, f"An item is made from it on {len(hit)} floor item{'s' if len(hit) != 1 else ''}.", layer=name)
  if made:
    other = sorted({float(c["facts"].get("thickness_mm") or 0.0) for c in made})

    return _row(it, LISTED, "The floor items for this layer use another thickness (" + ", ".join(f"{o:g} mm" for o in other) + "), taken from the heading of their floor.", layer=name)
  return _row(it, NOT_MADE, "No item is made for this layer. It is not in the bill unless you measure it yourself.", layer=name)

def _waterproof(it: dict, cands: list) -> dict:
  mat, under = it.get("material"), str(it.get("under") or "").upper()
  for c in cands:
    f = c.get("facts") or {}
    if f.get("material") == mat and not f.get("roof_floor"):
      return _row(it, USED, "An item is made from it.", material=mat)
  for s in _roof_sets(cands):
    if s.get("heading") == it.get("heading") and any(isinstance(r, dict) and r.get("material") == mat for r in s.get("waterproof") or []):
      return _row(it, USED, "It is on the roof treatment item.", material=mat)
  if under in ROOF_HEADINGS and not _has_roof_item(cands):
    return _row(it, NOT_MADE, NO_ROOF_ITEM, material=mat)
  return _row(it, NOT_MADE, "No item is made for this membrane. It is not in the bill unless you measure it yourself.", material=mat)

def ledger(items: list, printed: dict, cands: list) -> dict:
  params, clash = printed.get("params") or {}, {c["param"] for c in printed.get("conflicts") or []}
  table = printed.get("lap_table_mm") or {}
  lap_clash = {str(c.get("bar")) for c in printed.get("conflicts") or [] if c.get("param") == "lap_table"}
  flags: list = []
  by_kind: dict = {}

  for it in items or []:
    by_kind.setdefault(it.get("kind"), []).append(it)
  rows: list = []
  special = {"RCC_WALL_THICKNESS": _walls, "STAIR_WIDTH": _stairs, "SLAB_THICKNESS": _slabs}
  for kind, group in sorted(by_kind.items(), key=lambda kv: str(kv[0])):
    if kind in special:
      rows += special[kind]([g for g in group if g.get("value_mm") is not None], cands, flags)
      continue

    for it in group:
      if kind == "CLEAR_COVER" and it.get("value_mm") is not None:
        rows.append(_cover(it, params, clash))
      elif kind in KIND_PARAM:
        name, scope = KIND_PARAM[kind]
        rows.append(_param_row(it, name, params, clash) if scope is None or it.get("scope") == scope else _row(it, LISTED, f"It is not a '{scope}' note (this one is '{it.get('scope')}'), so it does not set that thickness."))
      elif kind in ("SOIL_STABILISATION", "SOIL_STAB_NOTE", "SOIL_STAB_CONDITION", "STAB_CEMENT_PCT"):
        rows.append(_soil(it, params, clash))
      elif kind == "PCC_PROJECTION":
        rows.append(_row(it, LISTED, "It is printed on one section, not on every foundation, so it is not applied to all of them.", PP.PCC_PROJECTION_PARAM))
      elif kind == "LAP_LENGTH":
        key = PP._bar_key(it["bar_dia_mm"]) if it.get("bar_dia_mm") is not None else None
        if key is not None and key in table:
          rows.append(_row(it, USED, "It is in the lap table of the calculation.", PP.LAP_PARAM))
        elif key in lap_clash:
          rows.append(_row(it, CONFLICT, "This bar is given two different laps, so none is applied.", PP.LAP_PARAM))
        else:
          rows.append(_row(it, LISTED, "It does not reach the calculation."))
      elif kind in ("CONCRETE_CLASS", "STEEL_GRADE"):
        rows.append(_row(it, GRADE, "A member takes it when the drawing prints exactly one for that kind of member (see the printed grades)."))
      elif kind == "BUILD_UP_LAYER":
        rows.append(_layer(it, cands))
      elif kind == "WATERPROOF_LAYER":
        rows.append(_waterproof(it, cands))
      elif kind in NO_QUANTITY:
        rows.append(_row(it, LISTED, NO_QUANTITY[kind]))
      else:
        rows.append(_row(it, LISTED, "No calculation reads this note."))

  counts = {f: sum(1 for r in rows if r["fate"] == f) for f in FATES}
  flagged = ("RCC_WALL_THICKNESS", "STAIR_WIDTH", "SLAB_THICKNESS")
  look = counts[NOT_MADE] + len(flags) + sum(1 for r in rows if r["fate"] == CONFLICT and r["kind"] not in flagged)
  return {"rows": rows, "contradictions": flags, "summary": {"notes": len(rows), **counts, "contradictions": len(flags), "look": look}}
