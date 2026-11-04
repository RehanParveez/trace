from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.audit.service import AuditLogService
from app.modules.drawings_boq.finish_schedule.common import audit_entity
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.rebar.bbs_service import BbsService
from sqlalchemy import func, select
from uuid import UUID, uuid4
from app.modules.drawings_boq.takeoff.repository import TakeoffRepository
from app.modules.drawings_boq.takeoff.extract.extract_repository import ExtractRepository
from app.modules.drawings_boq.rebar.bbs_match_models import RebarBbsDecision, RebarBbsMatch, RebarBbsMatchRun
from app.core.exceptions import TraceException
from app.modules.drawings_boq.rebar.bbs_models import RebarBbsRow
from app.modules.drawings_boq.rebar import bbs_decisions as DEC
from app.modules.drawings_boq.rebar import member_match as MM
from app.modules.drawings_boq.rebar import member_source as MS

PAGE_SIZE_MAX = 500
KINDS = ("MATCH", "ASK", "EXTRA", "MISSING")

def _now():
  return datetime.now(timezone.utc)

def _json_safe(value):
  if isinstance(value, dict):
    return {str(k): _json_safe(v) for k, v in value.items()}
  if isinstance(value, (list, tuple, set)):
    return [_json_safe(v) for v in value]
  return value

