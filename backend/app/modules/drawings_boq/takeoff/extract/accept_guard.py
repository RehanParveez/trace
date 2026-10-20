from __future__ import annotations
import re
from sqlalchemy import select
from app.modules.drawings_boq.models import TakeoffCandidate, TakeoffMeasurement, TakeoffSheet

CODE = "MARK_ACCEPTED_ELSEWHERE"
MARKED = ("COLUMN", "FOOTING", "DOOR", "WINDOW", "SITE")

def norm(tag) -> str:
  """C-2, C 2 and c2 are the same mark."""
  return re.sub(r"[^A-Z0-9]", "", str(tag or "").upper())

def key_of(category: str, tag, floor) -> tuple | None:
  if category == "SITE":
    floor = "SITE"
  if category not in MARKED or not norm(tag) or floor is None:
    return None
  return (category, norm(tag), str(floor))

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
    k = key_of(cand.category, cand.tag, floor)
    if k is None:
      return None
    other = {s: p for s, p in self.held.get(k, {}).items() if s != cand.sheet_id}
    return message(cand.tag, list(other.values()), cand.category == "SITE") if other else None

  def add(self, cand, floor, page=None) -> None:
    k = key_of(cand.category, cand.tag, floor)
    if k is not None:
      self.held.setdefault(k, {})[cand.sheet_id] = page

async def load(session, org, project_id, wanted: list) -> Guard:
  marks = {key_of(c.category, c.tag, 0) for c in wanted if c.category in MARKED}
  marks.discard(None)
  if not marks:
    return Guard()

  tags = {m[1] for m in marks}
  rows = (await session.execute(
    select(TakeoffCandidate.sheet_id, TakeoffCandidate.category, TakeoffCandidate.tag, TakeoffMeasurement.level_id, TakeoffSheet.page_no)
    .join(TakeoffMeasurement, TakeoffMeasurement.id == TakeoffCandidate.measurement_id)
    .join(TakeoffSheet, TakeoffSheet.id == TakeoffCandidate.sheet_id)
    .where(TakeoffCandidate.organization_id == org, TakeoffCandidate.project_id == project_id, TakeoffCandidate.decision == "ACCEPTED",
      TakeoffCandidate.category.in_(MARKED), TakeoffCandidate.tag.is_not(None)))).all()
  g = Guard()
  for sheet_id, category, tag, level_id, page in rows:
    if norm(tag) in tags:
      k = key_of(category, tag, level_id)
      if k is not None:
        g.held.setdefault(k, {})[sheet_id] = page
  return g

def held_marks(read: list, floor_of) -> dict:
  out: dict = {}
  for sh in read:
    for c in sh["candidates"]:
      if c.decision != "ACCEPTED":
        continue
      k = key_of(c.category, c.tag, floor_of(c, sh))
      if k is not None:
        out.setdefault(k, {})[sh["sheet_id"]] = sh["page_no"]
  return out
