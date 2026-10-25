from __future__ import annotations
import re
from sqlalchemy import select
from app.modules.drawings_boq.models import TakeoffCandidate, TakeoffMeasurement, TakeoffSheet

CODE = "MARK_ACCEPTED_ELSEWHERE"
MARKED = ("COLUMN", "FOOTING", "DOOR", "WINDOW", "LINTEL", "STAIR", "BEAM", "SITE")
DRAWN_GROUP = ("DRAWN", "LDRAWN")
FLOOR_TAG = "FLOOR-FINISH"
FLOOR_WET = "FLOOR_WET"

def wet_floor(cand) -> bool:
  """The floor tile of the baths and toilets, a line of its own since the floor finish stopped carrying them."""
  return cand.category == "WALL" and ((getattr(cand, "facts", None) or {}).get("foundation_item")) == FLOOR_WET

def includes_wet(category, tag, facts) -> bool:
  """A floor finish accepted before the baths and toilets were split off: its area carries them."""
  f = facts or {}
  return category == "WALL" and tag == FLOOR_TAG and not f.get("floor_scope") and float(f.get("wet_room_area_m2") or 0.0) > 0.0

def floor_message(pages: list) -> str:
  where = ", ".join(f"page {p}" for p in sorted(set(p for p in pages if p))) if any(pages) else "another read"
  return (f"The floor finish of this floor accepted from {where} already includes the baths and toilets (it was accepted before their floor became a line of its own). Accepting "
    f"their floor tile too counts them twice. Reject this one, or delete that floor finish measurement and read the sheet again to have the two lines.")

def norm(tag) -> str:
  """C-2, C 2 and c2 are the same mark."""
  return re.sub(r"[^A-Z0-9]", "", str(tag or "").upper())

def mark_key(category: str, tag, facts=None) -> tuple | None:
  n = norm(tag)
  if category not in MARKED or not n or n.startswith(DRAWN_GROUP):
    return None
  f = facts or {}
  if category == "BEAM" and (f.get("derived_from") or f.get("from_strips")):
    return None
  return (category, n)

def key_of(category: str, tag, floor, facts=None) -> tuple | None:
  mk = mark_key(category, tag, facts)
  if category == "SITE":
    floor = "SITE"
  if mk is None or floor is None:
    return None
  return (category, mk[1], str(floor))

def message(tag, pages: list, site: bool = False) -> str:
  where = ", ".join(f"page {p}" for p in sorted(set(pages))) if pages else "another sheet"
  if site:
    return (f"{tag} is already accepted from {where}. The same tank, ramp, wall or gate is drawn on several sheets (the plans, the elevations, the details), so accepting it here as well counts it twice. "
      f"Reject this one, or accept it anyway if the project has a second one.")
  return (f"Mark {tag} on this floor is already accepted from {where}. Accepting it here as well counts it twice. Reject this one, or accept it anyway "
    f"once you have checked that it is not the same mark.")

class Guard:
  def __init__(self, held: dict | None = None):
    self.held: dict = {k: dict(v) for k, v in (held or {}).items()}

  def clash(self, cand, floor) -> str | None:
    if wet_floor(cand):
      held = self.held.get(("FLOOR", str(floor)), {})
      return floor_message(list(held.values())) if held else None
    k = key_of(cand.category, cand.tag, floor, cand.facts)
    if k is None:
      return None
    other = {s: p for s, p in self.held.get(k, {}).items() if s != cand.sheet_id}
    return message(cand.tag, list(other.values()), cand.category == "SITE") if other else None

  def add(self, cand, floor, page=None) -> None:
    k = key_of(cand.category, cand.tag, floor, cand.facts)
    if k is not None:
      self.held.setdefault(k, {})[cand.sheet_id] = page

async def load(session, org, project_id, wanted: list) -> Guard:
  marks = {key_of(c.category, c.tag, 0, c.facts) for c in wanted if c.category in MARKED}
  marks.discard(None)
  g = Guard()
  if any(wet_floor(c) for c in wanted):
    old = (await session.execute(
      select(TakeoffCandidate.sheet_id, TakeoffCandidate.category, TakeoffCandidate.tag, TakeoffCandidate.facts, TakeoffMeasurement.level_id, TakeoffSheet.page_no)
      .join(TakeoffMeasurement, TakeoffMeasurement.id == TakeoffCandidate.measurement_id)
      .join(TakeoffSheet, TakeoffSheet.id == TakeoffCandidate.sheet_id)
      .where(TakeoffCandidate.organization_id == org, TakeoffCandidate.project_id == project_id, TakeoffCandidate.decision == "ACCEPTED",
        TakeoffCandidate.category == "WALL", TakeoffCandidate.tag == FLOOR_TAG))).all()
    for sheet_id, category, tag, facts, level_id, page in old:
      if includes_wet(category, tag, facts):
        g.held.setdefault(("FLOOR", str(level_id)), {})[sheet_id] = page
  if not marks:
    return g

  tags = {m[1] for m in marks}
  rows = (await session.execute(
    select(TakeoffCandidate.sheet_id, TakeoffCandidate.category, TakeoffCandidate.tag, TakeoffMeasurement.level_id, TakeoffSheet.page_no, TakeoffCandidate.facts)
    .join(TakeoffMeasurement, TakeoffMeasurement.id == TakeoffCandidate.measurement_id)
    .join(TakeoffSheet, TakeoffSheet.id == TakeoffCandidate.sheet_id)
    .where(TakeoffCandidate.organization_id == org, TakeoffCandidate.project_id == project_id, TakeoffCandidate.decision == "ACCEPTED",
      TakeoffCandidate.category.in_(MARKED), TakeoffCandidate.tag.is_not(None)))).all()
  for sheet_id, category, tag, level_id, page, facts in rows:
    if norm(tag) in tags:
      k = key_of(category, tag, level_id, facts)
      if k is not None:
        g.held.setdefault(k, {})[sheet_id] = page
  return g

def held_marks(read: list, floor_of) -> dict:
  out: dict = {}
  for sh in read:
    for c in sh["candidates"]:
      if c.decision != "ACCEPTED":
        continue
      k = key_of(c.category, c.tag, floor_of(c, sh), c.facts)
      if k is not None:
        out.setdefault(k, {})[sh["sheet_id"]] = sh["page_no"]
      if includes_wet(c.category, c.tag, c.facts):
        out.setdefault(("FLOOR", str(floor_of(c, sh))), {})[sh["sheet_id"]] = sh["page_no"]
  return out
