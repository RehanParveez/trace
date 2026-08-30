from __future__ import annotations
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.modules.whatsapp.models import PhotoTagSource

class ChannelConnectRequest(BaseModel):
  phone_number_id: str = Field(
    min_length=1,
    max_length=64,
  )
  business_account_id: str = Field(
    min_length=1,
    max_length=64,
  )
  access_token: str = Field(
    min_length=1,
  )
  display_phone_number: str | None = Field(
    default=None,
    max_length=32,
  )

class ChannelResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  phone_number_id: str
  business_account_id: str
  display_phone_number: str | None
  is_active: bool
  created_at: datetime

class PhotoTagResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  tag: str
  confidence: float | None
  source: PhotoTagSource

class PhotoTagCreateRequest(BaseModel):
  tag: str = Field(
    min_length=1,
    max_length=100,
  )

class SitePhotoResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  project_id: UUID | None
  storage_key: str
  sender_phone_number: str | None
  caption_raw: str | None
  caption_parsed: dict
  location_text: str | None
  photo_date: date | None
  is_ai_tagged: bool
  tags: list[PhotoTagResponse] = Field(
    default_factory=list,
  )
  created_at: datetime
  photo_url: str

class SitePhotoAssignProjectRequest(BaseModel):
  project_id: UUID

class SitePhotoUpdateRequest(BaseModel):
  location_text: str | None = Field(
    default=None,
    max_length=500,
  )
  photo_date: date | None = None