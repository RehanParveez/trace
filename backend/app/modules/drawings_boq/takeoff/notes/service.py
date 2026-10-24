from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from uuid import UUID
from app.modules.drawings_boq.takeoff.prep import facts as drawing_facts, printed_params
from app.modules.drawings_boq.takeoff.notes import fates

class NotesService(ExtractService):
  async def report(self, org: UUID, drawing_id: UUID) -> dict:
    await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    read = [{"page_no": s.page_no, "label": s.label, "facts": (s.prep_meta or {}).get("facts")} for s in sheets if (s.prep_meta or {}).get("facts") is not None]
    items = drawing_facts.gather(read)["items"]
    page_of = {s.id: s.page_no for s in sheets}
    rows = await self.repo.candidates(org, [s.id for s in sheets])
    cands = [{"page_no": page_of.get(c.sheet_id), "category": c.category, "facts": c.facts or {}, "count": int(c.count or 1),
      "codes": [n.get("code") for n in (c.notes or []) if isinstance(n, dict)]} for c in rows if c.decision != "REJECTED"]
    out = fates.ledger(items, printed_params.from_items(items), cands)
    return {"drawing_id": drawing_id, "sheets_read": len(read), "sheets_total": len(sheets), **out}
