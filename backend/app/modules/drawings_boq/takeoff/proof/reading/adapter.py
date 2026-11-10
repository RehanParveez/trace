from __future__ import annotations
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from app.modules.drawings_boq.takeoff.proof.reading import vocab as V
from app.modules.drawings_boq.takeoff.extract import column_census_items as CCI
from app.modules.drawings_boq.takeoff.extract import column_detail_cells as CDC
from app.modules.drawings_boq.takeoff.extract import beam_section_items as BSI
from app.modules.drawings_boq.takeoff.extract import footing_section_items as FSI
from app.modules.drawings_boq.takeoff.extract import slab_callouts as SC
from app.modules.drawings_boq.takeoff.extract import slab_thickness_items as STI
from app.modules.drawings_boq.takeoff.extract import lintel_schedule_items as LSI
from app.modules.drawings_boq.takeoff.extract import finish_spec_items as FSP
from app.modules.drawings_boq.takeoff.extract import drain_labels as DLB
from app.modules.drawings_boq.takeoff.extract import roof_plan_walls as RPW
from app.modules.drawings_boq.takeoff.extract import wall_pieces as WPC
from app.modules.drawings_boq.takeoff.extract import roof_plan_walls as RPW
from app.modules.drawings_boq.takeoff.extract import wall_pieces as WPC
from app.modules.drawings_boq.takeoff.extract import level_marks as LMK
from app.modules.drawings_boq.takeoff.extract import tube_fixtures as TFX
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.extract import kinds as K
from app.modules.drawings_boq.takeoff.extract import read_status as RS
from app.modules.drawings_boq.takeoff.extract import structure_tables as ST
from app.modules.drawings_boq.takeoff.proof import benchmark as BM
from app.modules.drawings_boq.takeoff.prep import page_role as PRL

FINISH_KINDS = ("BOUNDARY_PAINT", "BOUNDARY_PLASTER", "CEILING_PAINT", "CEILING_PLASTER", "DADO", "FLOOR_BALLAST", "FLOOR_BRICK_TILES", "FLOOR_COMPACTED_MUD", "FLOOR_CS_BED", "FLOOR_FINISH",
  "FLOOR_LAWN", "FLOOR_MUD_PLASTER", "FLOOR_PASSAGE", "FLOOR_PCC", "FLOOR_PORCH", "FLOOR_SAND_FILL", "FLOOR_TERRACE", "FLOOR_WET", "KACHA_FLOOR", "MEMBRANE", "MEMBRANE_COAT", "MEMBRANE_POLYTHENE",
  "PAINT_INSIDE", "PAINT_OUTSIDE", "PLASTER_INSIDE", "PLASTER_OUTSIDE", "ROOF_BALLAST", "ROOF_MEMBRANE", "ROOF_PCC", "ROOF_POLYTHENE", "ROOF_SCREED", "ROOF_TREATMENT", "SKIRTING", "WALL_TILE", "WET_WATERPROOF")
CLASS_OF = {
  "COLUMN": "COLUMN", "FOOTING": "FOOTING_PAD", "BEAM": "BEAM", "SLAB": "SLAB_PANEL", "LINTEL": "LINTEL_TYPE", "STAIR": "STAIR", "ROOM": "ROOM", "DOOR": "DOOR", "WINDOW": "WINDOW", "WALL": "WALL",
  "OHWT": "TANK", "UGWT": "TANK", "SEPTIC": "TANK", "GATE": "GATE", "BOUNDARY_WALL": "BOUNDARY_WALL",
  "DRAIN_MANHOLE": "DRAIN_POINT", "GULLY_TRAP": "DRAIN_POINT", "INSPECTION_CHAMBER": "DRAIN_POINT", "SEWER_PIPE": "PIPE_RUN", "RAIN_PIPE": "PIPE_RUN",
  "ELEC_BOARD": "DISTRIBUTION_BOARD", "ELEC_FAN": "ELECTRICAL_POINT", "ELEC_LIGHT": "ELECTRICAL_POINT", "ELEC_LOWV": "ELECTRICAL_POINT", "ELEC_OTHER": "ELECTRICAL_POINT",
  "ELEC_SOCKET": "ELECTRICAL_POINT", "ELEC_SWITCH": "ELECTRICAL_POINT", **{k: "FINISH_LAYER" for k in FINISH_KINDS}}
