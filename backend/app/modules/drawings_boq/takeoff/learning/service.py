from __future__ import annotations
import asyncio
import datetime
import hashlib
from sqlalchemy import select
from app.modules.drawings_boq.takeoff import corrections as CR
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.identity.models import Organization, User
from uuid import UUID, uuid4
from app.modules.drawings_boq.takeoff.ai_reader.models import AiShadowRead, AiExample
from app.modules.drawings_boq.models import TakeoffCorrection
from app.modules.drawings_boq.takeoff.ai_reader import examples as EX
from app.modules.drawings_boq.takeoff.crops import source
from app.modules.drawings_boq.takeoff.learning import pattern as PT, strip as ST

OFF, OWN, SHARED = "OFF", "OWN", "SHARED"
CONSENTS = (OFF, OWN, SHARED)
KIND_OF = {"accept": CR.REVIEW_ACCEPTED, "correct": CR.REVIEW_CORRECTED, "reject": CR.REVIEW_REJECTED}
MEANING = {OFF: "Corrections are kept in the company's own log only; nothing is made into an example and nothing leaves the company.",
  OWN: "Answers the company accepted are kept as examples shown to the model for this company's own drawings only.",
  SHARED: "As OWN, and the examples may be shown for other companies' drawings; corrections leave the company only as patterns with no name, drawing or project, to find rules that hold across companies."}

async def consent_of(session: AsyncSession, org: UUID) -> str:
  got = (await session.execute(select(Organization.learning_consent).where(Organization.id == org))).scalar_one_or_none()
  return got if got in CONSENTS else OFF

async def _name_of(session: AsyncSession, user_id: UUID) -> str:
  u = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
  return (f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email) if u else str(user_id)

async def _drawing_sha(storage_key: str | None, fallback: str) -> str:
  if not storage_key:
    return fallback
  try:
    return hashlib.sha256(await asyncio.to_thread(source.drawing_bytes, storage_key)).hexdigest()
  except Exception:
    return fallback

async def forget_example(session: AsyncSession, org: UUID, key: str) -> int:
  rows = (await session.execute(select(AiExample).where(AiExample.organization_id == org))).scalars().all()
  gone = [r for r in rows if (r.crop_ref or {}).get("key") == key]
  for r in gone:
    await session.delete(r)
  return len(gone)

async def note_review(session: AsyncSession, *, org: UUID, user_id: UUID, project_id: UUID, drawing, row: dict, action: str, stored: str | None, reason: str | None) -> dict:
  key = row["key"]
  
  gone = await forget_example(session, org, key)
  if action == "withdraw":
    return {"logged": False, "example": False, "forgotten": gone}
  
  read = (await session.execute(select(AiShadowRead).where(AiShadowRead.id == UUID(row["read_id"]), AiShadowRead.organization_id == org))).scalar_one_or_none() if row.get("read_id") else None
  task = row.get("task")
  item = PT.item_of(task, key, read.ai_value if read else None)
  subject, what = PT.subject_of(task, item)
  logged = await CR.record(session, org=org, user_id=user_id, project_id=project_id, drawing_id=drawing.id, sheet_id=read.sheet_id if read else None, kind=KIND_OF[action], subject=subject or task,
    before={"read": what, "label": what if task == PT.LEGEND_ENTRY else None}, after={"value": stored}, context={"task": task, "reason": reason, "subject": subject, "key": key})
  consent = await consent_of(session, org)
  made = False
  
  if consent != OFF and action == "accept" and item and task in EX.TASKS:
    sha = await _drawing_sha(getattr(drawing, "storage_key", None), str(drawing.id))
    ex = EX.make(task=task, office=None, kind=PT.kind_of(task, item), crop_ref={"key": key, "page": read.page_no if read else None}, text=PT.quote_of(task, item), answer=item,
      checked_by=await _name_of(session, user_id), date=datetime.date.today().isoformat(), drawing=sha, shared=consent == SHARED)
    session.add(AiExample(id=uuid4(), organization_id=org, task=ex.task, office=ex.office, kind=ex.kind, crop_ref=ex.crop_ref, words=list(ex.words), answer=ex.answer,
      checked_by=ex.checked_by, checked_on=ex.date, drawing=ex.drawing, shared=ex.shared))
    made = True
  return {"logged": logged, "example": made, "forgotten": gone, "consent": consent}

async def export_shared(session: AsyncSession, salt: str) -> list:
  orgs = (await session.execute(select(Organization.id).where(Organization.learning_consent == SHARED))).scalars().all()
  out: list = []
  for org in orgs:
    rows = (await session.execute(select(TakeoffCorrection).where(TakeoffCorrection.organization_id == org, TakeoffCorrection.kind.in_((*ST.REVIEW_KINDS, CR.IDENTITY_SET)))
      .order_by(TakeoffCorrection.created_at))).scalars().all()
    out += ST.records(rows, ST.source_of(org, salt))
  return out
