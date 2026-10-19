from __future__ import annotations
from contextvars import ContextVar
from uuid import UUID
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.core.crypto import keyring

_platform_admin: ContextVar[bool] = ContextVar("platform_admin", default=False)
_service_scope: ContextVar[str | None] = ContextVar("service_scope", default=None)
_system_scope: ContextVar[bool] = ContextVar("system_scope", default=False)
_support_org_id: ContextVar[UUID | None] = ContextVar("support_org_id", default=None)

_APPLY_SCOPE_SQL = text(
  "SELECT set_config('app.current_org_id', :org_id, true), set_config('app.is_platform_admin', :admin, true), "
  "set_config('app.service_scope', :service, true), set_config('app.system_maintenance', :system, true), "
  "set_config('app.support_org_id', :support, true)"
)

def _scope_params() -> dict | None:
  org, service, support = _current_organization_id.get(), _service_scope.get(), _support_org_id.get()
  admin, system = _platform_admin.get(), _system_scope.get()
  if org is None and service is None and support is None and not admin and not system:
    return None
  
  return {
    "org_id": str(org) if org is not None else "",
    "admin": "true" if admin else "false",
    "service": service or "",
    "system": "true" if system else "false",
    "support": str(support) if support is not None else "",
  }

def _reset_scopes() -> None:
  _platform_admin.set(False)
  _service_scope.set(None)
  _system_scope.set(False)
  _support_org_id.set(None)

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
  _reset_scopes()
  await session.execute(_APPLY_SCOPE_SQL, _scope_params())
  await keyring.ensure_loaded(session, organization_id)

async def scope_session_as_platform_admin(session: AsyncSession) -> None:
  _platform_admin.set(True)
  await session.execute(_APPLY_SCOPE_SQL, _scope_params())

async def scope_session_as_dispatch(session: AsyncSession) -> None:
  _reset_scopes()
  clear_current_organization_id()
  _service_scope.set("dispatch")
  await session.execute(_APPLY_SCOPE_SQL, _scope_params())

async def scope_session_as_system(session: AsyncSession) -> None:
  """Seeds and maintenance that write shared rows nobody owns (organization_id IS NULL). Reads and writes no company's rows."""
  _reset_scopes()
  clear_current_organization_id()
  _system_scope.set(True)
  await session.execute(_APPLY_SCOPE_SQL, _scope_params())

async def scope_session_as_support(session: AsyncSession, organization_id: UUID) -> None:
  """Vendor support looking at one company: read-only, and the database refuses every row unless that company has an active support access grant."""
  _reset_scopes()
  clear_current_organization_id()
  _platform_admin.set(True)
  _support_org_id.set(organization_id)
  await session.execute(_APPLY_SCOPE_SQL, _scope_params())

@event.listens_for(Session, "after_begin")
def _reapply_tenant_settings(session, transaction, connection) -> None:
  params = _scope_params()
  if params is None:
    return
  connection.execute(_APPLY_SCOPE_SQL, params)