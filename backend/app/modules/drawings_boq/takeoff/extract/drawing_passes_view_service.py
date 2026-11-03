from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from app.modules.drawings_boq.takeoff.extract.drawing_passes_schemas import DrawingPassesResponse, TankSizeRequest
from app.modules.drawings_boq.takeoff.extract import tank_record as TR
from uuid import UUID
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.decisions import store as decided
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.takeoff.extract.drawing_passes_service import META_KEY, reconcile_drawing_passes, typed_tank_decisions

class DrawingPassesService:
  def __init__(self, session):
    self.session = session
    self.extract = ExtractService(session)

  @staticmethod
  def _response(drawing) -> DrawingPassesResponse:
    got = (drawing.ingestion_meta or {}).get(META_KEY) or {}
    typed = {k[len(TR.DECISION_PREFIX):]: v for k, v in typed_tank_decisions(drawing.ingestion_meta).items()}
    return DrawingPassesResponse(drawing_id=drawing.id, ran=bool(got), tanks=list(got.get("tanks") or []), electrical=got.get("electrical"), wall_steel=got.get("wall_steel"), typed=typed)

  async def view(self, org: UUID, drawing_id: UUID) -> DrawingPassesResponse:
    return self._response(await self.extract.core._pdf_drawing(org, drawing_id))

  async def type_tank_size(self, org: UUID, user_id: UUID, drawing_id: UUID, payload: TankSizeRequest) -> DrawingPassesResponse:
    drawing = await self.extract.core._pdf_drawing(org, drawing_id)
    value = (payload.value or "").strip() or None
    if value is not None and TR.decided(value) is None:
      raise TraceException("Type two sizes in mm (length x width, outside) or four (length x width x height x wall thickness).", status_code=422, code="TANK_SIZE_NOT_UNDERSTOOD")
    drawing.ingestion_meta = decided.put(drawing.ingestion_meta, TR.DECISION_PREFIX + payload.kind, value, user_id)
    await self.session.flush()
    
    touched = await reconcile_drawing_passes(self.extract, org, drawing_id)
    await self.extract.core._log(org, user_id, drawing_id, AuditAction.UPDATE, f"Typed the size of the {payload.kind} tank: {value}" if value else f"Took the typed size of the {payload.kind} tank off")
    await self.extract._sync_register(org, touched)
    await self.session.commit()
    return self._response(await self.extract.core._pdf_drawing(org, drawing_id))
