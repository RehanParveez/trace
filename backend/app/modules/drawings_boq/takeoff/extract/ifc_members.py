from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import select
from app.modules.drawings_boq.models import Drawing, BuildingLevel, DrawingElement, DrawingFormat
from app.modules.drawings_boq.takeoff.model import from_ifc as FI

async def of_project(session: AsyncSession, org: UUID, project_id: UUID) -> tuple:
  ids = list((await session.execute(select(Drawing.id).where(Drawing.organization_id == org, Drawing.project_id == project_id, Drawing.format == DrawingFormat.IFC))).scalars().all())
  if not ids:
    return ()
  levels = {lv.id: lv.name for lv in (await session.execute(select(BuildingLevel).where(BuildingLevel.organization_id == org, BuildingLevel.drawing_id.in_(ids)))).scalars().all()}
  rows = (await session.execute(select(DrawingElement).where(DrawingElement.organization_id == org, DrawingElement.drawing_id.in_(ids), DrawingElement.structural_role.in_(FI.KINDS)))).scalars().all()
  out: tuple = ()
  for did in ids:
    out += FI.from_rows([r for r in rows if r.drawing_id == did], str(did), levels)
  return out
