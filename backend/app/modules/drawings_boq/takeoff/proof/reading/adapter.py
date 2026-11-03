from __future__ import annotations
import os
from collections import Counter
from dataclasses import dataclass, field
from app.modules.drawings_boq.takeoff.proof.reading import vocab as V
from app.modules.drawings_boq.takeoff.extract import kinds as K
from app.modules.drawings_boq.takeoff.extract import read_status as RS
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
LINE_CLASSES = ("WALL", "BOUNDARY_WALL", "BEAM", "PLINTH_BEAM", "PIPE_RUN", "FOOTING_STRIP")
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
  aside = (c.facts or {}).get("set_aside")
  return c.decision != "REJECTED" and (not aside or aside.get("by") == RS.ROLE_BY)

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

def register_of(row: dict) -> dict:
  meta = row.get("meta") or {}
  ident = meta.get("identity") or {}
  vote = ident.get("role_vote") or {}
  role = ROLE_OF.get(vote.get("role") or "")
  
  if role is None:
    role = {"SPEC": V.Role.SPEC, "LEGEND": V.Role.LEGEND}.get(str(ident.get("sheet_type") or "").upper())
  ptype = meta.get("pdf_type") or {}
  text_type = TEXT_TYPE_OF.get(ptype.get("type"))
  if text_type is V.TextType.TEXT and ptype.get("partial_outline"):
    text_type = V.TextType.PARTIAL
  title = row.get("title") or {}
  return {"sheet": row["page_no"], "sheet_no": title.get("sheet_no") or ident.get("sheet_no"), "title": title.get("title") or ident.get("title"),
    "role": role.value if role else None, "plan_kind": (PLAN_KIND_OF.get(ident.get("plan_kind")) or None) and PLAN_KIND_OF[ident.get("plan_kind")].value,
    "floor": ident.get("floor"), "discipline": ident.get("discipline"), "scale_ratio": row.get("ratio"), "scale_basis": row.get("scale_source"), "text_type": text_type.value if text_type else None}

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
    for c in row.get("candidates") or []:
      if not _live(c):
        continue
      cls = class_of(c)
      if cls is None:
        out.unmapped[K.kind_of(c)] += 1
        continue

      pts = [] if upright else _points(c)
      attrs = _attrs(c)
      count = attrs["count"]
      status = V.Status.parse(RS.status_of(c))
      reasons = [r for r in RS.reasons_of(c) if r in V.Reason.names()]
      mark = None if c.tag in (None, "") else str(c.tag)
      single = _geometry(cls, pts)
      if single is None and count > 1 and len(pts) == count and cls.value not in LINE_CLASSES + AREA_CLASSES:
        for p in pts:
          out.items.append(ReadItem(sheet=sheet, cls=cls, mark=mark, geom={"point": p}, attrs={**attrs, "count": 1}, status=status, reasons=list(reasons), source=source, confidence=c.confidence))
        continue
      geom = single if single is not None else ({"point": pts[0]} if len(pts) == 1 and count == 1 else None)
      out.items.append(ReadItem(sheet=sheet, cls=cls, mark=mark, geom=geom, attrs=attrs, status=status, reasons=list(reasons), source=source, confidence=c.confidence))
  return out

def read_case(case: dict, files: dict, budget_s: float | None = None) -> dict:
  blobs = []
  for name in case["pdfs"]:
    with open(files[name], "rb") as fh:
      blobs.append((name, fh.read()))
  kw = {} if budget_s is None else {"budget_s": budget_s}
  return {name: rows for name, rows, _problems in BM.read_set(blobs, **kw)}

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
