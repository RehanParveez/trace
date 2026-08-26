from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.identity.models import Permission, PlatformAdmin, RefreshToken, Role, User

class IdentityRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def get_user_by_id(
    self,
    user_id: UUID,
  ) -> User | None:
    result = await self.session.execute(
      select(User)
      .where(User.id == user_id)
      .options(
        selectinload(User.organization),
        selectinload(User.role)
        .selectinload(Role.permissions),
      )
    )
    return result.scalar_one_or_none()

  async def get_user_by_email(
    self,
    email: str,
  ) -> User | None:
    result = await self.session.execute(
      select(User)
      .where(User.email == email.strip().lower())
      .options(
        selectinload(User.organization),
        selectinload(User.role)
        .selectinload(Role.permissions),
      )
    )
    return result.scalar_one_or_none()

  async def get_role_by_id(
    self,
    role_id: UUID,
  ) -> Role | None:
    result = await self.session.execute(
      select(Role)
      .where(Role.id == role_id)
      .options(
        selectinload(Role.permissions),
      )
    )
    return result.scalar_one_or_none()

  async def get_permission_by_key(
    self,
    key: str,
  ) -> Permission | None:
    result = await self.session.execute(
      select(Permission)
      .where(Permission.key == key)
    )
    return result.scalar_one_or_none()

  async def get_platform_admin(
    self,
    user_id: UUID,
  ) -> PlatformAdmin | None:
    result = await self.session.execute(
      select(PlatformAdmin)
      .where(PlatformAdmin.user_id == user_id)
    )
    return result.scalar_one_or_none()

  async def get_refresh_token_by_hash(
    self,
    token_hash: str,
  ) -> RefreshToken | None:
    result = await self.session.execute(
      select(RefreshToken)
      .where(
        RefreshToken.token_hash == token_hash
      )
      .options(
        selectinload(RefreshToken.user),
        selectinload(RefreshToken.organization),
      )
    )
    return result.scalar_one_or_none()

  async def add_refresh_token(
    self,
    refresh_token: RefreshToken,
  ) -> RefreshToken:
    self.session.add(refresh_token)
    await self.session.flush()
    return refresh_token

  async def revoke_refresh_token(
    self,
    refresh_token: RefreshToken,
    replacement_id: UUID | None = None,
  ) -> None:
    refresh_token.revoked_at = datetime.now(timezone.utc)
    refresh_token.replaced_by_token_id = replacement_id
    refresh_token.last_used_at = datetime.now(timezone.utc)
    await self.session.flush()

  async def revoke_all_user_refresh_tokens(
    self,
    user_id: UUID,
  ) -> None:
    now = datetime.now(timezone.utc)

    await self.session.execute(
      update(RefreshToken)
      .where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
      )
      .values(
        revoked_at=now,
        last_used_at=now,
      )
    )
    await self.session.flush()

  async def update_user_last_login(
    self,
    user: User,
  ) -> None:
    user.last_login_at = datetime.now(timezone.utc)
    user.failed_login_attempts = 0
    user.locked_until = None
    await self.session.flush()

  async def record_failed_login(
    self,
    user: User,
    *,
    locked_until: datetime | None = None,
  ) -> None:
    user.failed_login_attempts += 1

    if locked_until is not None:
      user.locked_until = locked_until
    await self.session.flush()

  async def update_password(
    self,
    user: User,
    password_hash: str,
  ) -> None:
    user.password_hash = password_hash
    user.password_changed_at = datetime.now(
      timezone.utc
    )
    await self.session.flush()

  async def mark_email_verified(
    self,
    user: User,
  ) -> None:
    user.is_verified = True
    await self.session.flush()