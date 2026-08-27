from __future__ import annotations
from collections.abc import Callable
from fastapi import Depends
from app.core.database import AsyncSessionLocal
from app.core.exceptions import TraceException
from app.dependencies.auth import get_current_user
from app.modules.identity.models import User
from app.modules.identity.repository import IdentityRepository

def require_permission(
  permission_key: str,
) -> Callable:
  async def dependency(
    current_user: User = Depends(
      get_current_user
    ),
  ) -> User:
    print(f"=== PERMISSION CHECK DEBUG ===")
    print(f"User email: {current_user.email}")
    print(f"User ID: {current_user.id}")
    print(f"User role: {current_user.role}")
    print(f"User role ID: {current_user.role.id if current_user.role else None}")
    print(f"Required permission: {permission_key}")

    if current_user.role:
      permissions = {
        permission.key
        for permission in current_user.role.permissions
      }
      print(f"User's role permissions: {permissions}")
      print(f"Has required permission: {permission_key in permissions}")
    else:
      print("User has NO ROLE assigned!")
      permissions = set()

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