from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class OrganizationResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  name: str
  slug: str
  is_active: bool
  ai_enabled: bool
  created_at: datetime
  updated_at: datetime

class OrganizationUpdateRequest(BaseModel):
  name: str | None = Field(
    default=None, min_length=2, max_length=255
  )
  slug: str | None = Field(
    default=None, min_length=2, max_length=100
  )
  ai_enabled: bool | None = None

  @field_validator("name")
  @classmethod
  def normalize_name(cls, value: str | None) -> str | None:
    if value is None:
      return None
    value = value.strip()
    if not value:
      raise ValueError("Organization name cannot be empty.")
    return value

  @field_validator("slug")
  @classmethod
  def normalize_slug(cls, value: str | None) -> str | None:
    if value is None:
      return None
    value = value.strip().lower()
    if not value:
      raise ValueError("Organization slug cannot be empty.")
    return value

class AISettingsResponse(BaseModel):
  ai_enabled: bool

class AISettingsUpdateRequest(BaseModel):
  ai_enabled: bool

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
  permissions: list[PermissionResponse] = Field(default_factory=list)

class RoleCreateRequest(BaseModel):
  name: str = Field(min_length=2, max_length=100)
  description: str | None = Field(default=None, max_length=500)
  permission_ids: list[UUID] = Field(default_factory=list)

  @field_validator("name")
  @classmethod
  def normalize_name(cls, value: str) -> str:
    value = value.strip()
    if not value:
      raise ValueError("Role name cannot be empty.")
    return value

class RoleUpdateRequest(BaseModel):
  name: str | None = Field(default=None, min_length=2, max_length=100)
  description: str | None = Field(default=None, max_length=500)
  permission_ids: list[UUID] | None = None

  @field_validator("name")
  @classmethod
  def normalize_name(cls, value: str | None) -> str | None:
    if value is None:
      return None
    value = value.strip()
    if not value:
      raise ValueError("Role name cannot be empty.")
    return value

class MemberResponse(BaseModel):
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

class MemberRoleUpdateRequest(BaseModel):
  role_id: UUID

class MemberStatusUpdateRequest(BaseModel):
  is_active: bool

class InvitationCreateRequest(BaseModel):
  email: EmailStr
  role_id: UUID

class InvitationAcceptRequest(BaseModel):
  token: str = Field(min_length=1, max_length=4096)

class InvitationAcceptanceResponse(BaseModel):
  message: str
  organization_id: UUID
  organization_name: str
  role_id: UUID
  role_name: str

class InvitationResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  email: EmailStr
  role_id: UUID
  invited_by_user_id: UUID
  accepted_by_user_id: UUID | None
  expires_at: datetime
  accepted_at: datetime | None
  revoked_at: datetime | None
  created_at: datetime