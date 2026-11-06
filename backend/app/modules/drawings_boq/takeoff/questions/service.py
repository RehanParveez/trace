from __future__ import annotations
from app.modules.drawings_boq.takeoff.service import TakeoffService
from uuid import UUID
from app.modules.drawings_boq.takeoff.questions import answers as AN
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.engine.catalogue import loader as CAT
from app.engine.catalogue import conventions as CV
from app.modules.drawings_boq import company_conventions as CCV
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.questions import engine as QE
from app.modules.audit.models import AuditAction

class QuestionsService(TakeoffService):
  async def _project(self, org: UUID, project_id: UUID) -> tuple:
    drawings = await self.repo.project_pdf_drawings(org, project_id)
    held = [d for d in drawings if (d.ingestion_meta or {}).get(AN.META_LEDGER)]
    snapshot = max((d.ingestion_meta[AN.META_LEDGER] for d in held), key=lambda s: str(s.get("at") or ""), default=None)
    return drawings, snapshot, AN.merge([d.ingestion_meta for d in drawings])

  def _ledger(self, snapshot: dict, conventions: list, answers: dict | None) -> list:
    return LG.build(CAT.items(), snapshot["facts"], snapshot["evidence"], conventions, snapshot.get("methods") or {}, answers)

  async def view(self, org: UUID, project_id: UUID) -> dict:
    drawings, snapshot, answers = await self._project(org, project_id)
    
    if snapshot is None:
      return {"project_id": project_id, "has_ledger": False, "questions": [], "open": 0, "by_state": {}}
    on = CV.on_ids(await CCV.in_force(self.session, org))
    questions = QE.build(self._ledger(snapshot, on, None), answers, on)
    by_state: dict = {}
    for q in questions:
      by_state[q["state"]] = by_state.get(q["state"], 0) + 1
    return {"project_id": project_id, "has_ledger": True, "questions": questions, "open": by_state.get(QE.OPEN, 0), "by_state": by_state}

  async def answer(self, org: UUID, user_id: UUID, project_id: UUID, key: str, value: str | None) -> dict:
    view = await self.view(org, project_id)
    
    if not view["has_ledger"]:
      raise TraceException("This project has no ledger yet. Run the first-upload job.", status_code=409, code="NO_LEDGER")
    question = next((q for q in view["questions"] if q["key"] == key), None)
    if question is None or question["state"] == QE.RETIRED:
      raise TraceException("This is not a question asked for this project.", status_code=404, code="QUESTION_UNKNOWN")
    drawings, snapshot, _answers = await self._project(org, project_id)
    home = next((d for d in drawings if (d.ingestion_meta or {}).get(AN.META_LEDGER)), None) or drawings[0]
    
    if value is None:
      for d in drawings:
        if key in AN.stored(d.ingestion_meta):
          d.ingestion_meta = AN.clear(d.ingestion_meta, key)
      message = f"Withdrew the answer to {key}"
    else:
      why = QE.check(question, value)
      if why:
        raise TraceException(why, status_code=422, code="ANSWER_INVALID")
      home.ingestion_meta = AN.put(home.ingestion_meta, key, value, user_id)
      message = f"Answered {key} with {value}"
    await self._log(org, user_id, home.id, AuditAction.UPDATE, message, commit=False)
    await self.session.commit()
    return await self.view(org, project_id)
