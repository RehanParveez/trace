from __future__ import annotations
import re
from app.modules.drawings_boq.rebar.member_source import FLOOR_RANK, norm_mark
from dataclasses import dataclass, field
from difflib import SequenceMatcher

FAMILIES = ("FOOTING", "PLINTH", "COLUMN", "BEAM", "SLAB", "LINTEL", "STAIR", "PARAPET", "TANK")
SHEET_FAMILY = (("PLINTH", "PLINTH"), ("FOOTING", "FOOTING"), ("COLUMN", "COLUMN"), ("LINTEL", "LINTEL"), ("STAIR", "STAIR"), ("PARAPET", "PARAPET"),
  ("SLAB", "SLAB"), ("BEAM", "BEAM"), ("UGWT", "TANK"), ("OHWT", "TANK"), ("TANK", "TANK"), ("SEPTIC", "TANK"))
FLOOR_WORDS = (("SUB", "BASEMENT"), ("BASEMENT", "BASEMENT"), ("G.F", "GROUND"), ("GROUND", "GROUND"), ("F.F", "FIRST"), ("FIRST", "FIRST"),
  ("S.F", "SECOND"), ("SECOND", "SECOND"), ("M.F", "MUMTY"), ("MUMTY", "MUMTY"), ("ROOF", "ROOF"))
FLOORED = ("COLUMN", "BEAM", "SLAB")
SHIFTED = ("BEAM", "SLAB")
TABLE_SOURCES = ("SCHEDULE", "SECTION")
MARK_SHAPE = {"COLUMN": re.compile(r"^(PC\d*|C\d+)[A-Z]?$"), "BEAM": re.compile(r"^(IB|SB|B)\d*[A-Z]?$"), "FOOTING": re.compile(r"^F\d+$"), "LINTEL": re.compile(r"^[A-Z]{1,2}\d+[A-Z]?$")}
AUTO_AT = 0.9
NAME_SIM = 0.8
SPAN_TOL_IN = 18.0
END_ALLOWANCE_IN = 0.0
CONF_FLOOR, CONF_ANY, CONF_UNREAD, CONF_OTHER, CONF_USER = 0.97, 0.95, 0.9, 0.6, 1.0
METHODS = ("FAMILY_MARK", "ROOM_PANEL", "SHEET_ONLY", "USER")
CONF_SHEET = 0.9

def family_of(sheet_name: str) -> str | None:
  up = sheet_name.upper()
  return next((fam for word, fam in SHEET_FAMILY if word in up), None)

def floor_labels(sheet_name: str, family: str | None = None) -> list:
  if family in ("TANK", "PARAPET", "FOOTING", "PLINTH", "STAIR"):
    return []
  m = re.search(r"\(([^)]*)\)", sheet_name)
  text = m.group(1).upper() if m else ""
  out: list = []
  for word, floor in FLOOR_WORDS:
    if re.search(r"(?<![A-Z])" + re.escape(word) + r"(?![A-Z])", text) and floor not in out:
      out.append(floor)
  return out

def _rank(floor: str) -> int:
  return FLOOR_RANK.index(floor) if floor in FLOOR_RANK else len(FLOOR_RANK)

def propose_floor(family: str, label: str, present: list) -> str:
  if family in SHIFTED:
    above = sorted((f for f in present if _rank(f) > _rank(label) and f != "MUMTY"), key=_rank)
    if above:
      return above[0]
    return "ROOF" if "ROOF" in present else label

  if label in present:
    return label
  if label == "MUMTY" and "ROOF" in present:
    return "ROOF"
  if label == "BASEMENT" and "GROUND" in present:
    return "GROUND"
  return label

def propose_floor_map(sheet_names: list, members: list) -> dict:
  def floors_of(*classes) -> list:
    return sorted({m.floor for m in members if m.floor in FLOOR_RANK and m.cls in classes}, key=_rank)
  out: dict = {}
  for name in sheet_names:
    fam = family_of(name)
    if fam in FLOORED:
      labels = floor_labels(name, fam)
      if labels:
        present = floors_of("COLUMN") if fam == "COLUMN" else floors_of("COLUMN", "BEAM", "SLAB")
        out[name] = [propose_floor(fam, lab, present) for lab in labels]
  return out

def targets_of(family: str, sheet_name: str, member: str | None) -> list:
  text = (member or "").strip()
  up = text.upper()
  if family == "TANK":
    word = next((w for w in ("UGWT", "OHWT", "SEPTIC", "HARVESTING") if w in sheet_name.upper()), None)
    return [("TANK", word)] if word else []
  if family == "PLINTH":
    m = re.search(r"\bAT\s+([A-Z0-9\-]+)\s*$", up)
    return [("PLINTH", norm_mark(m.group(1)))] if m else []
  if family == "STAIR":
    m = re.search(r"\((F[\- ]?\d+)\)", up)
    return [("FOOTING", norm_mark(m.group(1)))] if m else []
  if family in MARK_SHAPE:
    out = []
    
    for part in re.split(r"[/&,+]", up):
      part = re.sub(r"[\s\-]*STAIRCASE$", "", part.strip())
      nm = norm_mark(part)
      if nm and MARK_SHAPE[family].match(nm):
        out.append((family, nm))
    return out
  return []

