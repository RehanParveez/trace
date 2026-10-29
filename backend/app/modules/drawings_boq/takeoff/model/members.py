from __future__ import annotations
import hashlib
import math
from app.modules.drawings_boq.takeoff.extract import floor_union as FU
from app.modules.drawings_boq.takeoff.extract import mark_entities as ME
from dataclasses import dataclass, field
from app.modules.drawings_boq.takeoff.model.types import Member, Sighting, Decision
from app.modules.drawings_boq.takeoff.extract.crosschecks import _sheet_floor
from app.modules.drawings_boq.takeoff.extract import accept_guard as AG

KINDS = ("COLUMN", "FOOTING", "BEAM")
POSITIONED = ("COLUMN", "FOOTING")
SCHEDULE, DETAIL, PLAN = "SCHEDULE", "DETAIL", "PLAN"
BASIS_RANK = {SCHEDULE: 0, DETAIL: 1, PLAN: 2}
SIZE_TOL_MM = 25.4
FALLBACK_TOL_SHARE = 0.02
NO_POSITION = "NO_POSITION"
IDENTITY = FU.Registration(1 + 0j, 0j, 0, 0, 0, 0.0, 0.0)

@dataclass(frozen=True)
class MemberSet:
  members: tuple = ()
  decisions: tuple = ()
  unregistered: tuple = ()
  counts: dict = field(default_factory=dict)
  ifc_sizes: dict = field(default_factory=dict)

  def summary(self) -> dict:
    by_kind: dict = {}
    for m in self.members:
      row = by_kind.setdefault(m.kind, {"members": 0, "sightings": 0, "on_several_sheets": 0})
      row["members"] += 1
      row["sightings"] += len(m.sightings)
      row["on_several_sheets"] += 1 if len({(s.drawing_id, s.page_no) for s in m.sightings}) > 1 else 0
    audit = [{"kind": k, "mark": mk, "floors": dict(sorted((str(f), n) for f, n in v.items())), "same": len(set(v.values())) <= 1} for (k, mk), v in sorted(self.counts.items()) if len(v) > 1]
    return {"by_kind": dict(sorted(by_kind.items())), "decisions": len(self.decisions), "unregistered_sheets": list(self.unregistered), "marks_on_several_floors": audit,
      "marks_with_different_counts": sum(1 for a in audit if not a["same"])}

def key_of(c) -> str:
  return str(getattr(c, "key", None) or getattr(c, "ckey", None) or getattr(c, "id", ""))

def basis_of(c) -> str:
  codes = {n.get("code") for n in (getattr(c, "notes", None) or []) if isinstance(n, dict)}
  return SCHEDULE if codes & set(ME.SCHEDULE_CODES) else DETAIL if codes & set(ME.DETAIL_CODES) else PLAN

def size_of(c) -> tuple | None:
  p = getattr(c, "params", None) or {}
  keys = {"COLUMN": ("length_mm", "width_mm"), "FOOTING": ("length_mm", "width_mm", "depth_mm"), "BEAM": ("width_mm", "depth_mm")}[c.category]
  vals = [p.get(k) for k in keys]
  if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 for v in vals):
    return None
  return tuple(round(float(v), 1) for v in vals)

def _same_size(a, b) -> bool:
  return a is not None and b is not None and len(a) == len(b) and all(abs(x - y) <= SIZE_TOL_MM for x, y in zip(a, b))

@dataclass
class _Sight:
  sheet: int
  cand: object
  mark: str | None
  point: tuple | None
  basis: str
  size: tuple | None

def _register(sheets: list, ids: list) -> tuple:
  rows = {i: [c for c in sheets[i]["candidates"] if c.category in FU.ANCHOR_CATEGORIES and c.decision != "REJECTED"] for i in ids}
  base = max(ids, key=lambda i: (len(FU.anchors(rows[i])), -i))
  out: dict = {base: IDENTITY}
  for i in ids:
    if i != base:
      out[i] = FU.register(rows[base], rows[i])
  return base, out

def _tol_pt(size_a, size_b, mm_per_pt, extent) -> float:
  sizes = [min(s) for s in (size_a, size_b) if s]
  if sizes and mm_per_pt:
    return 0.5 * min(sizes) / mm_per_pt
  return max(3.0, FALLBACK_TOL_SHARE * extent)

def _id(kind: str, floor, mark, where) -> str:
  return "m_" + hashlib.sha1(f"{kind}|{floor}|{mark}|{where}".encode()).hexdigest()[:12]