LINE_CLASSES = ("WALL", "BOUNDARY_WALL", "BEAM", "PLINTH_BEAM", "PIPE_RUN", "FOOTING_STRIP", "PARAPET")
AREA_CLASSES = ("ROOM", "SLAB_PANEL")
UPRIGHT_NOTE = "SHEET_READ_UPRIGHT"
TEXT_TYPE_OF = {"VECTOR_TEXT": V.TextType.TEXT, "VECTOR_OUTLINED": V.TextType.OUTLINED, "VECTOR_NOLETTER": V.TextType.OUTLINED, "RASTER": V.TextType.RASTER, "IMAGE_PAGE": V.TextType.RASTER, "EMPTY": V.TextType.TEXT}
ROLE_OF = {PRL.ARCH_PLAN: V.Role.PLAN, PRL.FURNITURE_PLAN: V.Role.PLAN, PRL.STRUCT_PLAN: V.Role.PLAN, PRL.MEP_PLAN: V.Role.PLAN, PRL.DETAIL: V.Role.DETAIL, PRL.SECTION: V.Role.SECTION,
  PRL.ELEVATION: V.Role.ELEVATION, PRL.NOTES: V.Role.NOTES, PRL.SCHEDULE: V.Role.SCHEDULE, PRL.COVER: V.Role.COVER}
PLAN_KIND_OF = {"FOUNDATION": V.PlanKind.FOUNDATION, "FURNITURE": V.PlanKind.FURNITURE, "WORKING": V.PlanKind.FLOOR}
NUMERIC = (int, float)

@dataclass
class ReadItem:
  sheet: int
  cls: V.ElementClass
  mark: str | None
  geom: dict | None
  attrs: dict
  status: V.Status
  reasons: list
  source: V.ReadSource
  confidence: float | None = None
  join: dict | None = None

@dataclass
class PageInfo:
  sheet: int
  mm_per_pt: float | None
  paper_mm: tuple | None
  upright: bool
  register: dict
  coverage: dict = field(default_factory=dict)

@dataclass
class SetRead:
  items: list = field(default_factory=list)
  pages: dict = field(default_factory=dict)
  unmapped: Counter = field(default_factory=Counter)

def class_of(cand) -> V.ElementClass | None:
  kind = K.kind_of(cand)
  if cand.category == "BEAM" and K.role_of(cand) == "PLINTH_BEAM":
    return V.ElementClass.PLINTH_BEAM
  if cand.category == "WINDOW" and "ventilator" in str(cand.label or "").lower():
    return V.ElementClass.VENTILATOR
  name = CLASS_OF.get(kind)
  return V.ElementClass.parse(name) if name else None

def _live(c) -> bool:
  f = c.facts or {}
  aside = f.get("set_aside")
  return c.decision != "REJECTED" and not f.get("stack") and (not aside or aside.get("by") in (RS.ROLE_BY, FS.STACK_BY, FS.FAMILY_BY))

def _points(c) -> list:
  pts = (c.geometry or {}).get("points") or []
  return [[float(p[0]), float(p[1])] for p in pts if isinstance(p, (list, tuple)) and len(p) >= 2]

def _attrs(c) -> dict:
  out = {"count": int(c.count or 1)}
  for name, value in (c.params or {}).items():
    if isinstance(value, NUMERIC) and not isinstance(value, bool):
      out[name] = float(value)
  if "length_mm" in out and "width_mm" in out and c.category in ("COLUMN", "FOOTING", "DOOR", "WINDOW"):
    out["size_mm"] = [out["length_mm"], out["width_mm"]]
  return out

def _geometry(cls: V.ElementClass, pts: list) -> dict | None:
  if cls.value in LINE_CLASSES and len(pts) >= 2:
    return {"polyline": pts}
  if cls.value in AREA_CLASSES and len(pts) >= 3:
    return {"polygon": pts}
  return None

