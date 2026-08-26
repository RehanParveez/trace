from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128

class PasswordMixin(BaseModel):
  password: str = Field(
    min_length=PASSWORD_MIN_LENGTH,
    max_length=PASSWORD_MAX_LENGTH,
  )

class LoginRequest(PasswordMixin):
  email: EmailStr

  @field_validator("email")
  @classmethod
  def normalize_email(cls, value: EmailStr) -> str:
    return str(value).strip().lower()

class RegisterRequest(BaseModel):
  email: EmailStr

  password: str = Field(
    min_length=PASSWORD_MIN_LENGTH,
    max_length=PASSWORD_MAX_LENGTH,
  )

  password_confirmation: str = Field(
    min_length=PASSWORD_MIN_LENGTH,
    max_length=PASSWORD_MAX_LENGTH,
  )

  first_name: str = Field(
    min_length=1,
    max_length=100,
  )

  last_name: str = Field(
    min_length=1,
    max_length=100,
  )

  organization_name: str = Field(
    min_length=2,
    max_length=255,
  )

  @field_validator("email")
  @classmethod
  def normalize_email(cls, value: EmailStr) -> str:
    return str(value).strip().lower()

  @field_validator("password_confirmation")
  @classmethod
  def passwords_match(
    cls,
    value: str,
    info,
  ) -> str:
    password = info.data.get("password")

    if password is not None and value != password:
      raise ValueError("Passwords do not match.")

    return value

class RefreshRequest(BaseModel):
  refresh_token: str = Field(
    min_length=1,
    max_length=4096,
  )

class LogoutRequest(BaseModel):
  refresh_token: str = Field(
    min_length=1,
    max_length=4096,
  )

class ForgotPasswordRequest(BaseModel):
  email: EmailStr

  @field_validator("email")
  @classmethod
  def normalize_email(cls, value: EmailStr) -> str:
    return str(value).strip().lower()

class ResetPasswordRequest(BaseModel):
  token: str = Field(
    min_length=1,
    max_length=4096,
  )

  password: str = Field(
    min_length=PASSWORD_MIN_LENGTH,
    max_length=PASSWORD_MAX_LENGTH,
  )

  password_confirmation: str = Field(
    min_length=PASSWORD_MIN_LENGTH,
    max_length=PASSWORD_MAX_LENGTH,
  )

  @field_validator("password_confirmation")
  @classmethod
  def passwords_match(
    cls,
    value: str,
    info,
  ) -> str:
    password = info.data.get("password")

    if password is not None and value != password:
      raise ValueError("Passwords do not match.")

    return value

class ChangePasswordRequest(BaseModel):
  current_password: str = Field(
    min_length=1,
    max_length=128,
  )

  new_password: str = Field(
    min_length=PASSWORD_MIN_LENGTH,
    max_length=PASSWORD_MAX_LENGTH,
  )

  new_password_confirmation: str = Field(
    min_length=PASSWORD_MIN_LENGTH,
    max_length=PASSWORD_MAX_LENGTH,
  )

  @field_validator("new_password_confirmation")
  @classmethod
  def passwords_match(
    cls,
    value: str,
    info,
  ) -> str:
    password = info.data.get("new_password")

    if password is not None and value != password:
      raise ValueError("Passwords do not match.")
    return value

class VerifyEmailRequest(BaseModel):
  token: str = Field(
    min_length=1,
    max_length=4096,
  )

class ResendVerificationRequest(BaseModel):
  email: EmailStr

  @field_validator("email")
  @classmethod
  def normalize_email(cls, value: EmailStr) -> str:
    return str(value).strip().lower()

class PermissionResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  key: str
  description: str | None

class RoleResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  name: str
  description: str | None
  is_system: bool
  permissions: list[PermissionResponse] = Field(
    default_factory=list,
  )

class OrganizationResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  name: str
  slug: str
  is_active: bool

class UserResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  organization_id: UUID
  email: EmailStr
  first_name: str
  last_name: str
  is_active: bool
  is_verified: bool
  last_login_at: datetime | None
  role: RoleResponse
  organization: OrganizationResponse

class TokenResponse(BaseModel):
  access_token: str
  refresh_token: str
  token_type: str = "bearer"

class LoginResponse(BaseModel):
  user: UserResponse
  tokens: TokenResponse

class CurrentUserResponse(BaseModel):
  user: UserResponse

class MessageResponse(BaseModel):
  message: str

class PasswordResetResponse(BaseModel):
  message: str

class RegistrationResponse(BaseModel):
  user: UserResponse
  message: str