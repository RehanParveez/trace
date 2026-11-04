from __future__ import annotations
import hashlib
import json
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.rebar.bbs_service import BbsService, _finding_key, _json_safe
from app.modules.drawings_boq.rebar.bbs_expect_service import BbsExpectService
from app.modules.drawings_boq.rebar.bbs_match_service import BbsMatchService
from app.modules.audit.service import AuditLogService
from app.core.exceptions import TraceException
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.finish_schedule.common import audit_entity
from app.modules.drawings_boq.rebar import bbs_audit as audit
from app.modules.drawings_boq.rebar import bbs_crosscheck as XC
from app.modules.drawings_boq.rebar import bbs_expect_decisions as XD
from app.modules.drawings_boq.rebar import expect_source as ES
from app.modules.drawings_boq.rebar import member_match as MM
from app.modules.drawings_boq.rebar import member_source as MS
from app.modules.drawings_boq.rebar.bbs_models import RebarAuditFinding, RebarAuditRun, RebarBbsDocument

KEY_MAX = 600

def decisions_digest(decisions: dict) -> str:
  audited = {k: v for k, v in decisions.items() if k != "steel_source"}
  return hashlib.sha256(json.dumps(audited, sort_keys=True, default=str).encode()).hexdigest()

def cross_key(f, taken: set) -> str:
  key = _finding_key(f)
  if isinstance(f, XC.XFinding):
    key = f"{key}|{f.rule[:80]}"
  key = key[:KEY_MAX]
  base, n = key, 1
  while key in taken:
    n += 1
    key = f"{base[:KEY_MAX - 6]}#{n}"
  taken.add(key)
  return key

class BbsCrossCheckService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.bbs = BbsService(session)
    self.match = BbsMatchService(session)
    self.expect = BbsExpectService(session)
    self.audit_log = AuditLogService(session)

  async def _log(self, org, user_id, entity_id, message) -> None:
    await self.audit_log.log(org, user_id, audit_entity("SCHEDULE_IMPORT"), entity_id, AuditAction.CREATE, message)

  async def _previous(self, org: UUID, doc: RebarBbsDocument):
    if doc.version <= 1:
      return None
    return (await self.session.execute(select(RebarBbsDocument).where(RebarBbsDocument.project_id == doc.project_id, RebarBbsDocument.organization_id == org,
      RebarBbsDocument.version == doc.version - 1))).scalar_one_or_none()

  async def run(self, org: UUID, document_id: UUID, user_id: UUID) -> RebarAuditRun:
    doc = await self.bbs._document(org, document_id)
    project_id, version_no = doc.project_id, doc.version
    parsed, names = await self.bbs._load_parsed(org, doc)
    decisions = await self.match.decisions(org, project_id)
    expect_decisions = {k: v for k, v in decisions.items() if k in XD.EXPECT_KEYS}
    sheets, cands = await self.expect._read(org, project_id)
    jobs = ES.build_jobs(sheets, cands, expect_decisions, [s.name for s in parsed.sheets])
    if not jobs:
      raise TraceException("No structural drawing of this project has been read yet, so there is nothing to check the bar schedule against. Upload and prepare the structural drawings first.",
        status_code=409, code="NO_DRAWING_MEMBERS")
      
    results = ES.run_jobs(jobs)
    members = MS.collapse(MS.members_from_sheets(sheets, cands))
    for job, _e in results:
      if job.get("decision_only") and job["cls"] != "SLAB":
        members.append(MS.DrawingMember("", 0, job["cls"], job["mark"], job["floor"], 1, "DECISION"))
        
    matched = MM.match_rows(parsed.rows, names, members, decisions)
    cross_bands = XC.load_cross_bands()
    cross = XC.crosscheck(parsed.rows, names, matched, results, members, expect_decisions, cross_bands, XC.drawing_refs(sheets), XC.size_conflicts(sheets, parsed.rows, matched, names))
    l1_bands = audit.load_bands()
    shapes, rule = await self.bbs._shapes_and_rules(org)
    l1 = audit.run_l1(parsed, l1_bands, shapes, rule)
    findings = list(l1.findings) + list(cross.findings)
    previous = await self._previous(org, doc)
    
    diff: dict = {}
    if previous is not None:
      old_parsed, old_names = await self.bbs._load_parsed(org, previous)
      diff = audit.diff_rows(old_parsed.rows, old_names, parsed.rows, names)
      diff["from_version"], diff["to_version"] = previous.version, doc.version
    before = (await self.session.execute(select(RebarAuditRun.id).where(RebarAuditRun.document_id == document_id, RebarAuditRun.organization_id == org)
      .order_by(RebarAuditRun.created_at.desc()).limit(1))).scalar_one_or_none()
    
    carried: dict = {}
    if before is not None:
      for f in (await self.session.execute(select(RebarAuditFinding).where(RebarAuditFinding.run_id == before, RebarAuditFinding.organization_id == org,
        RebarAuditFinding.status != "OPEN"))).scalars().all():
        carried[f.finding_key] = f
    totals = _json_safe(dict(l1.totals))
    totals["by_code"] = _count(findings, "code")
    totals["by_class"] = _count(findings, "finding_class")
    totals["crosscheck"] = _json_safe(cross.totals)
    totals["row_expect"] = {str(i): v for i, v in cross.row_expect.items()}
    run = RebarAuditRun(id=uuid4(), organization_id=org, document_id=document_id, level="L4",
      engine_digest=hashlib.sha256(f"{audit.AUDIT_VERSION}|{XC.CROSSCHECK_VERSION}|{parsed.profile}".encode()).hexdigest(),
      rules_digest=hashlib.sha256(f"{l1_bands.digest}|{cross_bands.digest}".encode()).hexdigest(), decisions_digest=decisions_digest(decisions),
      previous_document_id=previous.id if previous else None, totals=totals, diff=diff, created_by_user_id=user_id)
    self.session.add(run)
    await self.session.flush()
    run_id, finding_count = run.id, len(findings)
    taken: set = set()
    for f in findings:
      key = cross_key(f, taken)
      
      row = RebarAuditFinding(id=uuid4(), organization_id=org, run_id=run_id, document_id=document_id, code=f.code, finding_class=f.finding_class, rule=f.rule[:300],
        finding_key=key, bbs_ref=_json_safe(f.bbs_ref), drawing_ref=_json_safe(getattr(f, "drawing_ref", None)), bbs_value=f.bbs_value, trace_value=f.trace_value,
        diff_kg=f.diff_kg, diff_pct=f.diff_pct, confidence=f.confidence, question=f.question, effect_basis=getattr(f, "effect_basis", None),
        convention=_json_safe(getattr(f, "convention", None)))
      old = carried.get(key)
      if old is not None:
        row.status, row.reason, row.decided_by_user_id, row.decided_at = old.status, old.reason, old.decided_by_user_id, old.decided_at
      self.session.add(row)
    await self.session.commit()
    await self._log(org, user_id, document_id, f"Cross-checked bar bending schedule version {version_no} against the drawings: {finding_count} finding(s)")
    return (await self.session.execute(select(RebarAuditRun).where(RebarAuditRun.id == run_id))).scalar_one()

def _count(findings: list, attr: str) -> dict:
  out: dict = {}
  for f in findings:
    out[getattr(f, attr)] = out.get(getattr(f, attr), 0) + 1
  return out