def _source(page_type: dict) -> V.ReadSource:
   return V.ReadSource.OCR if page_type.get("text_recovered") or page_type.get("ocr_words_added") else V.ReadSource.TEXT

def norm_key(mark) -> str:
  return re.sub(r"[\s\-_]+", "", str(mark or "")).upper()

def register_of(row: dict) -> dict:
  meta = row.get("meta") or {}
  ident = meta.get("identity") or {}
  vote = ident.get("role_vote") or {}
  role = ROLE_OF.get(vote.get("role") or ident.get("role") or "")
  
  if role is None:
    role = {"SPEC": V.Role.SPEC, "LEGEND": V.Role.LEGEND}.get(str(ident.get("sheet_type") or "").upper())
  ptype = meta.get("pdf_type") or {}
  text_type = TEXT_TYPE_OF.get(ptype.get("type"))
  if text_type is V.TextType.TEXT and ptype.get("partial_outline"):
    text_type = V.TextType.PARTIAL
  title = row.get("title") or {}
  derived = RS.plan_kind_of(ident) if role is V.Role.PLAN else None
  plan_kind = derived if derived in V.PlanKind.names() else (PLAN_KIND_OF[ident["plan_kind"]].value if ident.get("plan_kind") in PLAN_KIND_OF else None)
  return {"sheet": row["page_no"], "sheet_no": title.get("sheet_no") or ident.get("sheet_no"), "title": title.get("title") or ident.get("title"),
    "role": role.value if role else None, "plan_kind": plan_kind,
    "floor": ident.get("floor") or (None if title.get("composite") else title.get("level_hint")), "discipline": ident.get("discipline"), "scale_ratio": row.get("ratio"), "scale_basis": row.get("scale_source"), "text_type": text_type.value if text_type else None}

def _status_of(conflicts: list, reasons: list) -> V.Status:
  return V.Status.UNSURE if conflicts or reasons else V.Status.READ

JOIN_OF = {"COLUMN": "schedule_join", "BEAM": "section_join", "FOOTING": "footing_section_join"}

