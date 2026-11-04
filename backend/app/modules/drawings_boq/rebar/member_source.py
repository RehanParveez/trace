from __future__ import annotations
import re
from dataclasses import dataclass, field

FLOOR_RANK = ("BASEMENT", "GROUND", "FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "ROOF", "MUMTY")
TANK_WORDS = ("UGWT", "OHWT", "SEPTIC", "HARVESTING")
PRINTED_PATTERNS = ((re.compile(r"^(PC|C)\d+[A-Z]?$"), "COLUMN"), (re.compile(r"^(IB|SB|B)\d*[A-Z]?$"), "BEAM"), (re.compile(r"^F\d+$"), "FOOTING"))
UNMARKED_BEAM = re.compile(r"-BEAM-")
STRONG = {"SCHEDULE": 4, "PLANTED": 3, "CANDIDATE": 3, "SECTION": 2, "PRINTED": 1}

@dataclass
class DrawingMember:
  pdf_key: str
  sheet: int
  cls: str
  mark: str
  floor: str | None
  count: int = 1
  source: str = "CANDIDATE"
  name: str | None = None
  attrs: dict = field(default_factory=dict)

  def ref(self) -> dict:
    return {"pdf_key": self.pdf_key, "sheet": self.sheet, "class": self.cls, "mark": self.mark, "floor": self.floor}

def norm_mark(mark) -> str:
  return re.sub(r"[\s\-_.]", "", str(mark or "")).upper()

def sheet_floor(meta: dict) -> str | None:
  ident = meta.get("identity") or {}
  title = meta.get("title") or {}
  return ident.get("floor") or (None if title.get("composite") else title.get("level_hint"))

def candidate_dict(c) -> dict:
  g = (lambda k: c.get(k)) if isinstance(c, dict) else (lambda k: getattr(c, k, None))
  return {"category": g("category"), "tag": g("tag"), "label": g("label"), "count": g("count"), "decision": g("decision"), "params": g("params") or {}, "facts": g("facts") or {}}

def _live(c: dict) -> bool:
  return c.get("decision") != "REJECTED" and not (c.get("facts") or {}).get("set_aside")

def members_from_sheets(sheets: list, candidates: dict) -> list:
  out: list = []
  scheduled = {norm_mark(rec["mark"]) for sh in sheets for rec in (((sh.get("meta") or {}).get("structure_tables") or {}).get("column_schedule") or {}).get("cells") or [] if rec.get("mark")}
  for sh in sheets:
    key, page, meta = sh["pdf_key"], sh["page_no"], sh.get("meta") or {}
    floor = sheet_floor(meta)
    
    tables = meta.get("structure_tables") or {}
    for rec in (tables.get("column_schedule") or {}).get("cells") or []:
      if rec.get("state") == "READ" and rec.get("mark"):
        size = (rec.get("size") or {}).get("size_in")
        out.append(DrawingMember(key, page, "COLUMN", str(rec["mark"]), rec.get("floor"), 1, "SCHEDULE", attrs={"size_in": size, "steel": rec.get("steel"), "mid": rec.get("mid"), "joint": rec.get("joint")}))
    planted = ((meta.get("structure_joins") or {}).get("planted")) or [{"mark": lab["mark"], "floor": floor} for lab in (tables.get("planted_labels") or {}).get("labels") or []]
    for rec in planted:
      if norm_mark(rec["mark"]) in scheduled:
        out.append(DrawingMember(key, page, "COLUMN", str(rec["mark"]), rec.get("floor") or floor, 1, "PLANTED"))
    for rec in (tables.get("beam_sections") or {}).get("sections") or []:
      out.append(DrawingMember(key, page, "BEAM", str(rec["mark"]), None, 1, "SECTION", attrs={"width_in": rec.get("width_in"), "depth_in": rec.get("depth_in")}))
    for sec in list(meta.get("footing_sections") or []) + list((tables.get("footing_sections") or {}).get("sections") or []):
      if sec.get("mark"):
        out.append(DrawingMember(key, page, "FOOTING", str(sec["mark"]), None, 1, "SECTION", attrs={k: v for k, v in sec.items() if k != "mark"}))
    for raw in candidates.get((key, page)) or []:
      c = candidate_dict(raw)
      if not _live(c):
        continue
    
      cat, tag, count = c["category"], c.get("tag"), int(c.get("count") or 1)
      if cat in ("COLUMN", "FOOTING", "LINTEL", "STAIR") and tag:
        out.append(DrawingMember(key, page, cat, str(tag), floor, count, "CANDIDATE"))
      elif cat == "BEAM" and tag and not UNMARKED_BEAM.search(str(tag)):
        out.append(DrawingMember(key, page, "BEAM", str(tag), floor, count, "CANDIDATE", attrs={"length_mm": (c["params"] or {}).get("length_mm")}))
      elif cat == "SITE" and tag and str(tag).upper() in TANK_WORDS:
        out.append(DrawingMember(key, page, "TANK", str(tag), None, count, "CANDIDATE"))
      elif cat in ("SLAB", "ROOM") and c.get("label") and not str(c["label"]).startswith("Room ·"):
        out.append(DrawingMember(key, page, "SLAB", str(c["label"]), floor, 1, "CANDIDATE", name=str(c["label"]), attrs={"length_mm": (c["params"] or {}).get("length_mm"), "width_mm": (c["params"] or {}).get("width_mm")}))
    for mark, n in (((meta.get("mark_evidence") or {}).get("seen")) or {}).items():
      for pattern, cls in PRINTED_PATTERNS:
        if pattern.match(norm_mark(mark)):
          out.append(DrawingMember(key, page, cls, str(mark), floor, int(n or 1), "PRINTED"))
          break
  return out

def collapse(members: list) -> list:
  best: dict = {}
  for m in members:
    best[(m.cls, norm_mark(m.mark))] = max(best.get((m.cls, norm_mark(m.mark)), 0), STRONG[m.source])
  kept = [m for m in members if STRONG[m.source] == best[(m.cls, norm_mark(m.mark))]]
  merged: dict = {}
  
  for m in kept:
    k = (m.cls, norm_mark(m.mark), m.floor, m.pdf_key, m.sheet, m.source)
    if k in merged:
      merged[k].count += m.count if m.source != "SCHEDULE" else 0
    else:
      merged[k] = DrawingMember(m.pdf_key, m.sheet, m.cls, m.mark, m.floor, m.count, m.source, m.name, dict(m.attrs))
  return list(merged.values())
