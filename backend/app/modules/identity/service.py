from __future__ import annotations
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import TraceException
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.modules.identity.enums import TokenType
from app.modules.identity.models import RefreshToken, User
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import LoginResponse, RegistrationResponse, TokenResponse
from app.modules.identity.password_policy import validate_password

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

class IdentityService:
  def __init__(
    self,
    session: AsyncSession,
  ):
    self.session = session
    self.repository = IdentityRepository(
      session
    )

  @staticmethod
  def hash_refresh_token(
    token: str,
  ) -> str:
    return hashlib.sha256(
      token.encode("utf-8")
    ).hexdigest()

  @staticmethod
  def generate_one_time_token() -> str:
    return secrets.token_urlsafe(48)

  @staticmethod
  def normalize_email(email: str) -> str:
    return email.strip().lower()

  async def authenticate(
    self,
    email: str,
    password: str,
  ) -> User:
    email = self.normalize_email(email)

    user = await self.repository.get_user_by_email(
      email
    )
    if user is None:
      raise TraceException(
        "Invalid email or password.",
        status_code=401,
        code="INVALID_CREDENTIALS",
      )

    now = datetime.now(timezone.utc)
    if (
      user.locked_until is not None
      and user.locked_until > now
    ):
      raise TraceException(
        "Account temporarily locked. Please try again later.",
        status_code=429,
        code="ACCOUNT_TEMPORARILY_LOCKED",
      )

    if not verify_password(
      password,
      user.password_hash,
    ):
      failed_attempts = (
        user.failed_login_attempts + 1
      )

      locked_until = None
      if (
        failed_attempts
        >= MAX_FAILED_LOGIN_ATTEMPTS
      ):
        locked_until = (
          now
          + timedelta(
            minutes=LOCKOUT_MINUTES
          )
        )
      await self.repository.record_failed_login(
        user,
        locked_until=locked_until,
      )

      await self.session.commit()
      raise TraceException(
        "Invalid email or password.",
        status_code=401,
        code="INVALID_CREDENTIALS",
      )
    if not user.is_active:
      raise TraceException(
        "User account is inactive.",
        status_code=403,
        code="USER_INACTIVE",
      )
    if not user.organization.is_active:
      raise TraceException(
        "Organization is inactive.",
        status_code=403,
        code="ORGANIZATION_INACTIVE",
      )
    return user

  async def login(
    self,
    email: str,
    password: str,
  ) -> LoginResponse:
    user = await self.authenticate(
      email=email,
      password=password,
    )

    access_token = create_access_token(
      subject=str(user.id),
      organization_id=str(
        user.organization_id
      ),
    )

    refresh_token = create_refresh_token(
      subject=str(user.id),
      organization_id=str(
        user.organization_id
      ),
    )

    await self._store_refresh_token(
      user=user,
      raw_token=refresh_token,
    )

    await self.repository.update_user_last_login(
      user
    )
    
    await self.session.commit()

    return LoginResponse(
      user=user,
      tokens=TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
      ),
    )

  async def refresh(
    self,
    raw_refresh_token: str,
  ) -> TokenResponse:
    try:
      payload = decode_token(
        raw_refresh_token
      )
    except Exception as exc:
      raise TraceException(
        "Invalid refresh token.",
        status_code=401,
        code="INVALID_REFRESH_TOKEN",
      ) from exc

    if payload.get("type") != TokenType.REFRESH:
      raise TraceException(
        "Invalid token type.",
        status_code=401,
        code="INVALID_TOKEN_TYPE",
      )

    subject = payload.get("sub")
    organization_id = payload.get("org_id")

    if not subject or not organization_id:
      raise TraceException(
        "Invalid refresh token.",
        status_code=401,
        code="INVALID_REFRESH_TOKEN",
      )

    try:
      user_id = UUID(subject)
      token_org_id = UUID(organization_id)
    except ValueError as exc:
      raise TraceException(
        "Invalid refresh token claims.",
        status_code=401,
        code="INVALID_REFRESH_TOKEN",
      ) from exc

    token_hash = self.hash_refresh_token(
      raw_refresh_token
    )

    stored_token = (
      await self.repository
      .get_refresh_token_by_hash(
        token_hash
      )
    )

    if stored_token is None:
      raise TraceException(
        "Invalid refresh token.",
        status_code=401,
        code="INVALID_REFRESH_TOKEN",
      )

    if stored_token.user_id != user_id:
      raise TraceException(
        "Invalid refresh token.",
        status_code=401,
        code="INVALID_REFRESH_TOKEN",
      )

    if (
      stored_token.organization_id
      != token_org_id
    ):
      raise TraceException(
        "Invalid refresh token.",
        status_code=401,
        code="INVALID_REFRESH_TOKEN",
      )

    if stored_token.is_revoked:
      await self.repository.revoke_all_user_refresh_tokens(
        user_id
      )
      await self.session.commit()
      raise TraceException(
        "Refresh token reuse detected.",
        status_code=401,
        code="REFRESH_TOKEN_REUSE_DETECTED",
      )

    if stored_token.expires_at <= datetime.now(
      timezone.utc
    ):
      raise TraceException(
        "Refresh token has expired.",
        status_code=401,
        code="REFRESH_TOKEN_EXPIRED",
      )
    user = await self.repository.get_user_by_id(
      user_id
    )
    if user is None or not user.is_active:
      raise TraceException(
        "User account is unavailable.",
        status_code=401,
        code="USER_UNAVAILABLE",
      )

    if not user.organization.is_active:
      raise TraceException(
        "Organization is inactive.",
        status_code=403,
        code="ORGANIZATION_INACTIVE",
      )
    new_access_token = create_access_token(
      subject=str(user.id),
      organization_id=str(
        user.organization_id
      ),
    )
    new_refresh_token = create_refresh_token(
      subject=str(user.id),
      organization_id=str(
        user.organization_id
      ),
    )
    replacement = await self._store_refresh_token(
      user=user,
      raw_token=new_refresh_token,
    )
    await self.repository.revoke_refresh_token(
      stored_token,
      replacement_id=replacement.id,
    )

    await self.session.commit()
    return TokenResponse(
      access_token=new_access_token,
      refresh_token=new_refresh_token,
    )

  async def logout(
    self,
    raw_refresh_token: str,
  ) -> None:
    token_hash = self.hash_refresh_token(
      raw_refresh_token
    )
    stored_token = (
      await self.repository
      .get_refresh_token_by_hash(
        token_hash
      )
    )
    if stored_token is None:
      return

    if not stored_token.is_revoked:
      await self.repository.revoke_refresh_token(
        stored_token
      )
    await self.session.commit()

  async def logout_all(
    self,
    user_id: UUID,
  ) -> None:
    await self.repository.revoke_all_user_refresh_tokens(
      user_id
    )
    await self.session.commit()

  async def get_current_user(
    self,
    user_id: UUID,
  ) -> User:
    user = await self.repository.get_user_by_id(
      user_id
    )

    if user is None:
      raise TraceException(
        "User not found.",
        status_code=401,
        code="USER_NOT_FOUND",
      )

    if not user.is_active:
      raise TraceException(
        "User account is inactive.",
        status_code=403,
        code="USER_INACTIVE",
      )

    if not user.organization.is_active:
      raise TraceException(
        "Organization is inactive.",
        status_code=403,
        code="ORGANIZATION_INACTIVE",
      )
    return user

  async def _store_refresh_token(
    self,
    user: User,
    raw_token: str,
  ) -> RefreshToken:
    payload = decode_token(raw_token)

    expires_at = datetime.fromtimestamp(
      payload["exp"],
      tz=timezone.utc,
    )
    token = RefreshToken(
      id=uuid4(),
      user_id=user.id,
      organization_id=user.organization_id,
      token_hash=self.hash_refresh_token(
        raw_token
      ),
      expires_at=expires_at,
    )

    return await self.repository.add_refresh_token(
      token
    )
    
  async def verify_email(self, token: str,
) -> None:
   user_id = await self.token_store.consume(
    prefix="email-verification",
    token=token,
  )

   if not user_id:
    raise TraceException(
      "Invalid or expired verification token.",
      status_code=400,
      code="INVALID_VERIFICATION_TOKEN",
    )
   user = await self.repository.get_user_by_id(
    UUID(user_id)
  )
   if user is None:
    raise TraceException(
      "Invalid verification token.",
      status_code=400,
      code="INVALID_VERIFICATION_TOKEN",
    )

   if user.is_verified:
    return
   await self.repository.mark_email_verified(user)

   await self.session.commit()