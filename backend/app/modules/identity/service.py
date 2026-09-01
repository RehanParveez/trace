from __future__ import annotations
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import TraceException
from app.core.redis import IdentityTokenStore
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.modules.identity.enums import TokenType
from app.modules.identity.models import RefreshToken, User, Organization
from app.modules.identity.password_policy import validate_password
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import LoginResponse, RegistrationResponse, TokenResponse
from app.core.config import settings
from app.modules.identity.email import EmailService
from sqlalchemy import select

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

EMAIL_VERIFICATION_TTL_SECONDS = 60 * 60 * 24
PASSWORD_RESET_TTL_SECONDS = 60 * 15


class IdentityService:
  def __init__(
    self,
    session: AsyncSession,
    token_store: IdentityTokenStore,
    email_service: EmailService | None = None,
  ):
    self.session = session

    self.repository = IdentityRepository(
      session
    )

    self.token_store = token_store
    self.email_service = email_service or EmailService()

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
  def normalize_email(
    email: str,
  ) -> str:
    return email.strip().lower()

  @staticmethod
  def generate_organization_slug(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        slug,
    )
    slug = slug.strip("-")

    return slug

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

  async def get_organization_by_slug(
    self,
    slug: str,
  ) -> Organization | None:
    result = await self.session.execute(
      select(Organization).where(Organization.slug == slug)
    )
    return result.scalar_one_or_none()
  
  async def register(self, email: str, password: str, first_name: str, last_name: str, organization_name: str, password_confirmation: str,
) -> RegistrationResponse:

   email = self.normalize_email(email)

   if password != password_confirmation:
    raise TraceException(
      "Passwords do not match.",
      status_code=422,
      code="PASSWORD_MISMATCH",
    )

   validate_password(password)

   existing_user = await self.repository.get_user_by_email(
    email
   )

   if existing_user is not None:
    raise TraceException(
      "An account with this email already exists.",
      status_code=409,
      code="EMAIL_ALREADY_REGISTERED",
    )

   organization_name = organization_name.strip()

   if not organization_name:
    raise TraceException(
      "Organization name is required.",
      status_code=422,
      code="ORGANIZATION_NAME_REQUIRED",
    )

   organization = await self.repository.get_organization_by_name(
    organization_name
   )

   if organization is not None:
    raise TraceException(
      "An organization with this name already exists.",
      status_code=409,
      code="ORGANIZATION_ALREADY_EXISTS",
    )

   organization_slug = self.generate_organization_slug(
    organization_name
   )

   if await self.repository.get_organization_by_slug(organization_slug) is not None:
    organization_slug = f"{organization_slug}-{secrets.token_hex(3)}"

   organization = await self.repository.create_organization(
    name=organization_name,
    slug=organization_slug,
  )

   role = await self.repository.get_role_by_name(
    organization_id=organization.id,
    name="Company Admin",
   )

   if role is None:
    role = await self.repository.create_role(
      organization_id=organization.id,
      name="Company Admin",
      description=(
        "Full administrative access to the organization."
      ),
      is_system=True,
    )

   user = await self.repository.create_user(
    organization_id=organization.id,
    role_id=role.id,
    email=email,
    password_hash=hash_password(password),
    first_name=first_name.strip(),
    last_name=last_name.strip(),
    is_active=True,
    is_verified=False,
  )

   await self.session.commit()

   user = await self.repository.get_user_by_id(
    user.id
  )

   if user is None:
    raise TraceException(
      "Failed to load newly created user.",
      status_code=500,
      code="REGISTRATION_USER_LOAD_FAILED",
    )

   verification_token = await self.create_email_verification_token(user)
   await self.email_service.send(
     recipient=user.email,
     subject="Verify your email address",
     body=(
       "Welcome. Please verify your email address:\n\n"
       f"{settings.frontend_base_url}/verify-email?token={verification_token}"
     ),
   )

   return RegistrationResponse(
    user=user,
    verification_required=True,
    message=(
      "Registration successful. "
      "Please verify your email."
    ),
  )

  async def create_email_verification_token(
    self,
    user: User,
  ) -> str:
    return await self.token_store.create(
      prefix="email-verification",
      user_id=str(user.id),
      ttl_seconds=EMAIL_VERIFICATION_TTL_SECONDS,
    )

  async def verify_email(
    self,
    token: str,
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

    try:
      parsed_user_id = UUID(user_id)
    except ValueError as exc:
      raise TraceException(
        "Invalid verification token.",
        status_code=400,
        code="INVALID_VERIFICATION_TOKEN",
      ) from exc

    user = await self.repository.get_user_by_id(
      parsed_user_id
    )

    if user is None:
      raise TraceException(
        "Invalid verification token.",
        status_code=400,
        code="INVALID_VERIFICATION_TOKEN",
      )

    if user.is_verified:
      return

    await self.repository.mark_email_verified(
      user
    )

    await self.session.commit()

  async def resend_verification(
    self,
    email: str,
  ) -> str | None:
    email = self.normalize_email(email)

    user = await self.repository.get_user_by_email(email)
    if user is None or user.is_verified:
      return None
    token = await self.create_email_verification_token(user)

    await self.email_service.send(
      recipient=user.email,
      subject="Verify your email address",
      body=f"Verify your email address: {settings.frontend_base_url}/verify-email?token={token}",
    )

    return token

  async def change_password(
    self,
    user: User,
    current_password: str,
    new_password: str,
    password_confirmation: str,
  ) -> None:

    if not verify_password(
      current_password,
      user.password_hash,
    ):
      raise TraceException(
        "Current password is incorrect.",
        status_code=400,
        code="INVALID_CURRENT_PASSWORD",
      )

    if new_password != password_confirmation:
      raise TraceException(
        "Passwords do not match.",
        status_code=422,
        code="PASSWORD_MISMATCH",
      )

    if verify_password(
      new_password,
      user.password_hash,
    ):
      raise TraceException(
        "New password must be different from your current password.",
        status_code=422,
        code="PASSWORD_REUSE",
      )

    validate_password(new_password)

    user.password_hash = hash_password(
      new_password
    )

    user.failed_login_attempts = 0
    user.locked_until = None

    await self.repository.revoke_all_user_refresh_tokens(
      user.id
    )

    await self.session.commit()

  async def create_password_reset_token(
    self,
    user: User,
  ) -> str:
    return await self.token_store.create(
      prefix="password-reset",
      user_id=str(user.id),
      ttl_seconds=PASSWORD_RESET_TTL_SECONDS,
    )

  async def forgot_password(
    self,
    email: str,
  ) -> str | None:
    email = self.normalize_email(email)

    user = await self.repository.get_user_by_email(email)
    if user is None:
      return None
    token = await self.create_password_reset_token(user)
    await self.email_service.send(
      recipient=user.email,
      subject="Reset your password",
      body=f"Reset your password: {settings.frontend_base_url}/reset-password?token={token}",
    )
    return token

  async def reset_password(
    self,
    token: str,
    new_password: str,
  ) -> None:

    user_id = await self.token_store.consume(
      prefix="password-reset",
      token=token,
    )

    if not user_id:
      raise TraceException(
        "Invalid or expired password reset token.",
        status_code=400,
        code="INVALID_RESET_TOKEN",
      )

    try:
      parsed_user_id = UUID(user_id)
    except ValueError as exc:
      raise TraceException(
        "Invalid password reset token.",
        status_code=400,
        code="INVALID_RESET_TOKEN",
      ) from exc

    user = await self.repository.get_user_by_id(
      parsed_user_id
    )

    if user is None:
      raise TraceException(
        "Invalid password reset token.",
        status_code=400,
        code="INVALID_RESET_TOKEN",
      )

    validate_password(new_password)

    user.password_hash = hash_password(
      new_password
    )

    user.failed_login_attempts = 0
    user.locked_until = None

    await self.repository.revoke_all_user_refresh_tokens(
      user.id
    )

    await self.session.commit()

  async def login(
    self,
    email: str, password: str) -> LoginResponse:
    user = await self.authenticate(email=email, password=password)
    tokens = await self.issue_tokens(user)
    await self.repository.update_user_last_login(user)
    await self.session.commit()
    
    return LoginResponse(user=user, tokens=tokens)

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
    
  async def issue_tokens(self, user: User) -> TokenResponse:
    access_token = create_access_token(
      subject=str(user.id),
      organization_id=str(user.organization_id),
    )
    refresh_token = create_refresh_token(
      subject=str(user.id),
      organization_id=str(user.organization_id),
    )
    
    await self._store_refresh_token(user=user, raw_token=refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

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

    if (
      stored_token.expires_at
      <= datetime.now(timezone.utc)
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