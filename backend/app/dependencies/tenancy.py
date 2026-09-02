from __future__ import annotations
from contextvars import ContextVar
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_current_organization_id: ContextVar[
  UUID | None
] = ContextVar(
  "current_organization_id",
  default=None,
)

def set_current_organization_id(
  organization_id: UUID,
) -> None:
  _current_organization_id.set(
    organization_id
  )

def get_current_organization_id() -> UUID:
  organization_id = _current_organization_id.get()

  if organization_id is None:
    raise RuntimeError(
      "Organization context has not been initialized."
    )

  return organization_id

def clear_current_organization_id() -> None:
  _current_organization_id.set(None)
  
async def scope_session_to_org(
  session: AsyncSession,
  organization_id: UUID,
) -> None:
  await session.execute(
    text("SELECT set_config('app.current_org_id', :org_id, true)"),
    {"org_id": str(organization_id)},
  )
  set_current_organization_id(organization_id)
  

async def scope_session_as_platform_admin(session: AsyncSession) -> None:
  await session.execute(
    text("SELECT set_config('app.is_platform_admin', 'true', true)")
  )