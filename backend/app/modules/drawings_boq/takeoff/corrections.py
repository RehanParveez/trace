from __future__ import annotations
import json
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.models import TakeoffCorrection
from sqlalchemy import func, select

log = logging.getLogger(__name__)

ITEM_REJECTED, ITEM_RESTORED, ITEM_VALUE_TYPED = "ITEM_REJECTED", "ITEM_RESTORED", "ITEM_VALUE_TYPED"
CONFLICT_RESOLVED, BULK_APPROVE, IDENTITY_SET, SCALE_SET, LAYOUT_CHOICE = "CONFLICT_RESOLVED", "BULK_APPROVE", "IDENTITY_SET", "SCALE_SET", "LAYOUT_CHOICE"
MARK_CHOICE = "MARK_CHOICE"
KINDS = (ITEM_REJECTED, ITEM_RESTORED, ITEM_VALUE_TYPED, CONFLICT_RESOLVED, BULK_APPROVE, IDENTITY_SET, SCALE_SET, LAYOUT_CHOICE, MARK_CHOICE)
MAX_JSON_CHARS = 4000

def _plain(value) -> dict:
  """A JSON object no larger than MAX_JSON_CHARS (a larger one is replaced by a note saying so)."""
  try:
    text = json.dumps(value if value is not None else {}, default=str, sort_keys=True)
    if len(text) <= MAX_JSON_CHARS:
      plain = json.loads(text)
      return plain if isinstance(plain, dict) else {"value": plain}
  except (TypeError, ValueError):
    pass
  return {"cut": True}

def snapshot(row) -> dict:
  return {"category": row.category, "tag": row.tag, "label": row.label, "count": row.count, "status": row.status, "source": row.source,
    "work_item": row.suggested_work_item, "confidence": float(row.confidence) if row.confidence is not None else None}

async def record(session: AsyncSession, *, org: UUID, user_id: UUID | None, project_id: UUID, kind: str, drawing_id: UUID | None = None, sheet_id: UUID | None = None,
  subject: str | None = None, before=None, after=None, context=None, extract_version: int | None = None) -> bool:
  if kind not in KINDS:
    log.warning("corrections: unknown kind %s", kind)
    return False
  try:
    async with session.begin_nested():
      session.add(TakeoffCorrection(organization_id=org, project_id=project_id, drawing_id=drawing_id, sheet_id=sheet_id, user_id=user_id, kind=kind,
        subject=(subject or None) and str(subject)[:120], before=_plain(before), after=_plain(after), context=_plain(context), extract_version=extract_version))
    return True
  except Exception:
    log.warning("corrections: could not write a %s line", kind, exc_info=True)
    return False

async def record_committed(session: AsyncSession, **kw) -> bool:
  if not await record(session, **kw):
    return False
  try:
    await session.commit()
    return True
  except Exception:
    log.warning("corrections: could not commit a line", exc_info=True)
    try:
      await session.rollback()
    except Exception:
      pass
    return False

async def project_corrections(session: AsyncSession, org: UUID, project_id: UUID, limit: int = 200) -> dict:
  limit = max(1, min(int(limit), 500))
  base = (TakeoffCorrection.organization_id == org, TakeoffCorrection.project_id == project_id)
  counts = dict((await session.execute(select(TakeoffCorrection.kind, func.count()).where(*base).group_by(TakeoffCorrection.kind))).all())
  rows = (await session.execute(select(TakeoffCorrection).where(*base).order_by(TakeoffCorrection.created_at.desc()).limit(limit))).scalars().all()
  return {"counts": {k: int(v) for k, v in counts.items()}, "rows": [{"id": r.id, "kind": r.kind, "subject": r.subject, "drawing_id": r.drawing_id, "sheet_id": r.sheet_id,
    "user_id": r.user_id, "before": r.before or {}, "after": r.after or {}, "context": r.context or {}, "created_at": r.created_at} for r in rows]}