class BbsMatchService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.bbs = BbsService(session)
    self.audit_log = AuditLogService(session)

  async def _log(self, org, user_id, entity_id, message) -> None:
    await self.audit_log.log(org, user_id, audit_entity("SCHEDULE_IMPORT"), entity_id, AuditAction.UPDATE, message)

  async def decisions(self, org: UUID, project_id: UUID) -> dict:
    rows = (await self.session.execute(select(RebarBbsDecision).where(RebarBbsDecision.organization_id == org, RebarBbsDecision.project_id == project_id))).scalars().all()
    return {r.key: r.value for r in rows}

  async def project_decisions(self, org: UUID, project_id: UUID) -> dict:
    await self.bbs._require_project(org, project_id)
    return {"decisions": await self.decisions(org, project_id)}

  async def _put(self, org: UUID, project_id: UUID, user_id: UUID, key: str, value) -> None:
    try:
      value = DEC.clean(key, value)
    except ValueError as exc:
      raise TraceException(str(exc), status_code=422, code="BBS_DECISION_INVALID")
    row = (await self.session.execute(select(RebarBbsDecision).where(RebarBbsDecision.organization_id == org, RebarBbsDecision.project_id == project_id,
      RebarBbsDecision.key == key))).scalar_one_or_none()
    if row is None:
      self.session.add(RebarBbsDecision(id=uuid4(), organization_id=org, project_id=project_id, key=key, value=value, decided_by_user_id=user_id, decided_at=_now()))
    else:
      row.value, row.decided_by_user_id, row.decided_at = value, user_id, _now()
    await self.session.flush()

  async def set_floor_map(self, org: UUID, project_id: UUID, user_id: UUID, value: dict) -> dict:
    await self.bbs._require_project(org, project_id)
    await self._put(org, project_id, user_id, "bbs_floor_map", value)
    await self.session.commit()
    await self._log(org, user_id, project_id, "Confirmed the floor map of the bar bending schedule")
    return {"decisions": await self.decisions(org, project_id)}

  async def load_members(self, org: UUID, project_id: UUID) -> list:
    takeoff, extract = TakeoffRepository(self.session), ExtractRepository(self.session)
    sheets: list = []
    cands: dict = {}
    
    for drawing in await takeoff.project_pdf_drawings(org, project_id):
      rows = await takeoff.sheets(org, drawing.id)
      page_of = {s.id: s.page_no for s in rows}
      key = str(drawing.id)
      sheets.extend({"pdf_key": key, "page_no": s.page_no, "meta": s.prep_meta or {}} for s in rows)
      for c in await extract.candidates(org, list(page_of)):
        cands.setdefault((key, page_of[c.sheet_id]), []).append(MS.candidate_dict(c))
    return MS.collapse(MS.members_from_sheets(sheets, cands))

  def _run_out(self, run: RebarBbsMatchRun) -> dict:
    return {"id": run.id, "document_id": run.document_id, "floor_map": run.floor_map, "floor_map_proposed": run.floor_map_proposed, "floor_map_confirmed": run.floor_map_confirmed,
      "member_count": run.member_count, "stats": run.stats, "created_at": run.created_at}

  async def run(self, org: UUID, document_id: UUID, user_id: UUID) -> dict:
    doc = await self.bbs._document(org, document_id)
    project_id, version_no = doc.project_id, doc.version
    parsed, names = await self.bbs._load_parsed(org, doc)
    row_ids = list((await self.session.execute(select(RebarBbsRow.id).where(RebarBbsRow.document_id == document_id, RebarBbsRow.organization_id == org)
      .order_by(RebarBbsRow.row_no))).scalars().all())
    members = await self.load_members(org, project_id)
    
    if not members:
      raise TraceException("No structural drawing of this project has been read yet, so there is nothing to match the bar schedule to. Upload and prepare the structural drawings first.",
        status_code=409, code="NO_DRAWING_MEMBERS")
    result = MM.match_rows(parsed.rows, names, members, await self.decisions(org, project_id))
    run = RebarBbsMatchRun(id=uuid4(), organization_id=org, document_id=document_id, floor_map=_json_safe(result.floor_map), floor_map_proposed=_json_safe(result.floor_map_proposed),
      floor_map_confirmed=result.floor_map_confirmed, member_count=len(members), stats=_json_safe(result.stats), created_by_user_id=user_id)
    self.session.add(run)
    
    await self.session.flush()
    run_id, share = run.id, result.stats["share_without_asking"]
    for it in result.items:
      r = parsed.rows[it.row_index]
      self.session.add(RebarBbsMatch(id=uuid4(), organization_id=org, run_id=run_id, document_id=document_id, row_id=row_ids[it.row_index], kind=it.kind, family=it.family,
        sheet_name=names.get(r.sheet), member=r.member, floors=list(it.floors), method=it.method, confidence=it.confidence, basis=it.basis, reason=it.reason, elements=_json_safe(it.elements)))
      
    for m in result.missing:
      self.session.add(RebarBbsMatch(id=uuid4(), organization_id=org, run_id=run_id, document_id=document_id, row_id=None, kind="MISSING", family=m["class"], sheet_name=None,
        member=m["mark"], floors=[m["floor"]] if m["floor"] else [], method=None, confidence=0, basis=None, reason=m["reason"], elements=[_json_safe(m)]))
    await self.session.commit()
    await self._log(org, user_id, document_id, f"Matched bar bending schedule version {version_no} to the drawings: {round(share * 100, 1)}% without asking")
    return self._run_out((await self.session.execute(select(RebarBbsMatchRun).where(RebarBbsMatchRun.id == run_id))).scalar_one())

  async def latest(self, org: UUID, document_id: UUID) -> RebarBbsMatchRun | None:
    await self.bbs._document(org, document_id)
    return (await self.session.execute(select(RebarBbsMatchRun).where(RebarBbsMatchRun.document_id == document_id, RebarBbsMatchRun.organization_id == org)
      .order_by(RebarBbsMatchRun.created_at.desc()).limit(1))).scalar_one_or_none()

  async def latest_out(self, org: UUID, document_id: UUID) -> dict | None:
    run = await self.latest(org, document_id)
    return self._run_out(run) if run is not None else None

  async def items(self, org: UUID, document_id: UUID, kind: str | None, family: str | None, page: int, page_size: int) -> dict:
    run = await self.latest(org, document_id)
    
    if run is None:
      return {"run_id": None, "total": 0, "page": page, "page_size": page_size, "items": [], "asks": [], "counts_by_kind": {}}
    base = [RebarBbsMatch.run_id == run.id, RebarBbsMatch.organization_id == org]
    stmt = select(RebarBbsMatch).where(*base)
    if kind:
      stmt = stmt.where(RebarBbsMatch.kind == kind)
    if family:
      stmt = stmt.where(RebarBbsMatch.family == family)
      
    total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    size = min(page_size, PAGE_SIZE_MAX)
    items = list((await self.session.execute(stmt.order_by(RebarBbsMatch.sheet_name, RebarBbsMatch.member, RebarBbsMatch.id).offset((page - 1) * size).limit(size))).scalars().all())
    counts = dict((await self.session.execute(select(RebarBbsMatch.kind, func.count()).where(*base).group_by(RebarBbsMatch.kind))).all())
    ask_rows = (await self.session.execute(select(RebarBbsMatch.sheet_name, RebarBbsMatch.member, RebarBbsMatch.family, RebarBbsMatch.reason, func.count()).where(*base, RebarBbsMatch.kind == "ASK")
      .group_by(RebarBbsMatch.sheet_name, RebarBbsMatch.member, RebarBbsMatch.family, RebarBbsMatch.reason).order_by(RebarBbsMatch.sheet_name, RebarBbsMatch.member))).all()
    asks = [{"group": f"{s}|{m}", "sheet": s, "member": m, "family": f, "rows": int(n), "reason": r} for s, m, f, r, n in ask_rows]
    return {"run_id": run.id, "total": int(total), "page": page, "page_size": size, "items": [self._item_out(i) for i in items], "asks": asks,
      "counts_by_kind": {k: int(counts.get(k, 0)) for k in KINDS}}

  @staticmethod
  def _item_out(i: RebarBbsMatch) -> dict:
    return {"id": i.id, "row_id": i.row_id, "kind": i.kind, "family": i.family, "sheet_name": i.sheet_name, "member": i.member, "floors": i.floors, "method": i.method,
      "confidence": float(i.confidence or 0), "basis": i.basis, "reason": i.reason, "elements": i.elements}

  async def confirm(self, org: UUID, document_id: UUID, user_id: UUID, group: str, elements: list, note: str | None) -> dict:
    doc = await self.bbs._document(org, document_id)
    project_id = doc.project_id
    current = dict((await self.decisions(org, project_id)).get("bbs_member_map") or {})
    current[group] = {"elements": elements, "note": note or "", "by": str(user_id)}
    await self._put(org, project_id, user_id, "bbs_member_map", current)
    
    await self.session.commit()
    await self._log(org, user_id, document_id, f"Confirmed the match of {group}")
    return await self.run(org, document_id, user_id)

  async def forget(self, org: UUID, document_id: UUID, user_id: UUID, group: str) -> dict:
    doc = await self.bbs._document(org, document_id)
    project_id = doc.project_id
    current = dict((await self.decisions(org, project_id)).get("bbs_member_map") or {})
    
    if group not in current:
      raise TraceException("That match was not confirmed.", status_code=404, code="BBS_MATCH_NOT_CONFIRMED")
    current.pop(group)
    await self._put(org, project_id, user_id, "bbs_member_map", current)
    await self.session.commit()
    await self._log(org, user_id, document_id, f"Withdrew the confirmed match of {group}")
    return await self.run(org, document_id, user_id)