def name_words(name: str) -> list:
  text = re.sub(r"\((?:PART|P)[^)]*\)", "", name.upper())
  return [w.strip() for w in re.split(r"\s[-+&]\s|[+&]", text) if w.strip()]

def name_similarity(a: str, b: str) -> float:
  return max((SequenceMatcher(None, x, y).ratio() for x in name_words(a) for y in name_words(b)), default=0.0)

def span_fits(row_cut_ft, panel_span_in) -> bool:
  if row_cut_ft is None or panel_span_in is None:
    return True
  return abs(float(row_cut_ft) * 12.0 - END_ALLOWANCE_IN - float(panel_span_in)) <= SPAN_TOL_IN

@dataclass
class Item:
  row_index: int
  kind: str
  family: str | None
  floors: list
  method: str | None
  confidence: float
  elements: list = field(default_factory=list)
  reason: str | None = None
  basis: str | None = None

@dataclass
class MatchResult:
  items: list
  missing: list
  floor_map: dict
  floor_map_proposed: dict
  floor_map_confirmed: bool
  stats: dict
  asks: list

def _stat_block(items: list) -> dict:
  n = len(items)
  by_kind = {k: sum(1 for i in items if i.kind == k) for k in ("MATCH", "ASK", "EXTRA")}
  auto = sum(1 for i in items if i.kind == "MATCH" and i.confidence >= AUTO_AT)
  by_method: dict = {}
  for i in items:
    if i.kind == "MATCH":
      by_method[i.method] = by_method.get(i.method, 0) + 1
      
  by_family: dict = {}
  for i in items:
    slot = by_family.setdefault(i.family or "UNKNOWN", {"rows": 0, "matched": 0})
    slot["rows"] += 1
    slot["matched"] += 1 if i.kind == "MATCH" else 0
  unread = sum(1 for i in items if i.kind == "MATCH" and i.basis == "FLOOR_NOT_READ")
  sheet_only = sum(1 for i in items if i.kind == "MATCH" and i.method == "SHEET_ONLY")
  return {"room_check_skipped": sheet_only, "rows": n, "matched": by_kind["MATCH"], "ask": by_kind["ASK"], "extra": by_kind["EXTRA"], "matched_without_asking": auto,
    "share_without_asking": round(auto / n, 4) if n else 0.0, "floor_not_read": unread, "by_method": by_method, "by_family": by_family}

