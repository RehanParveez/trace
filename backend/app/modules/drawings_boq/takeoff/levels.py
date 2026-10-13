from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import select
from app.modules.drawings_boq.models import BuildingLevel
from sqlalchemy.exc import IntegrityError

LEVELS = {
  "FOUNDATION": ("Foundation", -20),
  "BASEMENT": ("Basement", -10),
  "GROUND": ("Ground floor", 0),
  "MEZZANINE": ("Mezzanine", 5),
  "FIRST": ("First floor", 10),
  "SECOND": ("Second floor", 20),
  "THIRD": ("Third floor", 30),
  "FOURTH": ("Fourth floor", 40),
  "TYPICAL": ("Typical floor", 50),
  "ROOF": ("Roof", 100),
}
KEY_PREFIX = "PDF:"

def level_spec(hint: str | None):
  return LEVELS.get(hint or "")

async def ensure_level(session: AsyncSession, org: UUID, drawing_id: UUID, hint: str | None) -> UUID | None:
  spec = level_spec(hint)
  if spec is None:
    return None
  key = KEY_PREFIX + str(hint)

  async def find():
    return (await session.execute(select(BuildingLevel).where(BuildingLevel.organization_id == org, BuildingLevel.drawing_id == drawing_id,
      BuildingLevel.ifc_storey_id == key))).scalar_one_or_none()

  row = await find()
  if row is None:
    try:
      async with session.begin_nested():
        session.add(BuildingLevel(organization_id=org, drawing_id=drawing_id, name=spec[0], ifc_storey_id=key, sequence=spec[1]))
        await session.flush()
    except IntegrityError:
      pass
    row = await find()
  return row.id if row is not None else None