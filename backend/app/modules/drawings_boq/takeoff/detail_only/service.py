from __future__ import annotations
import logging
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from app.modules.drawings_boq.takeoff.detail_only.repository import DetailOnlyRepository
from uuid import UUID
from decimal import Decimal
from app.modules.drawings_boq.takeoff import detail_only as DO
from app.modules.audit.models import AuditAction
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.prep.details import norm_mark
from app.modules.drawings_boq.takeoff.detail_only.models import DetailMarkDecision

log = logging.getLogger(__name__)

class DetailOnlyService(ExtractService):

  def __init__(self, session):
    super().__init__(session)
    self.store = DetailOnlyRepository(session)

  async def _load(self, org: UUID, drawing_id: UUID) -> tuple:
    drawing = await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    rows = await self.repo.candidates(org, [s.id for s in sheets])
    exts = await self.repo.extractions(org, [s.id for s in sheets])
    return drawing, sheets, rows, exts

  @staticmethod
  def _strip_tags(exts: list) -> list:
    tags: list = []
    for e in exts:
      st = e.stats or {}
      reads = [st.get("beam_strips"), *[v.get("beam_strips") for v in st.get("views") or []]]
      for r in reads:
        tags += list(((r or {}).get("by_tag") or {}).keys())
    return tags

  def _decision_items(self, decisions: list, rows: list, page_of: dict) -> list:
    out = []
    for d in decisions:
      did = str(d.id)
      if d.kind == DO.COLUMN_MARK:
        applied = any(r.sheet_id == d.sheet_id and r.ckey == d.ckey and ((r.facts or {}).get("mark_from_detail") or {}).get("decision_id") == did for r in rows)
      else:
        applied = any(((r.facts or {}).get("depth_choice") or {}).get("decision_id") == did for r in rows)
      out.append({"id": d.id, "kind": d.kind, "mark": d.mark, "sheet_id": d.sheet_id, "page_no": page_of.get(d.sheet_id), "ckey": d.ckey,
        "value_mm": float(d.value_mm) if d.value_mm is not None else None, "applied": applied, "decided_by_user_id": d.decided_by_user_id})
    return out

  async def report(self, org: UUID, drawing_id: UUID, loaded: tuple | None = None) -> dict:
    drawing, sheets, rows, exts = loaded or await self._load(org, drawing_id)
    page_of = {s.id: s.page_no for s in sheets}
    col_sheets = [{"page_no": s.page_no, "details": (s.prep_meta or {}).get("details")} for s in sheets if (s.prep_meta or {}).get("details")]
    beam_sheets = [{"page_no": s.page_no, "details": (s.prep_meta or {}).get("beam_details")} for s in sheets if (s.prep_meta or {}).get("beam_details")]
    out = DO.report(col_sheets, beam_sheets, rows, page_of, self._strip_tags(exts))
    out["drawing_id"] = drawing_id
    out["decisions"] = self._decision_items(await self.store.decisions(org, drawing_id), rows, page_of)
    return out

  async def _finish(self, org: UUID, user_id: UUID, drawing, touched: set, text: str, loaded: tuple) -> dict:
    await self.core._log(org, user_id, drawing.id, AuditAction.UPDATE, text)
    if touched:
      await self._sync_register(org, touched)
    await self.session.commit()
    return await self.report(org, drawing.id)

  async def choose_mark(self, org: UUID, user_id: UUID, drawing_id: UUID, payload) -> dict:
    loaded = await self._load(org, drawing_id)
    drawing, sheets, rows, _ = loaded
    row = next((r for r in rows if r.id == payload.candidate_id), None)
    
    if row is None:
      raise TraceException("This item is not on this drawing.", status_code=404, code="ITEM_NOT_FOUND")
    f = row.facts or {}
    if row.category != "COLUMN" or not f.get("from_shapes"):
      raise TraceException("Only columns found as unmarked shapes take a mark from a detail.", status_code=422, code="ITEM_NOT_UNMARKED_SHAPES")
    if row.decision != "NEW":
      raise TraceException("This item has already been decided. Take the decision back first.", status_code=409, code="ITEM_NOT_OPEN")
    if row.tag and not f.get("mark_from_detail"):
      raise TraceException("This item already has a mark on the plan.", status_code=409, code="ITEM_HAS_MARK")
    shown = next((t for t in f.get("candidate_tags") or [] if t and norm_mark(t) == norm_mark(payload.mark)), None)
    if shown is None:
      raise TraceException("That mark is not one of the marks whose details match the size of these shapes.", status_code=422, code="MARK_NOT_OFFERED")
  
    await self.store.delete_for_row(org, drawing.id, DO.COLUMN_MARK, row.sheet_id, row.ckey)
    d = DetailMarkDecision(organization_id=org, project_id=drawing.project_id, drawing_id=drawing.id, kind=DO.COLUMN_MARK, mark=shown, sheet_id=row.sheet_id, ckey=row.ckey,
      basis={"offered": list(f.get("candidate_tags") or []), "size_mm": list(f.get("size_used_mm") or []), "count": int(row.count or 0)}, decided_by_user_id=user_id)
    
    self.store.add(d)
    await self.session.flush()
    touched = {row.sheet_id} if DO.apply_column_mark(row, shown, str(d.id)) else set()
    return await self._finish(org, user_id, drawing, touched, f"Gave the mark {shown} to {row.count} unmarked column shapes (a detail of that size)", loaded)

  async def choose_depth(self, org: UUID, user_id: UUID, drawing_id: UUID, payload) -> dict:
    loaded = await self._load(org, drawing_id)
    drawing, sheets, rows, _ = loaded
    mark = norm_mark(payload.mark)
    now = await self.report(org, drawing_id, loaded)
    gap = next((g for g in now["depth_gaps"] if g["mark"] == mark), None)
    
    if gap is None:
      raise TraceException("No beam of this mark is waiting for a depth.", status_code=409, code="NO_DEPTH_GAP")
    opt = next((o for o in gap["options"] if abs(o["depth_mm"] - float(payload.depth_mm)) <= DO.DEPTH_SAME_MM), None)
    if opt is None:
      raise TraceException("That depth is not one of the depths printed for other beams of this kind.", status_code=422, code="DEPTH_NOT_OFFERED")
    await self.store.delete_depth(org, drawing.id, mark)
    
    d = DetailMarkDecision(organization_id=org, project_id=drawing.project_id, drawing_id=drawing.id, kind=DO.BEAM_DEPTH, mark=mark, value_mm=Decimal(str(opt["depth_mm"])),
      basis={"from": list(opt["marks"]), "options": gap["options"]}, decided_by_user_id=user_id)
    self.store.add(d)
    await self.session.flush()
    touched = {r.sheet_id for r in rows if DO.apply_beam_depth(r, mark, opt["depth_mm"], str(d.id), opt["marks"])}
    return await self._finish(org, user_id, drawing, touched, f"Chose a depth of {opt['depth_mm']:g} mm for the beams of mark {mark} (printed for {', '.join(opt['marks'])})", loaded)

  async def undo(self, org: UUID, user_id: UUID, drawing_id: UUID, decision_id: UUID) -> dict:
    loaded = await self._load(org, drawing_id)
    drawing, sheets, rows, _ = loaded
    d = await self.store.decision(org, decision_id)
    
    if d is None or d.drawing_id != drawing.id:
      raise TraceException("This decision is not on this drawing.", status_code=404, code="DECISION_NOT_FOUND")
    did = str(d.id)
    touched = {r.sheet_id for r in rows if (DO.undo_column_mark(r, did) if d.kind == DO.COLUMN_MARK else DO.undo_beam_depth(r, did))}
    await self.store.delete(org, d.id)
    return await self._finish(org, user_id, drawing, touched, f"Took back the choice for {d.mark}", loaded)
