from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from uuid import UUID
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.proof import known_facts as KF
from app.modules.drawings_boq.takeoff.proof import trace as TR
from app.modules.drawings_boq.takeoff.proof import readsummary as RS

class ProofService(ExtractService):

  async def read_of(self, org: UUID, drawing_id: UUID) -> list:
    """The sheets of a drawing that have been read, as the checks between the readers take them, with the notes and the scale analysis of each."""
    await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    exts = {e.sheet_id: e for e in await self.repo.extractions(org, [s.id for s in sheets])}
    rows = await self.repo.candidates(org, [s.id for s in sheets if s.id in exts])
    by: dict = {}
    
    for r in rows:
      by.setdefault(r.sheet_id, []).append(r)
    out = []
    for s in sheets:
      if s.id not in exts:
        continue
      meta = await self.prep.prep.meta(org, s.id)
      out.append({"sheet_id": s.id, "page_no": s.page_no, "title": (s.prep_meta or {}).get("title"), "stats": exts[s.id].stats, "candidates": by.get(s.id, []),
        "schedule": (s.prep_meta or {}).get("schedule"), "notes": exts[s.id].notes or [], "analysis": meta.analysis if meta is not None else None})
    return out

  async def facts_check(self, org: UUID, drawing_id: UUID, payload) -> dict:
    facts = []
    
    for i, f in enumerate(payload.facts):
      try:
        facts.append(KF.normalise(f.model_dump(exclude_none=True)))
      except ValueError as e:
        raise TraceException(f"Fact {i + 1}: {e}", status_code=422, code="FACT_NOT_USABLE")
    read = await self.read_of(org, drawing_id)
    if not read:
      raise TraceException("No sheet of this drawing has been read yet. Read the sheets first, then check them against what you know.", status_code=409, code="NOTHING_READ")
    results = KF.check(read, facts)
    
    t = KF.tally(results)
    return {"drawing_id": drawing_id, "results": [{"index": i, **{k: r[k] for k in ("text", "status", "expected", "found", "message", "pages")}} for i, r in enumerate(results)],
      "passed": t["pass"], "failed": t["fail"], "missing": t["missing"]}

  async def trace(self, org: UUID, drawing_id: UUID) -> dict:
    read = await self.read_of(org, drawing_id)
    sheets = [{"sheet_id": sh["sheet_id"], **TR.sheet_trace(sh["page_no"], sh["notes"], sh["candidates"], sh["analysis"], sh["stats"])} for sh in read]
    return {"drawing_id": drawing_id, "sheets": sheets, "summary": TR.drawing_summary(sheets)}

  async def summary(self, org: UUID, drawing_id: UUID) -> dict:
    return RS.summary(await self.read_of(org, drawing_id))
