from __future__ import annotations
import hashlib
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.rebar.bbs_match_service import BbsMatchService
from app.modules.drawings_boq.rebar.bbs_service import BbsService
from app.modules.audit.service import AuditLogService
from app.modules.drawings_boq.finish_schedule.common import audit_entity
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.rebar.bbs_match_models import RebarBbsDecision
from app.modules.drawings_boq.takeoff.extract.extract_repository import ExtractRepository
from app.modules.drawings_boq.takeoff.repository import TakeoffRepository
from app.modules.drawings_boq.rebar.bbs_expect_models import RebarBbsExpectRun, RebarBbsExpectation
from uuid import UUID, uuid4
from sqlalchemy import func, select
from app.core.exceptions import TraceException
from app.engine.measure import rebar_expect as RX
from app.modules.drawings_boq.rebar import bbs_expect_decisions as XD
from app.modules.drawings_boq.rebar import expect_source as ES
from app.modules.drawings_boq.rebar.member_source import candidate_dict

PAGE_SIZE_MAX = 500

def digest_of(decisions: dict) -> str:
  return hashlib.sha256(json.dumps(decisions, sort_keys=True, default=str).encode()).hexdigest()

def _number(v):
  return None if v is None else float(v)

class BbsExpectService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.bbs = BbsService(session)
    self.match = BbsMatchService(session)
    self.audit_log = AuditLogService(session)

  async def _log(self, org, user_id, entity_id, message) -> None:
    await self.audit_log.log(org, user_id, audit_entity("SCHEDULE_IMPORT"), entity_id, AuditAction.UPDATE, message)

  async def expect_decisions(self, org: UUID, project_id: UUID) -> dict:
    stored = await self.match.decisions(org, project_id)
    return {k: v for k, v in stored.items() if k in XD.EXPECT_KEYS}

  async def set_decision(self, org: UUID, project_id: UUID, user_id: UUID, key: str, value) -> dict:
    await self.bbs._require_project(org, project_id)
    if key not in XD.EXPECT_KEYS:
      raise TraceException(f"{key} is not a decision of the expected quantities.", status_code=422, code="BBS_DECISION_INVALID")
    if value is None:
      row = (await self.session.execute(select(RebarBbsDecision).where(RebarBbsDecision.organization_id == org, RebarBbsDecision.project_id == project_id,
        RebarBbsDecision.key == key))).scalar_one_or_none()
      if row is not None:
        await self.session.delete(row)
        await self.session.flush()
    else:
      await self.match._put(org, project_id, user_id, key, value)
    await self.session.commit()
    await self._log(org, user_id, project_id, f"{'Set' if value is not None else 'Cleared'} the decision {key} of the bar schedule audit")
    return {"decisions": await self.match.decisions(org, project_id)}

  async def _read(self, org: UUID, project_id: UUID) -> tuple:
    takeoff, extract = TakeoffRepository(self.session), ExtractRepository(self.session)
    sheets: list = []
    cands: dict = {}
    for drawing in await takeoff.project_pdf_drawings(org, project_id):
      rows = await takeoff.sheets(org, drawing.id)
      page_of = {s.id: s.page_no for s in rows}
      key = str(drawing.id)
      sheets.extend({"pdf_key": key, "page_no": s.page_no, "meta": s.prep_meta or {}} for s in rows)
      for c in await extract.candidates(org, list(page_of)):
        cands.setdefault((key, page_of[c.sheet_id]), []).append(candidate_dict(c))
    return sheets, cands

  @staticmethod
  def _run_out(run: RebarBbsExpectRun) -> dict:
    return {"id": run.id, "document_id": run.document_id, "decisions": run.decisions, "decisions_digest": run.decisions_digest, "member_count": run.member_count,
      "complete_count": run.complete_count, "stats": run.stats, "created_at": run.created_at}

  async def run(self, org: UUID, document_id: UUID, user_id: UUID) -> dict:
    doc = await self.bbs._document(org, document_id)
    project_id, version_no = doc.project_id, doc.version
    parsed, _names = await self.bbs._load_parsed(org, doc)
    decisions = await self.expect_decisions(org, project_id)
    sheets, cands = await self._read(org, project_id)
    jobs = ES.build_jobs(sheets, cands, decisions)
    
    if not jobs:
      raise TraceException("No structural drawing of this project has been read yet, so there is nothing to work out. Upload and prepare the structural drawings first.",
        status_code=409, code="NO_DRAWING_MEMBERS")
    results = ES.run_jobs(jobs)
    expected = [e for _, e in results]
    shares = RX.input_shares(expected)
    by_class: dict = {}
    
    for e in expected:
      slot = by_class.setdefault(e.cls, {"members": 0, "complete": 0, "kg": 0.0})
      slot["members"] += 1
      slot["complete"] += 1 if e.complete else 0
      slot["kg"] = round(slot["kg"] + (float(e.kg) if e.kg is not None else 0.0), 2)
    complete = sum(1 for e in expected if e.complete)
    stats = {"shares": shares, "by_class": by_class, "complete_kg": round(sum(float(e.kg) for e in expected if e.complete and e.kg is not None), 2)}
    run = RebarBbsExpectRun(id=uuid4(), organization_id=org, document_id=document_id, decisions=decisions, decisions_digest=digest_of(decisions), member_count=len(expected),
      complete_count=complete, stats=stats, created_by_user_id=user_id)
    self.session.add(run)
    await self.session.flush()
    run_id = run.id
    for job, e in results:
      d = e.as_dict()
      self.session.add(RebarBbsExpectation(id=uuid4(), organization_id=org, run_id=run_id, document_id=document_id, member_class=e.cls, mark=e.mark[:60], floor=e.floor,
        count=e.count, total_ft=e.total_ft, kg=e.kg, complete=e.complete, plan_count=job.get("plan_count"), source_page=job.get("page"), decision_only=bool(job.get("decision_only")),
        lines=d["lines"], inputs=d["inputs"], blocked=d["blocked"], notes=d["notes"]))
      
    await self.session.commit()
    await self._log(org, user_id, document_id, f"Worked out the expected bar quantities for bar bending schedule version {version_no}: {complete} of {len(expected)} members complete")
    return self._run_out((await self.session.execute(select(RebarBbsExpectRun).where(RebarBbsExpectRun.id == run_id))).scalar_one())

  async def latest(self, org: UUID, document_id: UUID) -> RebarBbsExpectRun | None:
    await self.bbs._document(org, document_id)
    return (await self.session.execute(select(RebarBbsExpectRun).where(RebarBbsExpectRun.document_id == document_id, RebarBbsExpectRun.organization_id == org)
      .order_by(RebarBbsExpectRun.created_at.desc()).limit(1))).scalar_one_or_none()

  async def latest_out(self, org: UUID, document_id: UUID) -> dict | None:
    run = await self.latest(org, document_id)
    return self._run_out(run) if run is not None else None

  async def items(self, org: UUID, document_id: UUID, member_class: str | None, complete: bool | None, page: int, page_size: int) -> dict:
    run = await self.latest(org, document_id)
    if run is None:
      return {"run_id": None, "total": 0, "page": page, "page_size": page_size, "items": [], "counts_by_class": {}}
    base = [RebarBbsExpectation.run_id == run.id, RebarBbsExpectation.organization_id == org]
    stmt = select(RebarBbsExpectation).where(*base)
    
    if member_class:
      stmt = stmt.where(RebarBbsExpectation.member_class == member_class)
    if complete is not None:
      stmt = stmt.where(RebarBbsExpectation.complete == complete)
    total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    size = min(page_size, PAGE_SIZE_MAX)
    rows = list((await self.session.execute(stmt.order_by(RebarBbsExpectation.member_class, RebarBbsExpectation.mark, RebarBbsExpectation.floor, RebarBbsExpectation.id)
      .offset((page - 1) * size).limit(size))).scalars().all())
    counts = dict((await self.session.execute(select(RebarBbsExpectation.member_class, func.count()).where(*base).group_by(RebarBbsExpectation.member_class))).all())
    items = [{"id": r.id, "member_class": r.member_class, "mark": r.mark, "floor": r.floor, "count": _number(r.count), "total_ft": _number(r.total_ft), "kg": _number(r.kg),
      "complete": r.complete, "plan_count": r.plan_count, "source_page": r.source_page, "decision_only": r.decision_only, "lines": r.lines, "inputs": r.inputs,
      "blocked": r.blocked, "notes": r.notes} for r in rows]
    return {"run_id": run.id, "total": int(total), "page": page, "page_size": size, "items": items, "counts_by_class": {k: int(v) for k, v in counts.items()}}
