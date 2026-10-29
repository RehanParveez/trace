from __future__ import annotations
from uuid import UUID
from app.modules.drawings_boq.takeoff.extract import crosschecks as CK, ready as RD
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from app.modules.drawings_boq.takeoff.extract import ifc_members as IM

class CrossCheckService(ExtractService):
  """The checks between the readers of a drawing, worked out from what is stored now (nothing is saved, so they are never out of date)."""

  async def _read(self, org: UUID, drawing_id: UUID) -> list:
    await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    exts = {e.sheet_id: e for e in await self.repo.extractions(org, [s.id for s in sheets])}
    rows = await self.repo.candidates(org, [s.id for s in sheets if s.id in exts])
    
    by: dict = {}
    for r in rows:
      by.setdefault(r.sheet_id, []).append(r)
    return [{"sheet_id": s.id, "page_no": s.page_no, "title": (s.prep_meta or {}).get("title"), "stats": exts[s.id].stats, "candidates": by.get(s.id, []),
      "schedule": (s.prep_meta or {}).get("schedule"), "outline_check": (s.prep_meta or {}).get("outline_check")} for s in sheets if s.id in exts]

  async def checks(self, org: UUID, drawing_id: UUID) -> dict:
    return {"drawing_id": drawing_id, **CK.run(await self._read(org, drawing_id))}

  async def ready_to_accept(self, org: UUID, drawing_id: UUID) -> dict:
    drawing = await self.core._pdf_drawing(org, drawing_id)
    return {"drawing_id": drawing_id, **RD.ready(await self._read(org, drawing_id), ifc=await IM.of_project(self.session, org, drawing.project_id))}
