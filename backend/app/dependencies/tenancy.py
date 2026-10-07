from __future__ import annotations
from contextvars import ContextVar
from uuid import UUID
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

_platform_admin: ContextVar[bool] = ContextVar("platform_admin", default=False)

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
  set_current_organization_id(organization_id)
  _platform_admin.set(False)
  await session.execute(
    text("SELECT set_config('app.current_org_id', :org_id, true), set_config('app.is_platform_admin', 'false', true)"),
    {"org_id": str(organization_id)},
  )

async def scope_session_as_platform_admin(session: AsyncSession) -> None:
  _platform_admin.set(True)
  await session.execute(
    text("SELECT set_config('app.is_platform_admin', 'true', true)")
  )

@event.listens_for(Session, "after_begin")
def _reapply_tenant_settings(session, transaction, connection) -> None:
  """set_config(..., true) only lasts until COMMIT. Re-apply the tenant (and platform-admin flag) at the start of every
  transaction, so RLS keeps working after the first commit of a request or worker task."""
  org = _current_organization_id.get()
  admin = _platform_admin.get()
  if org is None and not admin:
    return
  connection.execute(
    text("SELECT set_config('app.current_org_id', :org_id, true), set_config('app.is_platform_admin', :admin, true)"),
    {"org_id": str(org) if org is not None else "", "admin": "true" if admin else "false"},
  )