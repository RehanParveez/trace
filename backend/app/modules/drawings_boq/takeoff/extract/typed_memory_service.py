from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from uuid import UUID
from app.modules.drawings_boq.takeoff.extract import typed_memory as TM
from app.modules.drawings_boq.takeoff.extract import kinds as KD

class TypedMemoryService(ExtractService):
  """The sizes typed when items of this drawing's project were accepted, newest first, one per kind of item and field."""

  async def memory(self, org: UUID, drawing_id: UUID) -> dict:
    drawing = await self.core._pdf_drawing(org, drawing_id)
    rows = await self.repo.accepted_with_typed(org, drawing.project_id)
    return {"drawing_id": drawing_id, "values": TM.latest([(KD.kind_of(r), r.facts, r.decided_at) for r in rows if (r.facts or {}).get(TM.KEY)])}