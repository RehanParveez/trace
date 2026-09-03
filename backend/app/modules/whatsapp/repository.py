from __future__ import annotations
from datetime import date
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.whatsapp.models import PhotoTag, SitePhoto, WhatsAppChannel, WhatsAppMessage

class WhatsAppChannelRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(
    self,
    channel: WhatsAppChannel,
  ) -> WhatsAppChannel:
    self.session.add(channel)
    await self.session.flush()
    return channel

  async def get_by_organization(
    self,
    organization_id: UUID,
  ) -> WhatsAppChannel | None:
    result = await self.session.execute(
      select(WhatsAppChannel).where(
        WhatsAppChannel.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def get_by_phone_number_id(
    self,
    phone_number_id: str,
  ) -> WhatsAppChannel | None:
    result = await self.session.execute(
      select(WhatsAppChannel).where(
        WhatsAppChannel.phone_number_id == phone_number_id,
        WhatsAppChannel.is_active.is_(True),
      )
    )
    return result.scalar_one_or_none()

  async def update(
    self,
    channel: WhatsAppChannel,
  ) -> WhatsAppChannel:
    self.session.add(channel)
    await self.session.flush()
    return channel

class WhatsAppMessageRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def try_create(
    self,
    message: WhatsAppMessage,
) -> WhatsAppMessage | None:
    self.session.add(message)

    try:
      async with self.session.begin_nested():
        await self.session.flush()
    except IntegrityError:
      return None

    return message

  async def get_by_id(
    self,
    message_id: UUID,
  ) -> WhatsAppMessage | None:
    result = await self.session.execute(
      select(WhatsAppMessage).where(
        WhatsAppMessage.id == message_id
      )
    )
    return result.scalar_one_or_none()
  
  async def get_by_id_for_update(
    self,
    message_id: UUID,
  ) -> WhatsAppMessage | None:
   result = await self.session.execute(
    select(WhatsAppMessage)
    .where(WhatsAppMessage.id == message_id)
    .with_for_update()
  )

   return result.scalar_one_or_none()

  async def get_by_prompt_wa_message_id(
    self,
    prompt_wa_message_id: str,
  ) -> WhatsAppMessage | None:
    result = await self.session.execute(
      select(WhatsAppMessage).where(
        WhatsAppMessage.prompt_wa_message_id == prompt_wa_message_id,
      )
    )
    return result.scalar_one_or_none()

  async def update(
    self,
    message: WhatsAppMessage,
  ) -> WhatsAppMessage:
    self.session.add(message)
    await self.session.flush()
    return message

class SitePhotoRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(
    self,
    photo: SitePhoto,
  ) -> SitePhoto:
    self.session.add(photo)
    await self.session.flush()
    return photo

  async def get_by_id_and_org(
    self,
    photo_id: UUID,
    organization_id: UUID,
  ) -> SitePhoto | None:
    result = await self.session.execute(
      select(SitePhoto)
      .where(
        SitePhoto.id == photo_id,
        SitePhoto.organization_id == organization_id,
      )
      .options(selectinload(SitePhoto.tags))
    )
    return result.scalar_one_or_none()

  async def get_by_whatsapp_message_id(
    self,
    whatsapp_message_id: UUID,
  ) -> SitePhoto | None:
    result = await self.session.execute(
      select(SitePhoto).where(
        SitePhoto.whatsapp_message_id == whatsapp_message_id,
      )
    )
    return result.scalar_one_or_none()

  async def list_by_org(
    self,
    organization_id: UUID,
    *,
    project_id: UUID | None = None,
    photo_date_from: date | None = None,
    photo_date_to: date | None = None,
    tag: str | None = None,
    unassigned_only: bool = False,
    skip: int = 0,
    limit: int = 100,
  ) -> list[SitePhoto]:
    query = (
      select(SitePhoto)
      .where(SitePhoto.organization_id == organization_id)
      .options(selectinload(SitePhoto.tags))
    )

    if project_id is not None:
      query = query.where(SitePhoto.project_id == project_id)
    if unassigned_only:                                 
      query = query.where(SitePhoto.project_id.is_(None))
    if photo_date_from is not None:
      query = query.where(SitePhoto.photo_date >= photo_date_from)
    if photo_date_to is not None:
      query = query.where(SitePhoto.photo_date <= photo_date_to)
    if tag is not None:
      query = query.join(PhotoTag).where(PhotoTag.tag == tag)

    query = (
      query.order_by(SitePhoto.created_at.desc())
      .offset(skip)
      .limit(limit)
    )

    result = await self.session.execute(query)
    return list(result.scalars().unique())

  async def update(
    self,
    photo: SitePhoto,
  ) -> SitePhoto:
    self.session.add(photo)
    await self.session.flush()
    return photo

class PhotoTagRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(
    self,
    tag: PhotoTag,
  ) -> PhotoTag:
    self.session.add(tag)
    await self.session.flush()
    return tag

  async def bulk_create(
    self,
    tags: list[PhotoTag],
  ) -> list[PhotoTag]:
    self.session.add_all(tags)
    await self.session.flush()
    return tags

  async def delete(
    self,
    tag: PhotoTag,
  ) -> None:
    await self.session.delete(tag)
    await self.session.flush()