def structure_items(sheet: int, meta: dict, source: V.ReadSource) -> list:
  out: list = []
  tables = (meta or {}).get("structure_tables") or {}
  for rec in (tables.get("column_schedule") or {}).get("cells") or []:
    if rec.get("state") != "READ":
      continue
  
    size = rec.get("size") or {}
    reasons = []
    how = size.get("how")
    if how == "DECODED" and not size.get("confirmed"):
      reasons.append("FONT_DECODED")
    elif how == "DECODED_PARTIAL" or not size.get("size_in"):
      reasons.append("GLYPH_REPAIRED")
    conflicts = (rec.get("sketch") or {}).get("conflicts") or []
    if conflicts:
      reasons.append("CONFLICT_IN_DRAWING")
    anchor = rec.get("anchor_native")
    out.append(ReadItem(sheet=sheet, cls=V.ElementClass.COLUMN_SCHEDULE_CELL, mark=rec["mark"], geom={"point": [float(anchor[0]), float(anchor[1])]} if anchor else None, attrs=ST.cell_attrs(rec),
      status=_status_of(conflicts, reasons), reasons=reasons, source=source))
    
  for rec in ((meta or {}).get(CDC.META_KEY) or {}).get("cells") or []:
    out.append(ReadItem(sheet=sheet, cls=V.ElementClass.COLUMN_SCHEDULE_CELL, mark=rec["mark"], geom={"point": [float(rec["anchor"][0]), float(rec["anchor"][1])]} if rec.get("anchor") else None, attrs=CDC.attrs_of(sheet, rec),
      status=_status_of(None, rec.get("reasons") or []), reasons=list(rec.get("reasons") or []), source=source))
  for rec in ((meta or {}).get(CCI.META_KEY) or {}).get("members") or []:
    out.append(ReadItem(sheet=sheet, cls=V.ElementClass.COLUMN, mark=None, geom={"point": [float(rec["at"][0]), float(rec["at"][1])]} if rec.get("at") else None, attrs={"count": 1, "size_mm": list(rec["size_mm"]), "floor": rec["floor"]},
      status=V.Status.UNSURE, reasons=list(CCI.REASONS), source=source))
  for rec in ((meta or {}).get(BSI.META_KEY) or {}).get("sections") or []:
    out.append(ReadItem(sheet=sheet, cls=V.ElementClass.BEAM_SECTION, mark=rec["mark"], geom=None, attrs=rec["attrs"], status=_status_of(None, rec["reasons"]), reasons=list(rec["reasons"]), source=source))
  for rec in ((meta or {}).get(SC.META_KEY) or {}).get("callouts") or []:
    out.append(ReadItem(sheet=sheet, cls=V.ElementClass.SLAB_BAR_CALLOUT, mark=None, geom={"point": [float(rec["at"][0]), float(rec["at"][1])]}, attrs={"text": rec["text"], "bar_dia_no": rec["bar"], "spacing_in": rec["spacing_in"]}, status=V.Status.READ, reasons=[], source=source))
  for rec in ((meta or {}).get(STI.META_KEY) or {}).get("facts") or []:
    if rec.get("key"):
      out.append(ReadItem(sheet=sheet, cls=V.ElementClass.NOTE_FACT, mark=rec["key"], geom=None, attrs={"key": rec["key"], "value": rec["value"], "unit": rec["unit"]}, status=V.Status.READ, reasons=[], source=source))
  for rec in ((meta or {}).get(LSI.META_KEY) or {}).get("types") or []:
    out.append(ReadItem(sheet=sheet, cls=V.ElementClass.LINTEL_TYPE, mark=rec["mark"], geom=None, attrs=rec["attrs"], status=_status_of(None, rec["reasons"]), reasons=list(rec["reasons"]), source=source))
  for rec in ((meta or {}).get(DLB.META_KEY) or {}).get("labels") or []:
    out.append(ReadItem(sheet=sheet, cls=V.ElementClass.DRAIN_POINT, mark=None, geom={"point": [float(rec["at"][0]), float(rec["at"][1])]}, attrs={"kind": rec["kind"], **({"size_in": rec["size_in"]} if rec.get("size_in") else {})},
      status=V.Status.READ, reasons=[], source=source))
  for rec in ((meta or {}).get(LMK.META_KEY) or {}).get("marks") or []:
    out.append(ReadItem(sheet=sheet, cls=V.ElementClass.LEVEL, mark=rec["mark"], geom={"point": [float(rec["at"][0]), float(rec["at"][1])]}, attrs={"count": 1, "value_in": rec["value_in"]}, status=V.Status.READ, reasons=[], source=source))
  for rec in ((meta or {}).get(TFX.META_KEY) or {}).get("fixtures") or []:
    out.append(ReadItem(sheet=sheet, cls=V.ElementClass.ELECTRICAL_POINT, mark=None, geom={"point": [float(rec["at"][0]), float(rec["at"][1])]}, attrs={"count": 1}, status=V.Status.READ, reasons=[], source=source))
  for block in ((meta or {}).get(FSP.META_KEY) or {}).get("blocks") or []:
    for layer in block["layers"]:
      attrs = {"spec": block["mark"], "order": layer["order"], "text": layer["text"], **({"thickness_in": layer["thickness_in"]} if "thickness_in" in layer else {})}
      out.append(ReadItem(sheet=sheet, cls=V.ElementClass.FINISH_LAYER, mark=block["mark"], geom={"point": [float(layer["at"][0]), float(layer["at"][1])]}, attrs=attrs, status=V.Status.READ, reasons=[], source=source))
  for rec in ((meta or {}).get(FSI.META_KEY) or {}).get("sections") or []:
    out.append(ReadItem(sheet=sheet, cls=V.ElementClass.FOOTING_SECTION, mark=rec["mark"], geom=None, attrs=rec["attrs"], status=_status_of(None, rec["reasons"]), reasons=list(rec["reasons"]), source=source))
  for rec in ((meta or {}).get("structure_joins") or {}).get("planted") or []:
    attrs = {"count": 1, **({"floor": rec["floor"]} if rec.get("floor") else {})}
    out.append(ReadItem(sheet=sheet, cls=V.ElementClass.COLUMN, mark=rec["mark"], geom={"point": [float(rec["at"][0]), float(rec["at"][1])]}, attrs=attrs, status=V.Status.READ, reasons=[], source=source,
      join={k: rec.get(k) for k in ("status", "how", "to", "reason")}))
  for rec in ((meta or {}).get("rebar_rules") or {}).get("facts") or []:
    attrs = {"key": rec["key"], "value": rec["value"], **({"unit": rec["unit"]} if rec.get("unit") else {})}
    out.append(ReadItem(sheet=sheet, cls=V.ElementClass.NOTE_FACT, mark=rec["key"], geom=None, attrs=attrs, status=V.Status.READ, reasons=[], source=source))
  for rec in (tables.get("beam_sections") or {}).get("sections") or []:
    reasons = []
    if rec.get("decoded") and (rec.get("sketch_dims") or 0) < 2:
      reasons.append("FONT_DECODED")
    if rec.get("conflicts"):
      reasons.append("CONFLICT_IN_DRAWING")
      
    out.append(ReadItem(sheet=sheet, cls=V.ElementClass.BEAM_SECTION, mark=rec["mark"], geom=None, attrs=ST.beam_section_attrs(rec), status=_status_of(rec.get("conflicts"), reasons), reasons=reasons, source=source))
  return out

