from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.drawings_boq.models import DrawingElement, BuildingLevel, Drawing, DrawingFormat, TakeoffCandidate, TakeoffExtraction, TakeoffMeasurement, TakeoffSheet
from app.modules.drawings_boq.takeoff import register as R
from sqlalchemy import delete, select
from app.core.exceptions import TraceException

MAX_ROWS = 20000
ROW_FIELDS = ("ifc_global_id", "ifc_type", "name", "raw_material_text", "unit", "quantity", "properties", "discipline", "structural_role",
  "classification_source", "classification_confidence", "quantity_source", "level_id", "length_mm", "width_mm", "height_mm", "thickness_mm",
  "area_mm2", "volume_mm3", "geometry_kind", "normalization_status", "normalization_issues", "type_mark", "type_name")
CLEARED = ("length_mm", "width_mm", "height_mm", "thickness_mm", "area_mm2", "volume_mm3")

def _is_pdf_row_clause():
  src = DrawingElement.properties["source"].as_string()
  return src == R.SOURCE

class RegisterService:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def _drawing(self, org: UUID, drawing_id: UUID) -> Drawing:
    drawing = (await self.session.execute(select(Drawing).where(Drawing.id == drawing_id, Drawing.organization_id == org))).scalar_one_or_none()
    if drawing is None:
      raise TraceException("Drawing not found.", status_code=404, code="DRAWING_NOT_FOUND")
    if drawing.format != DrawingFormat.PDF:
      raise TraceException("The PDF register is for PDF drawings. IFC drawings fill their register when they are read.", status_code=422,
        code="DRAWING_NOT_PDF")
    return drawing

  async def sync_drawing(self, org: UUID, drawing_id: UUID) -> dict:
    
    drawing = await self._drawing(org, drawing_id)
    sheets = list((await self.session.execute(select(TakeoffSheet).where(TakeoffSheet.organization_id == org, TakeoffSheet.drawing_id == drawing_id)
      .order_by(TakeoffSheet.page_no))).scalars().all())
    by_sheet = {s.id: s for s in sheets}
    cands = list((await self.session.execute(select(TakeoffCandidate).where(TakeoffCandidate.organization_id == org,
      TakeoffCandidate.sheet_id.in_(list(by_sheet) or [None])).order_by(TakeoffCandidate.sheet_id, TakeoffCandidate.category,
      TakeoffCandidate.label, TakeoffCandidate.id))).scalars().all())
    mids = [c.measurement_id for c in cands if c.measurement_id]
    measurements: dict = {}
    
    if mids:
      for m in (await self.session.execute(select(TakeoffMeasurement).where(TakeoffMeasurement.organization_id == org,
          TakeoffMeasurement.id.in_(mids)))).scalars().all():
        measurements[m.id] = {"id": m.id, "status": m.status, "computed": m.computed or {}}
    level_ids = {s.level_id for s in sheets if s.level_id}
    levels: dict = {}
    
    if level_ids:
      levels = {lv.id: lv.name for lv in (await self.session.execute(select(BuildingLevel).where(BuildingLevel.organization_id == org,
        BuildingLevel.id.in_(list(level_ids))))).scalars().all()}
    rows = R.build_rows(cands, by_sheet, measurements, levels)
    
    if len(rows) > MAX_ROWS:
      raise TraceException("This drawing has too many items to list.", status_code=422, code="REGISTER_TOO_LARGE")
    existing = {e.id: e for e in (await self.session.execute(select(DrawingElement).where(DrawingElement.drawing_id == drawing_id,
      DrawingElement.organization_id == org, _is_pdf_row_clause()))).scalars().all()}
    added = updated = 0
    keep: set = set()
    
    for row in rows:
      keep.add(row["id"])
      cur = existing.get(row["id"])
      if cur is None:
        self.session.add(DrawingElement(id=row["id"], drawing_id=drawing_id, organization_id=org,
          **{k: row.get(k) for k in ROW_FIELDS if k in row or k in ("quantity",)}))
        added += 1
        continue
    
      for k in ROW_FIELDS:
        setattr(cur, k, row.get(k))
        
      for k in CLEARED:
        if k not in row:
          setattr(cur, k, None)
      updated += 1
    gone = [i for i in existing if i not in keep]
    
    if gone:
      await self.session.execute(delete(DrawingElement).where(DrawingElement.organization_id == org, DrawingElement.drawing_id == drawing_id,
        DrawingElement.id.in_(gone)))
    await self.session.flush()
    read_ids = {x for x in (await self.session.execute(select(TakeoffExtraction.sheet_id).where(TakeoffExtraction.organization_id == org,
      TakeoffExtraction.sheet_id.in_(list(by_sheet) or [None])))).scalars().all()}
    waiting = [{"page_no": sh.page_no, "sheet_id": str(sh.id),
      "reason": "NOT_PREPARED" if sh.prep_status != "READY" else "NOT_READ"} for sh in sheets if sh.id not in read_ids]
    by_cat: dict = {}
    
    for r in rows:
      by_cat[r["ifc_type"]] = by_cat.get(r["ifc_type"], 0) + 1
    return {"drawing_id": drawing_id, "total": len(rows), "added": added, "updated": updated, "removed": len(gone), "by_type": by_cat,
      "sheets": len(sheets), "sheets_read": len(read_ids), "waiting": waiting, "measured": sum(1 for r in rows if r["properties"]["_pdf"]["mode"] == "PDF_MEASURED"),
      "needs_review": sum(1 for r in rows if r["normalization_status"] != "VALID")}

  async def sync_and_commit(self, org: UUID, drawing_id: UUID) -> dict:
    out = await self.sync_drawing(org, drawing_id)
    await self.session.commit()
    return out