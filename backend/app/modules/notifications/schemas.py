from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.modules.notifications.models import NotificationType

class NotificationResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  type: NotificationType
  title: str
  body: str | None
  link_path: str | None
  is_read: bool
  read_at: datetime | None
  created_at: datetime

class UnreadCountResponse(BaseModel):
  unread_count: int
  
class MessageResponse(BaseModel):
  message: str