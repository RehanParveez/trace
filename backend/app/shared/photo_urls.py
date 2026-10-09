from __future__ import annotations
from pydantic import BaseModel, computed_field, Field
from app.shared.storage import generate_presigned_url
from app.core.config import settings

class PhotoUrlMixin(BaseModel):
  photo_storage_key: str | None = Field(default=None, exclude=True)
  
  @computed_field
  @property
  def photo_url(self) -> str | None:
    if not self.photo_storage_key:
      return None
    return generate_presigned_url(self.photo_storage_key)

  @computed_field
  @property
  def photo_url_expires_in(self) -> int:
    return settings.site_photo_url_ttl_seconds