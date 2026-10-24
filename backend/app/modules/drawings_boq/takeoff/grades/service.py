from __future__ import annotations
import logging
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from uuid import UUID
from app.modules.drawings_boq.models import TakeoffMeasurement
from sqlalchemy import select
from app.modules.drawings_boq.takeoff.grades import stamp as GS
from app.engine.measure import grades as G
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.takeoff.prep import printed_params as PP
from app.modules.drawings_boq.takeoff.printed_service import printed_for_drawings

log = logging.getLogger(__name__)

class GradesService(ExtractService):
  async def _load(self, org: UUID, drawing_id: UUID) -> tuple:
    drawing = await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    rows = await self.repo.candidates(org, [s.id for s in sheets])
    ids = [c.measurement_id for c in rows if c.measurement_id]
    measurements: dict = {}
    if ids:
      measurements = {m.id: m for m in (await self.session.execute(select(TakeoffMeasurement).where(TakeoffMeasurement.organization_id == org,
        TakeoffMeasurement.id.in_(ids)))).scalars().all()}
    printed = await printed_for_drawings(self.session, org, [drawing_id])
    return drawing, rows, measurements, printed

  @staticmethod
  def _members(rows: list, measurements: dict, printed: dict) -> list:
    rules = printed.get("grades") or {}
    seen: dict = {}
    
    for c in rows:
      if c.decision == "REJECTED":
        continue
      member = GS.member_of(c)
      if member is None:
        continue
      slot = seen.setdefault(member, {"measured": 0, "stamped": 0, "typed": 0, "open": 0, "confirmed_open": 0, "found": 0})
      slot["found"] += 1
      m = measurements.get(c.measurement_id) if c.measurement_id and c.decision == "ACCEPTED" else None
      if m is None:
        continue
      slot["measured"] += 1
      kind = GS.classify(c, m.material_grade)
      if kind == "STAMPED":
        slot["stamped"] += 1
      elif kind == "TYPED":
        slot["typed"] += 1
      elif GS.is_concrete_code(m.work_item_code) and GS.stamp_for(c, rules.get("concrete")) is not None:
        slot["open"] += 1
        if m.status == "CONFIRMED":
          slot["confirmed_open"] += 1
          
    out = []
    for member in G.MEMBER_KINDS:
      crule = G.resolve(rules.get("concrete"), member)
      srule = G.resolve(rules.get("steel"), member)
      rrule = G.resolve(rules.get("steel"), member, "RING")
      ring_own = rrule["rule"] is not None and rrule["rule"].get("part") == "RING"
      slot = seen.get(member)
      
      if slot is None and crule["rule"] is None and srule["rule"] is None and not crule["clash"] and not srule["clash"] and not ring_own and not (rrule["clash"] and not srule["clash"]):
        continue
      out.append({"member": member, "label": GS.LABELS.get(member, member), **(slot or {"measured": 0, "stamped": 0, "typed": 0, "open": 0, "confirmed_open": 0, "found": 0}),
        "concrete": {k: crule["rule"].get(k) for k in ("class", "mix", "scope", "pages")} if crule["rule"] else None, "concrete_clash": crule["clash"],
        "steel": {k: srule["rule"].get(k) for k in ("label", "scope", "pages")} if srule["rule"] else None, "steel_clash": srule["clash"],
        "steel_ring": {k: rrule["rule"].get(k) for k in ("label", "scope", "pages")} if ring_own else None, "steel_ring_clash": rrule["clash"] if (ring_own or rrule["clash"] != srule["clash"]) else []})
    return out

  @staticmethod
  def _mixes(rows: list, measurements: dict) -> list:
    """The mixes printed for the lines that are not structural members (plaster mortar, plain concrete beds, cement-sand beds), one row for each kind of work and mix."""
    seen: dict = {}
    for c in rows:
      if c.decision == "REJECTED":
        continue

      mix = GS.mix_of(c)
      if mix is None:
        continue
      slot = seen.setdefault((mix["what"], mix["grade"]), {"what": mix["what"], "grade": mix["grade"], "pages": set(), "found": 0, "measured": 0, "stamped": 0, "typed": 0, "open": 0,
        "confirmed_open": 0})
      slot["found"] += 1
      slot["pages"].update(mix["pages"])
      m = measurements.get(c.measurement_id) if c.measurement_id and c.decision == "ACCEPTED" else None

      if m is None:
        continue
      slot["measured"] += 1
      if not m.material_grade:
        slot["open"] += 1
        if m.status == "CONFIRMED":
          slot["confirmed_open"] += 1
      elif m.material_grade == mix["grade"]:
        slot["stamped"] += 1
      else:
        slot["typed"] += 1
    return [{**s, "pages": sorted(s["pages"])} for _, s in sorted(seen.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1])))]

  def _report(self, drawing, rows: list, measurements: dict, printed: dict, changed: int = 0) -> dict:
    members = self._members(rows, measurements, printed)
    mixes = self._mixes(rows, measurements)
    params = printed.get("params") or {}
    notes = printed.get("notes") or {}
    plaster = {"thickness_mm": params.get(PP.PLASTER_PARAM), "note": notes.get(PP.PLASTER_PARAM)}
    summary = {"concrete_notes": len((printed.get("grades") or {}).get("concrete") or []), "steel_notes": len((printed.get("grades") or {}).get("steel") or []),
      "mix_notes": len(mixes), "measured": sum(m["measured"] for m in members + mixes), "stamped": sum(m["stamped"] for m in members + mixes),
      "typed": sum(m["typed"] for m in members + mixes), "open": sum(m["open"] for m in members + mixes), "confirmed_open": sum(m["confirmed_open"] for m in members + mixes),
      "clashes": sum(1 for m in members if m["concrete_clash"] or m["steel_clash"] or m["steel_ring_clash"])}
    return {"drawing_id": drawing.id, "concrete": (printed.get("grades") or {}).get("concrete") or [], "steel": (printed.get("grades") or {}).get("steel") or [], "members": members, "mixes": mixes,
      "plaster": plaster, "soil": printed.get("soil"), "conflicts": printed.get("conflicts") or [], "summary": summary, "changed": changed}

  async def report(self, org: UUID, drawing_id: UUID) -> dict:
    drawing, rows, measurements, printed = await self._load(org, drawing_id)
    return self._report(drawing, rows, measurements, printed)

  async def stamp(self, org: UUID, user_id: UUID, drawing_id: UUID, include_confirmed: bool) -> dict:
    drawing, rows, measurements, printed = await self._load(org, drawing_id)
    rules = (printed.get("grades") or {}).get("concrete") or []
    changed = 0
    
    for c in rows:
      m = measurements.get(c.measurement_id) if c.measurement_id and c.decision == "ACCEPTED" else None
      if m is None or m.material_grade:
        continue
      s = GS.stamp_for(c, rules) if GS.is_concrete_code(m.work_item_code) else None
      if s is None:
        s = GS.mix_stamp(c)
      if s is None:
        continue
      if m.status == "CONFIRMED":
        if not include_confirmed:
          continue
      
        m.status, m.confirmed_at, m.confirmed_by_user_id = "DRAFT", None, None
      m.material_grade = s["grade"][:50]
      c.facts = {**(c.facts or {}), GS.KEY: s}
      changed += 1
    await self.session.flush()
    if changed:
      await self.core._log(org, user_id, drawing.id, AuditAction.UPDATE, f"Gave the printed mix to {changed} measured line(s)")
    await self.session.commit()
    return self._report(drawing, rows, measurements, printed, changed)

  async def unstamp(self, org: UUID, user_id: UUID, drawing_id: UUID) -> dict:
    drawing, rows, measurements, printed = await self._load(org, drawing_id)
    changed = 0
    
    for c in rows:
      m = measurements.get(c.measurement_id) if c.measurement_id else None
      s = GS.stamped(c)
      if s is None and m is not None:
        s = GS.mix_of(c)
      if m is None or s is None:
        continue
      if m.material_grade == s.get("grade"):
        if m.status == "CONFIRMED":
          m.status, m.confirmed_at, m.confirmed_by_user_id = "DRAFT", None, None
        m.material_grade = None
        changed += 1
        
      facts = dict(c.facts or {})
      facts.pop(GS.KEY, None)
      c.facts = facts
    await self.session.flush()
    if changed:
      await self.core._log(org, user_id, drawing.id, AuditAction.UPDATE, f"Took back the printed mix from {changed} measured line(s)")
    await self.session.commit()
    return self._report(drawing, rows, measurements, printed, changed)