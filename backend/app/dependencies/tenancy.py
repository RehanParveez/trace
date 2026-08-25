from contextvars import ContextVar
from uuid import UUID

_current_organization_id: ContextVar[UUID | None] = ContextVar(
  "current_organization_id",
   default=None,
)

def set_current_organization_id(organization_id: UUID | None) -> None:
  _current_organization_id.set(organization_id)

def get_current_organization_id() -> UUID | None:
  return _current_organization_id.get()

def clear_current_organization_id() -> None:
  _current_organization_id.set(None)