def band_items(sheet: int, bands: dict, source: V.ReadSource) -> list:
  out: list = []
  for view in (bands or {}).get("views") or []:
    for b in view.get("bands") or []:
      reasons = [r for r in b.get("reasons") or [] if r in V.Reason.names()]
      attrs = {"count": 1, "width_in": float(b["width_in"]), "length_mm": float(b["length_mm"]), "fill": b.get("source") or "DOTS",
        "supports": [(s or {}).get("on") for s in b.get("supports") or []]}
      out.append(ReadItem(sheet=sheet, cls=V.ElementClass.BEAM, mark=b.get("mark"), geom={"polyline": b["polyline"]}, attrs=attrs, status=_status_of(None, reasons), reasons=reasons, source=source))
  return out

def panel_items(sheet: int, graph: dict, source: V.ReadSource) -> list:
  out: list = []
  for view in (graph or {}).get("views") or []:
    for p in view.get("panels") or []:
      reasons = [r for r in p.get("reasons") or [] if r in V.Reason.names()]
      attrs = {"count": 1, "void": bool(p.get("void")), "callouts": [c["text"] for c in p.get("callouts") or []], "room": p.get("room")}
      for key in ("clear_span_x_ft", "clear_span_y_ft"):
        if p.get(key) is not None:
          attrs[key] = float(p[key])
      out.append(ReadItem(sheet=sheet, cls=V.ElementClass.SLAB_PANEL, mark=p.get("mark"), geom={"polygon": p["polygon"]}, attrs=attrs, status=V.Status.UNSURE, reasons=reasons, source=source))
  return out