def _height(levels, floor) -> float | None:
  for l in levels or ():
    if l.key == floor:
      return l.f2f_mm or l.clear_mm
  return None

def _sighting(sheets: list, s: _Sight) -> Sighting:
  sh = sheets[s.sheet]
  return Sighting(str(sh.get("drawing_id") or sh.get("drawing") or ""), sh["page_no"], key_of(s.cand), s.basis)

def _best(g: list) -> _Sight:
  return min(g, key=lambda s: (BASIS_RANK[s.basis], s.size is None))

def build(read: list, levels=None, skip=None) -> MemberSet:
  sheets = [s for s in read if "title" in s and "stats" in s]
  
  by_kf: dict = {}
  floors_of_sheet: dict = {}
  for i, sh in enumerate(sheets):
    sf = _sheet_floor(sh)
    for c in sh["candidates"]:
      if c.category not in KINDS or (skip is not None and skip(sh, c)):
        continue
      if c.decision == "REJECTED" and not ME.is_mine(c):
        continue
      mk = AG.mark_key(c.category, c.tag, c.facts)
      if mk is None and c.category == "BEAM":
        continue
      floor = ME.floor_of_item(c, sf)
      by_kf.setdefault((c.category, floor), []).append((i, c, mk[1] if mk else None))
      floors_of_sheet.setdefault(floor, set()).add(i)
      
  frames: dict = {}
  bases: dict = {}
  unregistered: list = []
  for floor, ids in floors_of_sheet.items():
    ids = sorted(ids)
    if floor is None or len(ids) == 1:
      bases[floor], frames[floor] = ids[0], {i: IDENTITY if len(ids) == 1 else None for i in ids}
    else:
      bases[floor], frames[floor] = _register(sheets, ids)
    for i, reg in frames[floor].items():
      if reg is None:
        unregistered.append({"drawing_id": str(sheets[i].get("drawing_id") or sheets[i].get("drawing") or ""), "page_no": sheets[i]["page_no"], "floor": floor})
        
  members: list = []
  decisions: list = []
  counts: dict = {}
  for (kind, floor), rows in sorted(by_kf.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
    items = []
    for i, c, mark in rows:
      reg = frames[floor].get(i)
      pts = FU.points_of(c) if kind in POSITIONED else []
      if pts and reg is not None:
        items += [_Sight(i, c, mark, reg.apply(p), basis_of(c), size_of(c)) for p in pts]
      else:
        items.append(_Sight(i, c, mark, None, basis_of(c), size_of(c)))
    positioned = [s for s in items if s.point is not None]
    
    loose = [s for s in items if s.point is None]
    mm_base = sheets[bases[floor]].get("mm_per_pt") if floor in bases else None
    ext = FU._extent([s.point for s in positioned]) if positioned else 0.0
    parent = list(range(len(positioned)))
    def find(a):
      while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
      return a
  
    clash: list = []
    for a in range(len(positioned)):
      for b in range(a + 1, len(positioned)):
        sa, sb = positioned[a], positioned[b]
        if math.hypot(sa.point[0] - sb.point[0], sa.point[1] - sb.point[1]) > _tol_pt(sa.size, sb.size, mm_base, ext):
          continue
        if sa.mark and sb.mark and sa.mark != sb.mark:
          clash.append((sa, sb))
        else:
          parent[find(a)] = find(b)
    groups: dict = {}
    for a in range(len(positioned)):
      groups.setdefault(find(a), []).append(positioned[a])
      
    made: dict = {}
    for g in sorted(groups.values(), key=lambda g: (round(g[0].point[0]), round(g[0].point[1]))):
      mark = next((s.mark for s in g if s.mark), None)
      cx, cy = sum(s.point[0] for s in g) / len(g), sum(s.point[1] for s in g) / len(g)
      best = _best(g)
      half = 0.5 * max(best.size[:2]) / mm_base if best.size and mm_base else 0.0
      outline = ((cx - half, cy - half), (cx + half, cy - half), (cx + half, cy + half), (cx - half, cy + half)) if half else ()
      m = Member(_id(kind, floor, mark, (round(cx), round(cy))), kind, mark, floor, outline, best.size, _height(levels, floor), tuple(_sighting(sheets, s) for s in g))
      members.append(m)
      
      made.setdefault(mark, []).append(len(members) - 1)
      top = [s for s in g if s.size and s.basis == best.basis]
      distinct = [x for n, x in enumerate(s.size for s in top) if not any(_same_size(x, y) for y in [t.size for t in top[:n]])]
      if len(distinct) > 1:
        decisions.append(Decision(f"size:{m.id}", f"Size of {mark or 'the unmarked member'} on {floor or 'its sheet'}", tuple({"value": list(x), "sources": [best.basis]} for x in distinct), None))
    for sa, sb in clash:
      decisions.append(Decision(f"mark:{kind}:{floor}:{round(sa.point[0])}:{round(sa.point[1])}", f"Which mark stands here on {floor or 'its sheet'}: {sa.mark} or {sb.mark}?",
        ({"value": sa.mark, "sources": [f"page {sheets[sa.sheet]['page_no']}"]}, {"value": sb.mark, "sources": [f"page {sheets[sb.sheet]['page_no']}"]}), None))
      
    by_mark: dict = {}
    for s in loose:
      by_mark.setdefault(s.mark, []).append(s)
    for mark, g in sorted(by_mark.items(), key=lambda kv: str(kv[0])):
      if mark is not None and made.get(mark):
        k = made[mark][0]
        m = members[k]
        members[k] = Member(m.id, m.kind, m.mark, m.floor, m.outline, m.size_mm or _best(g).size, m.height_mm, m.sightings + tuple(_sighting(sheets, s) for s in g))
      else:
        members.append(Member(_id(kind, floor, mark, NO_POSITION), kind, mark, floor, (), _best(g).size, _height(levels, floor), tuple(_sighting(sheets, s) for s in g)))
    for mk in {m.mark for m in members if m.kind == kind and m.floor == floor and m.mark}:
      counts.setdefault((kind, mk), {})[floor] = sum(1 for m in members if m.kind == kind and m.floor == floor and m.mark == mk)
  return MemberSet(tuple(members), tuple(decisions), tuple(unregistered), counts)

def _mark_key(mark) -> str:
  return "".join(ch for ch in str(mark or "").upper() if ch.isalnum())

def merge(ms: MemberSet, ifc: tuple) -> MemberSet:
  if not ifc:
    return ms

  members = list(ms.members)
  decisions = list(ms.decisions)
  sizes: dict = dict(ms.ifc_sizes)
  slots: dict = {}
  
  for i, m in enumerate(members):
    if m.mark:
      slots.setdefault((m.kind, m.floor, _mark_key(m.mark)), []).append(i)
  by_key: dict = {}
  for im in ifc:
    by_key.setdefault((im.kind, im.floor, _mark_key(im.mark) if im.mark else None), []).append(im)
  extra = []
  for key, group in sorted(by_key.items(), key=lambda kv: str(kv[0])):
    mine = sorted(slots.get(key, []), key=lambda i: (members[i].size_mm is None, members[i].size_mm or ()))
    theirs = sorted(group, key=lambda m: (m.size_mm is None, m.size_mm or ()))
    for n, im in enumerate(theirs):
      if n >= len(mine):
        extra.append(im)
        continue
      k = mine[n]
      m = members[k]
      
      members[k] = Member(m.id, m.kind, m.mark, m.floor, m.outline, m.size_mm or im.size_mm, m.height_mm if m.height_mm is not None else im.height_mm, m.sightings + im.sightings)
      if im.size_mm:
        sizes.setdefault(m.id, []).append(im.size_mm)
      if m.size_mm and im.size_mm and not _same_size(m.size_mm, im.size_mm):
        decisions.append(Decision(f"ifc_size:{m.id}", f"Size of {m.mark} on {m.floor or 'its sheet'}: the PDF and the IFC model differ",
          ({"value": list(m.size_mm), "sources": [m.sightings[0].basis]}, {"value": list(im.size_mm), "sources": ["IFC"]}), None))
  return MemberSet(tuple(members) + tuple(extra), tuple(decisions), ms.unregistered, ms.counts, sizes)

def as_rows(ms: MemberSet, sheet_of: dict | None = None) -> list:
  sheet_of = sheet_of or {}
  return [{"id": m.id, "kind": m.kind, "mark": m.mark, "floor": m.floor, "size_mm": list(m.size_mm) if m.size_mm else None, "height_mm": m.height_mm, "positioned": bool(m.outline),
    "sightings": [{"drawing_id": s.drawing_id, "page_no": s.page_no, "sheet_id": sheet_of.get((s.drawing_id, s.page_no)), "candidate_key": s.candidate_key, "basis": s.basis} for s in m.sightings]}
    for m in ms.members]
