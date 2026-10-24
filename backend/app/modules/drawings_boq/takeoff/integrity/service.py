from __future__ import annotations
from uuid import UUID
from app.modules.drawings_boq.takeoff.integrity import checks
from app.modules.drawings_boq.takeoff.extract import config as C
from app.modules.drawings_boq.takeoff.prep import reader_status
from app.modules.drawings_boq.takeoff.decisions import store as decided
from app.modules.drawings_boq.takeoff.notes.service import NotesService

class IntegrityService(NotesService):
  async def integrity(self, org: UUID, drawing_id: UUID) -> dict:
    in_force = decided.effective((await self.core._pdf_drawing(org, drawing_id)).ingestion_meta)
    sheets = await self.core.repo.sheets(org, drawing_id)
    ids = [s.id for s in sheets]
    page_of = {s.id: s.page_no for s in sheets}
    extractions = await self.repo.extractions(org, ids)
    rows = await self.repo.candidates(org, ids)
    linked = await self.repo.existing_measurement_ids(org, [c.measurement_id for c in rows if c.measurement_id])
    notes = await self.report(org, drawing_id)

    out = checks.run(
      [{"page_no": s.page_no, "prep_status": s.prep_status, "content_kind": s.content_kind, "has_facts": (s.prep_meta or {}).get("facts") is not None,
        "text_source": (s.prep_meta or {}).get("text_source")} for s in sheets],
      [{"page_no": page_of.get(e.sheet_id), "extract_version": e.extract_version, "mm_per_pt": float(e.mm_per_pt) if e.mm_per_pt is not None else None,
        "scale_unverified": bool(e.scale_unverified), "decisions_stale": bool(decided.stale(e.stats, in_force))} for e in extractions],
      [{"page_no": page_of.get(c.sheet_id), "decision": c.decision, "status": c.status, "linked": bool(c.measurement_id and c.measurement_id in linked)} for c in rows],
      reader_status.status(), C.EXTRACT_VERSION, notes["summary"])
    return {"drawing_id": drawing_id, "code_version": C.EXTRACT_VERSION, **out}
