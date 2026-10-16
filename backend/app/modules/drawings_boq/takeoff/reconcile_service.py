from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.takeoff.frame_service import FrameService
from uuid import UUID
from app.modules.drawings_boq.models import DrawingElement, Drawing, DrawingFormat, DrawingStatus
from sqlalchemy import func, select
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff import frame_views as FV
from app.modules.drawings_boq.takeoff import reconcile_view as RV

MAX_SHIFT_MM = 1_000_000.0

class ReconcileService:

  def __init__(self, session: AsyncSession):
    self.session = session
    self.frames = FrameService(session)

  async def _models(self, org: UUID, project_id: UUID) -> list:
    rows = (await self.session.execute(
      select(Drawing, func.count(DrawingElement.id))
      .join(DrawingElement, DrawingElement.drawing_id == Drawing.id)
      .where(Drawing.organization_id == org, Drawing.project_id == project_id, Drawing.format == DrawingFormat.IFC, Drawing.status == DrawingStatus.PARSED,
        DrawingElement.organization_id == org, DrawingElement.structural_role == RV.COLUMN_ROLE)
      .group_by(Drawing.id).order_by(Drawing.created_at.desc(), Drawing.id))).all()
    return [(d, int(n)) for d, n in rows]

  async def reconcile(self, org: UUID, drawing_id: UUID, model_drawing_id: UUID | None = None, dx_mm: float | None = None, dy_mm: float | None = None) -> dict:
    drawing = await self.frames._drawing(org, drawing_id)
    if drawing.format != DrawingFormat.PDF:
      raise TraceException("Only a PDF drawing is set against a model.", status_code=422, code="DRAWING_NOT_PDF")
    if (dx_mm is None) != (dy_mm is None) or any(v is not None and abs(v) > MAX_SHIFT_MM for v in (dx_mm, dy_mm)):
      raise TraceException("Give both parts of the shift in millimetres, or neither.", status_code=422, code="RECONCILE_SHIFT_INVALID")
    models = await self._models(org, drawing.project_id)
    out: dict = {"drawing_id": drawing_id, "models": [{"drawing_id": d.id, "filename": d.original_filename, "columns": n} for d, n in models]}
    chosen = None
    
    if model_drawing_id is not None:
      chosen = next((d for d, _ in models if d.id == model_drawing_id), None)
      if chosen is None:
        raise TraceException("That model has no columns, or is not part of this project.", status_code=422, code="RECONCILE_MODEL_UNKNOWN")
    elif models:
      chosen = models[0][0]
    if chosen is None:
      return {**out, "model_drawing_id": None, "status": "NONE", "reason": "NO_MODEL"}
    s = await self.frames._state(org, drawing_id)
    
    if s["frame"] is None:
      return {**out, "model_drawing_id": chosen.id, "status": "NONE", "reason": "NO_PDF_COLUMNS"}
    members = FV.placed_members(s["formwork"], s["group_of_sheet"], {s["group"]: s["frame"]}).get(s["group"], {})
    elements = list((await self.session.execute(select(DrawingElement).where(DrawingElement.organization_id == org, DrawingElement.drawing_id == chosen.id,
      DrawingElement.structural_role == RV.COLUMN_ROLE))).scalars().all())
    got = RV.build(members, elements, offset=(dx_mm, dy_mm) if dx_mm is not None else None)
    if got["pdf_places"] == 0:
      return {**out, "model_drawing_id": chosen.id, "status": "NONE", "reason": "NO_PDF_COLUMNS"}
    return {**out, "model_drawing_id": chosen.id, **got}
