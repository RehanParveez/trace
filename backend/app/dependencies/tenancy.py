from __future__ import annotations
from contextvars import ContextVar
from uuid import UUID
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
    "SELECT set_config('app.current_org_id', $1, FALSE)",
    [str(organization_id)],
    execution_options={"isolation_level": "READ COMMITTED"},
  )