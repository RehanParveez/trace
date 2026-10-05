from __future__ import annotations
from app.modules.audit.models import AuditEntityType
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4
from sqlalchemy import or_, select
from app.modules.drawings_boq.models import Drawing, DrawingFormat, WorkItem, BuildingSpace, DrawingStatus, SpaceFinish
from app.core.exceptions import TraceException
from app.modules.drawings_boq.schedule_parsing import norm_key

def audit_entity(name: str):
  return getattr(AuditEntityType, name, AuditEntityType.DRAWING)

async def current_ifc_drawing_ids(session: AsyncSession, org: UUID, project_id: UUID) -> list[UUID]:
  r = await session.execute(select(Drawing.id).where(
    Drawing.organization_id == org, Drawing.project_id == project_id, Drawing.format == DrawingFormat.IFC,
    Drawing.status == DrawingStatus.PARSED, Drawing.is_current_revision.is_(True)))
  return sorted((row[0] for row in r.all()), key=str)

async def work_item_catalog(session: AsyncSession, org: UUID, codes=None) -> dict[str, WorkItem]:
  stmt = select(WorkItem).where(WorkItem.is_active.is_(True),
    or_(WorkItem.organization_id == org, WorkItem.organization_id.is_(None)))
  if codes:
    stmt = stmt.where(WorkItem.code.in_(list(codes)))
  out: dict = {}
  for w in sorted((await session.execute(stmt)).scalars().all(), key=lambda w: w.organization_id is not None):
    out[w.code] = w
  return out

async def require_work_item(session: AsyncSession, org: UUID, code: str) -> WorkItem:
  wi = (await work_item_catalog(session, org, [code])).get(code)
  if wi is None:
    raise TraceException(f"Work item '{code}' is not in the catalog.", status_code=422, code="WORK_ITEM_NOT_FOUND")
  return wi

async def carry_over_space_finishes(session: AsyncSession, new_drawing: Drawing) -> dict:
  prev = (await session.execute(
    select(Drawing).where(
      Drawing.organization_id == new_drawing.organization_id,
      Drawing.revision_group_id == new_drawing.revision_group_id,
      Drawing.id != new_drawing.id, Drawing.created_at < new_drawing.created_at)
    .order_by(Drawing.created_at.desc()).limit(1))).scalar_one_or_none()
  if prev is None:
    return {"carried": 0}

  async def _spaces(drawing_id):
    r = await session.execute(select(BuildingSpace).where(
      BuildingSpace.drawing_id == drawing_id, BuildingSpace.source == "IFC", BuildingSpace.is_active.is_(True)))
    return list(r.scalars().all())

  old, new = await _spaces(prev.id), await _spaces(new_drawing.id)
  if not old or not new:
    return {"carried": 0}
  by_gid = {s.ifc_global_id: s.id for s in new if s.ifc_global_id}
  by_name: dict = {}
  
  for s in new:
    by_name.setdefault((norm_key(s.number), norm_key(s.name)), []).append(s.id)
  mapping: dict = {}
  for s in old:
    target = by_gid.get(s.ifc_global_id)
    if target is None:
      options = by_name.get((norm_key(s.number), norm_key(s.name)), [])
      target = options[0] if len(options) == 1 else None
    if target is not None:
      mapping[s.id] = target
  if not mapping:
    return {"carried": 0}

  rows = (await session.execute(select(SpaceFinish).where(
    SpaceFinish.space_id.in_(list(mapping)), SpaceFinish.source.in_(("MANUAL", "SCHEDULE_IMPORT")),
    SpaceFinish.is_active.is_(True)))).scalars().all()
  
  for f in rows:
    session.add(SpaceFinish(
      id=uuid4(), organization_id=f.organization_id, space_id=mapping[f.space_id], surface=f.surface,
      work_item_code=f.work_item_code, finish_name=f.finish_name, height_mm=f.height_mm, source=f.source,
      schedule_row_id=f.schedule_row_id, confidence=f.confidence, review_status=f.review_status,
      is_active=True, extra={**(f.extra or {}), "carried_from": str(f.id)}, created_by_user_id=f.created_by_user_id))
  await session.flush()
  return {"carried": len(rows)}