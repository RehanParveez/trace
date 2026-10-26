from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.models import Drawing, TakeoffSheet
from app.modules.drawings_boq.takeoff.prep import facts as drawing_facts, printed_params
from app.modules.drawings_boq.takeoff.repository import takeoff_drawing_ids

async def printed_for_drawings(session: AsyncSession, org: UUID, drawing_ids) -> dict:
  ids = sorted(set(drawing_ids), key=str)
  if not ids:
    return printed_params.from_items([])
  sheets = (await session.execute(select(TakeoffSheet).where(TakeoffSheet.organization_id == org, TakeoffSheet.drawing_id.in_(ids))
    .order_by(TakeoffSheet.drawing_id, TakeoffSheet.page_no))).scalars().all()
  read = [{"page_no": s.page_no, "label": s.label, "facts": (s.prep_meta or {}).get("facts")} for s in sheets if (s.prep_meta or {}).get("facts") is not None]
  return printed_params.from_items(drawing_facts.gather(read)["items"])

async def spec_facts_for_project(session: AsyncSession, org: UUID, project_id: UUID) -> dict:
  """What the notes of the project's current drawings print that a finished bill should show: the pages that print a waterproofing coat."""
  ids = await takeoff_drawing_ids(session, org, project_id)
  if not ids:
    return {"waterproof_pages": []}
    
  current = (await session.execute(select(Drawing.id).where(Drawing.organization_id == org, Drawing.id.in_(ids), Drawing.is_current_revision.is_(True)))).scalars().all()
  sheets = (await session.execute(select(TakeoffSheet).where(TakeoffSheet.organization_id == org, TakeoffSheet.drawing_id.in_(current))
    .order_by(TakeoffSheet.drawing_id, TakeoffSheet.page_no))).scalars().all()
  read = [{"page_no": s.page_no, "label": s.label, "facts": (s.prep_meta or {}).get("facts")} for s in sheets if (s.prep_meta or {}).get("facts") is not None]
  items = drawing_facts.gather(read)["items"]
  pages = sorted({p for it in items if it.get("kind") == "WATERPROOF_LAYER" and it.get("material") == "waterproofing coat" for p in it.get("pages") or []})
  return {"waterproof_pages": pages}

async def printed_for_project(session: AsyncSession, org: UUID, project_id: UUID) -> dict:
  ids = await takeoff_drawing_ids(session, org, project_id)
  if not ids:
    return printed_params.from_items([])
  current = (await session.execute(select(Drawing.id).where(Drawing.organization_id == org, Drawing.id.in_(ids), Drawing.is_current_revision.is_(True)))).scalars().all()
  return await printed_for_drawings(session, org, current)
