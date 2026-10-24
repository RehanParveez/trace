from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract.floor_union_service import FloorUnionService
from uuid import UUID
from app.modules.drawings_boq.takeoff.extract import conflicts as CF
from app.modules.drawings_boq.takeoff.prep.details import norm_mark
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.takeoff.extract import links as LK
from app.modules.drawings_boq.takeoff.extract import steel_rollup as SR
from app.modules.drawings_boq.takeoff.printed_service import printed_for_drawings

DROP_AFTER_CHOICE = {"BEAM_SECTION": ("BEAM_SECTIONS_LISTED",), "SLAB_THICKNESS": (), "SOURCE_COUNT": ()}

def _intensity_ranges() -> dict:
  try:
    from app.engine.measure.pdf_steel import intensity_range
  except Exception:
    return {}
  out: dict = {}
  for fam in ("BEAM", "COLUMN", "FOOTING", "SLAB"):
    band = intensity_range(fam)
    if band:
      out[fam] = (float(band[0]), float(band[1]))
  return out

class ReviewService(FloorUnionService):

  async def _everything(self, org: UUID, drawing_id: UUID) -> tuple:
    read, _ = await self._read(org, drawing_id)
    rows = [c for s in read for c in s["candidates"]]
    sheets = {s["sheet_id"]: {"page_no": s["page_no"], "discipline": CF.sheet_discipline(s["title"])} for s in read}
    return rows, sheets

  async def conflicts(self, org: UUID, drawing_id: UUID, policy: dict | None = None) -> dict:
    rows, sheets = await self._everything(org, drawing_id)
    sections = await self.prep.drawing_beam_sections(org, drawing_id)
    return {"drawing_id": drawing_id, **CF.build(rows, sheets, sections, policy)}

  async def resolve(self, org: UUID, user_id: UUID, drawing_id: UUID, payload) -> dict:
    rows, sheets = await self._everything(org, drawing_id)
    sections = await self.prep.drawing_beam_sections(org, drawing_id)
    view = CF.build(rows, sheets, sections, payload.policy)
    picks = {k: v for k, v in (payload.choices or {}).items()}
    wanted = CF.resolutions(view["conflicts"], picks, use_policy=payload.apply_policy)
    by_id = {str(r.id): r for r in rows}
    section_of = {norm_mark(str(s["mark"])): s for s in sections if s.get("mark")}
    changed: list = []
    skipped: list = []
    touched: set = set()
    
    for rec in wanted:
      for iid in rec["item_ids"]:
        row = by_id.get(iid)
        if row is None or row.decision != "NEW":
          skipped.append({"id": iid, "code": "ALREADY_DECIDED", "message": "This item is already accepted or rejected, so its value is left alone."})
          continue
      
        section = section_of.get(norm_mark(str(rec["mark"]))) if rec.get("mark") else None
        if not CF.apply_to_row(row, rec, section):
          continue
        drop = DROP_AFTER_CHOICE.get(rec["kind"], ())
        if drop:
          row.notes = [n for n in (row.notes or []) if n.get("code") not in drop]
        touched.add(row.sheet_id)
        changed.append({"id": iid, "kind": rec["kind"], "by": rec["by"], "value": rec.get("value_mm") if rec.get("value_mm") is not None else rec.get("count")})
        if rec["kind"] == CF.COUNT:
          touched |= self._follow_lintels(rows, row, int(rec["count"]))
          
    if changed:
      await self.core._log(org, user_id, drawing_id, AuditAction.UPDATE,
        f"Settled {len(changed)} values the drawing prints differently ({'policy' if payload.apply_policy and not picks else 'chosen'})")
    await self.session.flush()
    if touched:
      await self._sync_register(org, touched)
    await self.session.commit()
    again = CF.build(rows, sheets, sections, payload.policy)
    return {"resolved": len(changed), "items": changed, "skipped": skipped, "conflicts": {"drawing_id": drawing_id, **again}}

  @staticmethod
  def _follow_lintels(rows: list, door_or_window, count: int) -> set:
    tag = str(door_or_window.tag or "")
    floor = ((door_or_window.facts or {}).get("floor_union") or {}).get("floor")
    out: set = set()
    
    if not tag or door_or_window.category not in ("DOOR", "WINDOW"):
      return out
    for r in rows:
      if r.category == "LINTEL" and r.decision == "NEW" and r.sheet_id == door_or_window.sheet_id and str(r.tag or "") == f"L-{tag}" and ((r.facts or {}).get("floor_union") or {}).get("floor") == floor:
        s = (r.facts or {}).get("split") or {}
        r.count = max(count - int(s.get("in_thin_wall") or 0) - int(s.get("in_rcc_left_out") or 0), 0) if s else count
        out.add(r.sheet_id)
    return out

  async def links(self, org: UUID, drawing_id: UUID) -> dict:
    rows, _ = await self._everything(org, drawing_id)
    return {"drawing_id": drawing_id, **LK.report(rows)}

  async def steel_rollup(self, org: UUID, drawing_id: UUID, conventions: dict | None = None) -> dict:
    rows, _ = await self._everything(org, drawing_id)
    printed = await printed_for_drawings(self.session, org, [drawing_id])
    return {"drawing_id": drawing_id, **SR.rollup(rows, conventions, _intensity_ranges(), printed)}