def match_rows(rows: list, sheet_names: dict, members: list, decisions: dict | None = None) -> MatchResult:
  decisions = decisions or {}
  confirmed_map = decisions.get("bbs_floor_map") or {}
  member_map = decisions.get("bbs_member_map") or {}
  names = [sheet_names[i] for i in sorted(sheet_names)]
  proposed = propose_floor_map(names, members)
  floor_map = {name: list(confirmed_map[name]) if name in confirmed_map else proposed.get(name, []) for name in set(proposed) | set(confirmed_map)}
  
  index: dict = {}
  for m in members:
    index.setdefault((m.cls, norm_mark(m.mark)), []).append(m)
  by_class: dict = {}
  for m in members:
    by_class.setdefault(m.cls, []).append(m)
  complete = {m.cls for m in members if m.source in TABLE_SOURCES}
  matched_keys: set = set()
  items: list = []
  seen_panel: dict = {}
  
  for idx, row in enumerate(rows):
    sheet = sheet_names.get(row.sheet, "")
    fam = family_of(sheet)
    floors = floor_map.get(sheet, []) if fam in FLOORED else []
    group = f"{sheet}|{row.member}"
    if group in member_map:
      els = list(member_map[group].get("elements") or [])
      items.append(Item(idx, "MATCH", fam, floors, "USER", CONF_USER, els, "confirmed by the user", "USER"))
      matched_keys.update((e.get("class"), norm_mark(e.get("mark")), e.get("floor")) for e in els)
      continue
  
    if fam is None:
      items.append(Item(idx, "ASK", None, floors, None, 0.0, [], "the sheet name names no member family"))
      continue
    if fam == "SLAB":
      panels = [m for m in by_class.get("SLAB", []) if (not floors or m.floor in floors or m.floor is None)]
      if not panels:
        plan = sorted(((m.sheet, m.pdf_key) for m in members if m.cls in FLOORED and m.floor in floors and floors), key=lambda t: (-sum(1 for x in members if (x.sheet, x.pdf_key) == t), t))
        if plan:
          items.append(Item(idx, "MATCH", fam, floors, "SHEET_ONLY", CONF_SHEET, [{"pdf_key": plan[0][1], "sheet": plan[0][0], "class": "SLAB_SHEET", "mark": None, "floor": floors[0]}],
            "no room names were read, so the room is not checked", "SHEET_ONLY"))
        else:
          items.append(Item(idx, "ASK", fam, floors, None, 0.0, [], "no slab panel and no plan sheet was read for this floor"))
        continue
    
      key = (row.sheet, row.member)
      seen_panel[key] = seen_panel.get(key, 0)
      scored = sorted(((name_similarity(row.member or "", p.name or p.mark), p) for p in panels), key=lambda t: -t[0])
      close = [(s, p) for s, p in scored if s >= NAME_SIM and span_fits(row.cut_ft, (p.attrs or {}).get("length_mm") and float(p.attrs["length_mm"]) / 25.4)]
      if not close:
        items.append(Item(idx, "ASK", fam, floors, None, 0.0, [], f"no panel is named like \"{row.member}\" within {SPAN_TOL_IN / 12:g} ft of the bar length"))
        continue
    
      pick = close[min(seen_panel[key], len(close) - 1)] if len(close) > 1 else close[0]
      seen_panel[key] += 1
      conf = 0.95 if len(close) == 1 else 0.9
      items.append(Item(idx, "MATCH", fam, floors, "ROOM_PANEL", conf, [pick[1].ref()], None, "ROOM_PANEL"))
      matched_keys.add(("SLAB", norm_mark(pick[1].mark), pick[1].floor))
      continue
    targets = targets_of(fam, sheet, row.member)
    if not targets:
      items.append(Item(idx, "ASK", fam, floors, None, 0.0, [], f"\"{row.member}\" names no {fam.lower()} mark on the drawings"))
      continue
  
    els: list = []
    best = 0.0
    basis = None
    other: list = []
    for cls, nm in targets:
      cands = index.get((cls, nm), [])
      if not cands:
        continue
      if cls not in FLOORED:
        hit, conf, why = cands, CONF_ANY, "ANY_FLOOR"
      else:
        hit = [m for m in cands if m.floor in floors]
        conf, why = (CONF_FLOOR, "FLOOR") if hit else (0.0, "")
        if not hit:
          hit = [m for m in cands if m.floor is None]
          conf, why = (CONF_UNREAD, "FLOOR_NOT_READ") if hit else (0.0, "")
        if not hit:
          other.extend(cands)
          continue
      
      els.extend(m.ref() for m in hit)
      matched_keys.update((m.cls, norm_mark(m.mark), m.floor) for m in hit)
      if conf > best:
        best, basis = conf, why
    if els:
      items.append(Item(idx, "MATCH", fam, floors, "FAMILY_MARK", best, els, None, basis))
    elif other:
      where = ", ".join(sorted({m.floor or "?" for m in other}, key=_rank))
      items.append(Item(idx, "EXTRA", fam, floors, None, CONF_OTHER, [m.ref() for m in other],
        f"{row.member} is drawn on the {where.lower()} floor only, not on {', '.join(f.lower() for f in floors) or 'this floor'}"))
    elif any(cls in complete for cls, _ in targets):
      items.append(Item(idx, "EXTRA", fam, floors, None, 0.0, [], f"{row.member} is not in the drawing's {fam.lower()} table"))
    else:
      items.append(Item(idx, "ASK", fam, floors, None, 0.0, [], f"{row.member} was not found among the {fam.lower()} marks read from the drawings"))
      
  missing = []
  for m in members:
    if m.cls in complete and m.source in TABLE_SOURCES and (m.cls, norm_mark(m.mark), m.floor) not in matched_keys and not any(
        (m.cls, norm_mark(m.mark), f) in matched_keys for f in (None,) if m.floor is None):
      if m.cls == "BEAM" and any(k[0] == "BEAM" and k[1] == norm_mark(m.mark) for k in matched_keys):
        continue
      missing.append({**m.ref(), "reason": f"{m.mark} is on the drawing and no bar schedule row names it"})
      
  asks: dict = {}
  for it in items:
    if it.kind == "ASK":
      r = rows[it.row_index]
      key = f"{sheet_names.get(r.sheet, '')}|{r.member}"
      slot = asks.setdefault(key, {"group": key, "sheet": sheet_names.get(r.sheet, ""), "member": r.member, "family": it.family, "rows": 0, "reason": it.reason})
      slot["rows"] += 1
  return MatchResult(items, missing, floor_map, proposed, bool(confirmed_map), _stat_block(items), list(asks.values()))