def items_of(rows: list) -> SetRead:
  out = SetRead()
  for row in rows:
    sheet = row["page_no"]
    meta = row.get("meta") or {}
    notes = [n.get("code") if isinstance(n, dict) else n for n in row.get("notes") or []]
    upright = UPRIGHT_NOTE in notes
    paper = meta.get("paper") or {}
    cov = {r["class"]: r["status"] for r in ((row.get("stats") or {}).get("coverage") or {}).get("classes") or []}
    out.pages[sheet] = PageInfo(sheet=sheet, mm_per_pt=row.get("mm_per_pt"), paper_mm=(paper.get("width_mm"), paper.get("height_mm")) if paper else None, upright=upright, register=register_of(row), coverage=cov)
    source = _source(meta.get("pdf_type") or {})
    walls = WPC.sheet_walls([c for c in row.get("candidates") or [] if _live(c) and class_of(c) == V.ElementClass.WALL], row.get("mm_per_pt")) if WPC.junctions_enabled() else []
    for c in row.get("candidates") or []:
      if not _live(c):
        continue
      cls = class_of(c)
      if cls is None:
        out.unmapped[K.kind_of(c)] += 1
        continue
      if cls == V.ElementClass.WALL and RPW.is_parapet(c):
        cls = V.ElementClass.PARAPET
      if cls == V.ElementClass.WALL and RPW.is_parapet(c):
        cls = V.ElementClass.PARAPET

      pts = [] if upright else _points(c)
      attrs = _attrs(c)
      count = attrs["count"]
      status = V.Status.parse(RS.status_of(c))
      reasons = [r for r in RS.reasons_of(c) if r in V.Reason.names()]
      mark = None if c.tag in (None, "") else str(c.tag)
      join = (c.facts or {}).get(JOIN_OF.get(c.category, "")) if c.category in JOIN_OF else None
      if cls in (V.ElementClass.WALL, V.ElementClass.PARAPET) and len(pts) >= 2 and WPC.active():
        parts = WPC.pieces_of(c, row.get("mm_per_pt"), walls)
        if len(parts) > 1:
          for part in parts:
            out.items.append(ReadItem(sheet=sheet, cls=cls, mark=mark, geom={"polyline": part}, attrs=attrs, status=status, reasons=list(reasons), source=source, confidence=c.confidence, join=join))
          continue
      if cls in (V.ElementClass.WALL, V.ElementClass.PARAPET) and len(pts) >= 2 and WPC.active():
        parts = WPC.pieces_of(c, row.get("mm_per_pt"), walls)
        if len(parts) > 1:
          for part in parts:
            out.items.append(ReadItem(sheet=sheet, cls=cls, mark=mark, geom={"polyline": part}, attrs=attrs, status=status, reasons=list(reasons), source=source, confidence=c.confidence, join=join))
          continue
      single = _geometry(cls, pts)
      if single is None and count > 1 and (len(pts) == count or not pts) and cls.value not in LINE_CLASSES + AREA_CLASSES:
        for k in range(count):
          out.items.append(ReadItem(sheet=sheet, cls=cls, mark=mark, geom={"point": pts[k]} if pts else None, attrs={**attrs, "count": 1}, status=status, reasons=list(reasons), source=source, confidence=c.confidence, join=join))
        continue
      geom = single if single is not None else ({"point": pts[0]} if len(pts) == 1 and count == 1 else None)
      
      out.items.append(ReadItem(sheet=sheet, cls=cls, mark=mark, geom=geom, attrs=attrs, status=status, reasons=list(reasons), source=source, confidence=c.confidence, join=join))
    out.items.extend(structure_items(sheet, meta, source))
    if not any(i.sheet == sheet and i.cls == V.ElementClass.BEAM for i in out.items):
      out.items.extend(band_items(sheet, (row.get("stats") or {}).get("beam_bands") or {}, source))
    if not any(i.sheet == sheet and i.cls == V.ElementClass.SLAB_PANEL for i in out.items):
      out.items.extend(panel_items(sheet, (row.get("stats") or {}).get("slab_panel_graph") or {}, source))
  return out

def read_case(case: dict, files: dict, budget_s: float | None = None, notes: dict | None = None) -> dict:
  blobs = []
  for name in case["pdfs"]:
    with open(files[name], "rb") as fh:
      blobs.append((name, fh.read()))
  kw = {} if budget_s is None else {"budget_s": budget_s}
  return {name: rows for name, rows, _problems in BM.read_set(blobs, rules=case.get("overrides"), **kw)}

def read_items(pdf_path: str) -> SetRead:
  with open(pdf_path, "rb") as fh:
    data = fh.read()
  name = os.path.basename(pdf_path)
  _n, rows, _p = BM.read_set([(name, data)])[0]
  return items_of(rows)

def mapping_table() -> list:
  rows = []
  for kind in sorted(K.KINDS):
    name = CLASS_OF.get(kind)
    rows.append((kind, name or "none"))
  return rows
