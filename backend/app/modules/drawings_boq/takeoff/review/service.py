from __future__ import annotations
from app.modules.drawings_boq.takeoff.review import rows as RW
from app.modules.drawings_boq.takeoff.questions.service import QuestionsService
from uuid import UUID
from sqlalchemy import select
from app.modules.drawings_boq.takeoff.ai_reader.models import AiShadowRead
from app.modules.drawings_boq.models import TakeoffCandidate, BOQItem, BOQVersion
from app.modules.drawings_boq import boq_logic as BL
from app.modules.drawings_boq.takeoff.decisions.service import DecisionsService
from app.engine.catalogue import conventions as CV
from app.modules.drawings_boq import company_conventions as CCV
from app.modules.drawings_boq.takeoff.decisions import store
from app.modules.drawings_boq.takeoff.questions import engine as QE
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.decisions.schemas import ChooseDecisionRequest
from app.modules.drawings_boq.takeoff.questions import answers as AN
from app.modules.audit.models import AuditAction

AI_TASKS = (RW.NOTE_TASK, RW.SCHEDULE_TASK, RW.LEGEND_TASK)
WITHDRAW = "withdraw"

class ReviewService(QuestionsService):
  async def _reads(self, org: UUID, project_id: UUID) -> list:
    got = (await self.session.execute(select(AiShadowRead).where(AiShadowRead.organization_id == org, AiShadowRead.project_id == project_id, AiShadowRead.task.in_(AI_TASKS))
      .order_by(AiShadowRead.created_at.desc()))).scalars().all()
    seen, out = set(), []
    for r in got:
      if (r.drawing_id, r.sheet_id, r.task) in seen:
        continue
      seen.add((r.drawing_id, r.sheet_id, r.task))
      out.append({"id": r.id, "task": r.task, "page_no": r.page_no, "status": r.status, "ai_value": r.ai_value, "drawing_id": r.drawing_id})
    return out

  async def _crops(self, org: UUID, project_id: UUID, drawings: list) -> dict:
    place = {}
    
    for n, d in enumerate(drawings):
      for s in await self.repo.sheets(org, d.id):
        place[s.id] = (n, s.page_no)
    got = (await self.session.execute(select(TakeoffCandidate.id, TakeoffCandidate.tag, TakeoffCandidate.sheet_id)
      .where(TakeoffCandidate.organization_id == org, TakeoffCandidate.project_id == project_id, TakeoffCandidate.tag.is_not(None), TakeoffCandidate.decision != "REJECTED")
      .order_by(TakeoffCandidate.created_at, TakeoffCandidate.id))).all()
    out: dict = {}
    for cid, tag, sheet_id in got:
      if sheet_id in place:
        out.setdefault((place[sheet_id][0], place[sheet_id][1], str(tag).upper()), cid)
    return out

  async def _rates(self, org: UUID, project_id: UUID, ledger: list) -> dict:
    ids = sorted({e["element"] for e in ledger})
    if not ids:
      return {}
    
    got = (await self.session.execute(select(BOQItem.work_item_code, BOQItem.unit, BOQItem.unit_rate).join(BOQVersion, BOQVersion.id == BOQItem.boq_version_id)
      .where(BOQItem.organization_id == org, BOQVersion.project_id == project_id, BOQItem.work_item_code.in_(ids), BOQItem.unit_rate.is_not(None))
      .order_by(BOQVersion.created_at.desc()))).all()
    unit_of = {e["element"]: (e.get("quantity") or {}).get("unit") for e in ledger if e.get("quantity")}
    out: dict = {}
    for code, unit, rate in got:
      if code not in out and unit_of.get(code) and BL.normalise_unit(unit) == BL.normalise_unit(unit_of[code]):
        out[code] = float(rate)
    return out

  async def _conflicts(self, org: UUID, drawings: list) -> list:
    out = []
    for d in drawings:
      for c in await DecisionsService(self.session).facts(org, d.id):
        out.append({**c, "drawing_id": d.id})
    return out

  async def _built(self, org: UUID, project_id: UUID) -> dict:
    drawings, snapshot, answers = await self._project(org, project_id)
    on = CV.on_ids(await CCV.in_force(self.session, org))
    empty = snapshot is None
    bare = [] if empty else self._ledger(snapshot, on, None)
    full = [] if empty else self._ledger(snapshot, on, answers)
    rates = await self._rates(org, project_id, bare)
    built = RW.build(ledger=bare, questions=[] if empty else QE.build(bare, answers, on, rates), evidence={"members": []} if empty else snapshot["evidence"], reads=await self._reads(org, project_id),
      answers=answers, review=store.review_merge([d.ingestion_meta for d in drawings]), crops=await self._crops(org, project_id, drawings), rates=rates, facts=await self._conflicts(org, drawings))
    return {**built, "drawings": drawings, "snapshot": snapshot, "answers": answers, "on": on, "full": full, "rates": rates}

  @staticmethod
  def _view(project_id: UUID, built: dict, item: str | None) -> dict:
    rows = [r for r in built["rows"] if item in r["touches"]] if item else built["rows"]
    by_kind: dict = {}
    for r in rows:
      by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    return {"project_id": project_id, "has_ledger": built["snapshot"] is not None, "rows": rows, "open": sum(1 for r in rows if r["state"] == RW.OPEN), "by_kind": by_kind,
      "rates_loaded": bool(built["rates"]), "item": item}

  async def review(self, org: UUID, project_id: UUID, item: str | None = None) -> dict:
    return self._view(project_id, await self._built(org, project_id), item)

  async def act(self, org: UUID, user_id: UUID, project_id: UUID, key: str, action: str, value: str | None, reason: str | None = None) -> dict:
    built = await self._built(org, project_id)
    row = next((r for r in built["rows"] if r["key"] == key), None)
    
    if row is None:
      raise TraceException("This is not a row of the review list of this project.", status_code=404, code="REVIEW_ROW_UNKNOWN")
    drawings, ask = built["drawings"], built["asks"].get(key)
    if action == WITHDRAW:
      stored, why = None, None
    else:
      stored, why = RW.resolve(row, ask, action, value)
    if why:
      raise TraceException(why, status_code=422, code="REVIEW_ACTION_INVALID")
    touched: list = []
    if row["kind"] == RW.AI_CANDIDATE:
      reason, bad = LR.check(action, reason)
      if bad:
        raise TraceException(bad, status_code=422, code="REVIEW_REASON_INVALID")
      home = next((d for d in drawings if str(d.id) == row["drawing_id"]), drawings[0])
      home.ingestion_meta = store.review_put(home.ingestion_meta, key, None if action == WITHDRAW else action, stored, user_id)
      await LS.note_review(self.session, org=org, user_id=user_id, project_id=project_id, drawing=home, row=row, action=action, stored=stored, reason=reason)
    elif key.startswith("fact."):
      if action == WITHDRAW:
        raise TraceException("A figure settled between the sheets is changed by choosing another value.", status_code=422, code="REVIEW_ACTION_INVALID")
      await DecisionsService(self.session).choose(org, user_id, UUID(row["drawing_id"]), ChooseDecisionRequest(decision_id=row["decision_id"], value=stored))
      return {**await self.review(org, project_id), "key": key, "touched": touched}
    else:
      home = next((d for d in drawings if (d.ingestion_meta or {}).get(AN.META_LEDGER)), None) or drawings[0]
      if action == WITHDRAW:
        for d in drawings:
          if key in AN.stored(d.ingestion_meta):
            d.ingestion_meta = AN.clear(d.ingestion_meta, key)
        after = {k: v for k, v in built["answers"].items() if k != key}
      else:
        home.ingestion_meta = AN.put(home.ingestion_meta, key, stored, user_id)
        after = {**built["answers"], key: {"value": stored}}
      touched = RW.changed(built["full"], self._ledger(built["snapshot"], built["on"], after))
      
    await self._log(org, user_id, home.id, AuditAction.UPDATE, f"Review: {action} {key}" + (f" with {stored}" if stored else ""), commit=False)
    await self.session.commit()
    return {**await self.review(org, project_id), "key": key, "touched": touched}
