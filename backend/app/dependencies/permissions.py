from __future__ import annotations
from collections.abc import Callable
from fastapi import Depends
from app.modules.identity.models import User
from app.dependencies.auth import get_current_user
from app.core.exceptions import TraceException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.identity.repository import IdentityRepository

def require_permission(permission_key: str) -> Callable:
  async def dependency(
    current_user: User = Depends(get_current_user),
  ) -> User:
    membership = getattr(current_user, "active_membership", None)

    if membership is None:
      raise TraceException(
        "Authentication context mismatch.",
        status_code=401,
        code="AUTHENTICATION_CONTEXT_MISMATCH",
      )

    permissions = {
      permission.key
      for permission in membership.role.permissions
    }

    if permission_key not in permissions:
      raise TraceException(
        "You do not have permission to perform this action.",
        status_code=403,
        code="PERMISSION_DENIED",
      )

    return current_user

  return dependency

def require_platform_admin() -> Callable:
  async def dependency(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
  ) -> User:
    repository = IdentityRepository(session)
    platform_admin = await repository.get_platform_admin(current_user.id)

    if platform_admin is None:
      raise TraceException(
        "Platform administrator access required.",
        status_code=403,
        code="PLATFORM_ADMIN_REQUIRED",
      )

    return current_user

  return dependency