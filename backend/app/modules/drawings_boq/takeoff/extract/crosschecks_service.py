from __future__ import annotations
from uuid import UUID
from app.modules.drawings_boq.takeoff.extract import crosschecks as CK, ready as RD
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService

class CrossCheckService(ExtractService):
  """The checks between the readers of a drawing, worked out from what is stored now (nothing is saved, so they are never out of date)."""

  async def checks(self, org: UUID, drawing_id: UUID) -> dict:
    await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    exts = {e.sheet_id: e for e in await self.repo.extractions(org, [s.id for s in sheets])}
    rows = await self.repo.candidates(org, [s.id for s in sheets if s.id in exts])
    
    by: dict = {}
    for r in rows:
      by.setdefault(r.sheet_id, []).append(r)
    return [{"sheet_id": s.id, "page_no": s.page_no, "title": (s.prep_meta or {}).get("title"), "stats": exts[s.id].stats, "candidates": by.get(s.id, []),
      "schedule": (s.prep_meta or {}).get("schedule")} for s in sheets if s.id in exts]

  async def checks(self, org: UUID, drawing_id: UUID) -> dict:
    return {"drawing_id": drawing_id, **CK.run(await self._read(org, drawing_id))}

  async def ready_to_accept(self, org: UUID, drawing_id: UUID) -> dict:
    return {"drawing_id": drawing_id, **RD.ready(await self._read(org, drawing_id))}
