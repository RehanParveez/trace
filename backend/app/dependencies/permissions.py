from __future__ import annotations
from collections.abc import Callable
from fastapi import Depends
from app.core.exceptions import TraceException
from app.dependencies.auth import get_current_user
from app.modules.identity.models import User

def require_permission(
  permission_key: str,
) -> Callable:
  async def dependency(
    current_user: User = Depends(
      get_current_user
    ),
  ) -> User:
    permissions = {
      permission.key
      for permission in current_user.role.permissions
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
    current_user: User = Depends(
      get_current_user
    ),
  ) -> User:
    from app.core.database import AsyncSessionLocal
    from app.modules.identity.repository import IdentityRepository

    async with AsyncSessionLocal() as session:
      repository = IdentityRepository(session)
      platform_admin = (
        await repository.get_platform_admin(
          current_user.id
        )
      )
    if platform_admin is None:
      raise TraceException(
        "Platform administrator access required.",
        status_code=403,
        code="PLATFORM_ADMIN_REQUIRED",
      )
    return current_user

  return dependency