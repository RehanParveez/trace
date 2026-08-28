from __future__ import annotations
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.modules.projects.models import ProjectMemberRole, ProjectStatus

class ClientCreate(BaseModel):
  name: str = Field(
    min_length=1,
    max_length=200,
  )

  contact_name: str | None = Field(
    default=None,
    max_length=200,
  )

  email: str | None = Field(
    default=None,
    max_length=255,
  )

  phone: str | None = Field(
    default=None,
    max_length=50,
  )

  address: str | None = None
  notes: str | None = None

class ClientUpdate(BaseModel):
  name: str | None = Field(
    default=None,
    min_length=1,
    max_length=200,
  )

  contact_name: str | None = Field(
    default=None,
    max_length=200,
  )

  email: str | None = Field(
    default=None,
    max_length=255,
  )

  phone: str | None = Field(
    default=None,
    max_length=50,
  )

  address: str | None = None

  notes: str | None = None

class ClientResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  organization_id: UUID
  name: str
  contact_name: str | None
  email: str | None
  phone: str | None
  address: str | None
  notes: str | None
  created_at: datetime
  updated_at: datetime

class ProjectCreate(BaseModel):
  name: str = Field(
    min_length=1,
    max_length=200,
  )

  code: str | None = Field(
    default=None,
    max_length=100,
  )

  description: str | None = None

  location: str | None = Field(
    default=None,
    max_length=500,
  )

  client_id: UUID | None = None
  start_date: date | None = None
  expected_end_date: date | None = None

class ProjectUpdate(BaseModel):
  name: str | None = Field(
    default=None,
    min_length=1,
    max_length=200,
  )

  code: str | None = Field(
    default=None,
    max_length=100,
  )

  description: str | None = None
  location: str | None = Field(
    default=None,
    max_length=500,
  )
  
  client_id: UUID | None = None
  status: ProjectStatus | None = None
  start_date: date | None = None
  expected_end_date: date | None = None
  actual_end_date: date | None = None

class ProjectResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  organization_id: UUID
  client_id: UUID | None
  name: str
  code: str | None
  description: str | None
  location: str | None

  status: ProjectStatus

  start_date: date | None
  expected_end_date: date | None
  actual_end_date: date | None
  created_at: datetime
  updated_at: datetime

class ProjectMemberCreate(BaseModel):
  user_id: UUID
  role: ProjectMemberRole = ProjectMemberRole.MEMBER

class ProjectMemberUpdate(BaseModel):
  role: ProjectMemberRole

class ProjectMemberResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  user_id: UUID
  role: ProjectMemberRole
  created_at: datetime
  updated_at: datetime

class MilestoneCreate(BaseModel):
  name: str = Field(
    min_length=1,
    max_length=200,
  )

  description: str | None = None
  due_date: date | None = None

class MilestoneUpdate(BaseModel):
  name: str | None = Field(
    default=None,
    min_length=1,
    max_length=200,
  )

  description: str | None = None
  due_date: date | None = None
  completed_at: date | None = None

class MilestoneResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID
  name: str
  description: str | None
  due_date: date | None
  completed_at: date | None
  created_at: datetime
  updated_at: datetime