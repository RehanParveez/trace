from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from uuid import UUID
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.reading_report import build as B
from app.modules.drawings_boq.takeoff.reading_report.models import ReadingOverride, ReadingMisreadReport
from app.modules.drawings_boq.takeoff.reading_report.repository import ReadingReportRepository

class ReadingReportService(ExtractService):
  def __init__(self, session):
    super().__init__(session)
    self.store = ReadingReportRepository(session)

  async def _load(self, org: UUID, drawing_id: UUID):
    drawing = await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    ids = [s.id for s in sheets]
    cands: dict = {}
    for c in await self.repo.candidates(org, ids):
      cands.setdefault(c.sheet_id, []).append(c)
    exts = {e.sheet_id: e for e in await self.repo.extractions(org, ids)}
    return drawing, sheets, exts, cands

  async def report(self, org: UUID, drawing_id: UUID, with_items: bool = False) -> dict:
    _, sheets, exts, cands = await self._load(org, drawing_id)
    out = B.build_report(drawing_id, sheets, exts, cands, await self.store.override_counts(org, drawing_id), await self.store.misread_counts(org, drawing_id), with_items)
    out["manual_marks_are_scored"] = False
    out["joins_applied_to_quantities"] = False
    return out

  async def sheet_items(self, org: UUID, drawing_id: UUID, sheet_id: UUID) -> dict:
    await self.core._pdf_drawing(org, drawing_id)
    sheet = await self.core._sheet(org, sheet_id)
    if sheet.drawing_id != drawing_id:
      raise TraceException("Sheet not found.", status_code=404, code="SHEET_NOT_FOUND")
    rows = await self.repo.candidates(org, [sheet_id])
    return {"sheet_id": sheet_id, "items": [B.item_row(c) for c in rows if c.decision != "REJECTED"]}

  async def completeness(self, org: UUID, project_id: UUID) -> dict:
    cands: list = []
    for d in await self.core.repo.project_pdf_drawings(org, project_id):
      ids = [s.id for s in await self.core.repo.sheets(org, d.id)]
      cands.extend(await self.repo.candidates(org, ids))
    out = B.completeness(cands)
    out["project_id"] = project_id
    return out

  async def _sheet_of(self, org: UUID, drawing_id: UUID, sheet_id: UUID):
    drawing = await self.core._pdf_drawing(org, drawing_id)
    sheet = await self.core._sheet(org, sheet_id)
    if sheet.drawing_id != drawing_id:
      raise TraceException("That sheet is not part of this drawing.", status_code=404, code="SHEET_NOT_FOUND")
    return drawing, sheet

  async def list_overrides(self, org: UUID, drawing_id: UUID, sheet_id: UUID | None) -> dict:
    await self.core._pdf_drawing(org, drawing_id)
    return {"drawing_id": drawing_id, "overrides": [self._override_out(r) for r in await self.store.overrides(org, drawing_id, sheet_id)]}

  @staticmethod
  def _override_out(r: ReadingOverride) -> dict:
    return {"id": r.id, "drawing_id": r.drawing_id, "sheet_id": r.sheet_id, "item_class": r.item_class, "mark": r.mark, "geometry": r.geometry, "attrs": r.attrs, "note": r.note,
      "status": r.status, "image_checked": bool(r.image_checked), "created_at": r.created_at, "counts_as_truth": bool(r.image_checked)}

  async def add_override(self, org: UUID, user_id: UUID, drawing_id: UUID, payload) -> dict:
    drawing, _ = await self._sheet_of(org, drawing_id, payload.sheet_id)
    row = ReadingOverride(organization_id=org, project_id=drawing.project_id, drawing_id=drawing_id, sheet_id=payload.sheet_id, item_class=payload.item_class, mark=(payload.mark or None),
      geometry=payload.geometry, attrs=payload.attrs, note=payload.note, created_by_user_id=user_id)
    self.store.add(row)
    await self.session.flush()
    await self.session.commit()
    await self.session.refresh(row)
    return self._override_out(row)

  async def withdraw_override(self, org: UUID, drawing_id: UUID, override_id: UUID) -> dict:
    await self.core._pdf_drawing(org, drawing_id)
    row = await self.store.override(org, drawing_id, override_id)
    if row is None:
      raise TraceException("Manual mark not found.", status_code=404, code="OVERRIDE_NOT_FOUND")
    row.status = "WITHDRAWN"
    await self.session.commit()
    return self._override_out(row)

  async def add_misread(self, org: UUID, user_id: UUID, drawing_id: UUID, payload) -> dict:
    drawing, sheet = await self._sheet_of(org, drawing_id, payload.sheet_id)
    ckey = item_class = mark = None
    version = None
    ext = await self.repo.extraction(org, sheet.id)
    if ext is not None:
      version = ext.extract_version
    if payload.candidate_id is not None:
      cand = (await self.repo.candidates_by_ids(org, [payload.candidate_id]) or [None])[0]
      if cand is None or cand.sheet_id != sheet.id:
        raise TraceException("That item is not on this sheet.", status_code=404, code="CANDIDATE_NOT_FOUND")
      ckey, mark = cand.ckey, cand.tag
      item_class = B.RS.class_of(cand) or "OTHER"
      if not payload.read_as:
        payload = payload.model_copy(update={"read_as": {"label": cand.label, "params": dict(cand.params or {}), "status": B.shown_status(cand), "reasons": B.RS.reasons_of(cand)}})
    row = ReadingMisreadReport(organization_id=org, project_id=drawing.project_id, drawing_id=drawing_id, sheet_id=sheet.id, candidate_id=payload.candidate_id, ckey=ckey,
      item_class=(payload.item_class or item_class), mark=(payload.mark or mark), kind=payload.kind, box=payload.box, expected=payload.expected, read_as=payload.read_as,
      note=payload.note, extract_version=version, reported_by_user_id=user_id)
    
    self.store.add(row)
    await self.session.flush()
    await self.session.commit()
    await self.session.refresh(row)
    return {k: getattr(row, k) for k in ("id", "drawing_id", "sheet_id", "candidate_id", "ckey", "item_class", "mark", "kind", "box", "expected", "read_as", "note", "extract_version", "status", "created_at")}

  async def list_misreads(self, org: UUID, drawing_id: UUID) -> list:
    await self.core._pdf_drawing(org, drawing_id)
    return [{k: getattr(r, k) for k in ("id", "drawing_id", "sheet_id", "candidate_id", "ckey", "item_class", "mark", "kind", "box", "expected", "read_as", "note", "extract_version", "status", "created_at")}
      for r in await self.store.misreads(org, drawing_id)]
