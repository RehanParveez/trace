from __future__ import annotations
from uuid import UUID
from app.modules.drawings_boq.takeoff.extract.mark_entities_service import MarkEntityService
from app.modules.drawings_boq.datums import DatumsService
from app.modules.drawings_boq.takeoff.model import members as MB
from app.modules.drawings_boq.takeoff.extract import ifc_members as IM
from app.modules.drawings_boq.takeoff.extract.layout_groups import undecided_sheets
from app.modules.drawings_boq.takeoff.extract.ready import mark_skip

class MemberService(MarkEntityService):

  async def members(self, org: UUID, drawing_id: UUID) -> dict:
    read, _ = await self._read(org, drawing_id, project=True)
    drawing = await self.core._pdf_drawing(org, drawing_id)
    prepared = await self.prep.drawing_floor_heights(org, drawing_id, await DatumsService(self.session).stored_for_run(org, drawing.project_id))
    plans = [s for s in read if "title" in s and "stats" in s]
    
    found = MB.merge(MB.build(plans, prepared["levels"], mark_skip(undecided_sheets(plans))), await IM.of_project(self.session, org, drawing.project_id))
    sheet_of = {(str(r.get("drawing_id")), r["page_no"]): r["sheet_id"] for r in plans}
    n = len({r.get("drawing_id") for r in read if r.get("drawing_id")})
    return {"drawing_id": drawing_id, "project_wide": n > 1, "members": MB.as_rows(found, sheet_of), "decisions": [d.as_dict() for d in found.decisions], "summary": found.summary()}