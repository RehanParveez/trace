from __future__ import annotations
import asyncio
import hashlib
import hmac
from datetime import date, datetime, timezone
from io import BytesIO
from typing import Any
from uuid import UUID, uuid4
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import TraceException
from app.modules.identity.models import Organization
from app.modules.projects.models import ProjectStatus
from app.modules.projects.repository import ProjectRepository
from app.modules.subscriptions.service import SubscriptionService
from app.modules.whatsapp.models import PhotoTag, PhotoTagSource, SitePhoto, WhatsAppChannel, WhatsAppMessage, WhatsAppMessageStatus, WhatsAppMessageType
from app.modules.whatsapp.repository import PhotoTagRepository, SitePhotoRepository, WhatsAppChannelRepository, WhatsAppMessageRepository
from app.modules.whatsapp.schemas import ChannelConnectRequest, PhotoTagCreateRequest, SitePhotoAssignProjectRequest, SitePhotoUpdateRequest
from app.shared.storage import build_site_photo_storage_key, generate_presigned_url, upload_fileobj
from app.modules.whatsapp.tasks import process_whatsapp_photo_task

GRAPH_API_BASE = (
  f"https://graph.facebook.com/{settings.whatsapp_graph_api_version}"
)
MAX_QUICK_REPLY_PROJECTS = 3

class WhatsAppService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.channels = WhatsAppChannelRepository(session)
    self.messages = WhatsAppMessageRepository(session)
    self.photos = SitePhotoRepository(session)
    self.tags = PhotoTagRepository(session)
    self.projects = ProjectRepository(session)
    self.subscriptions = SubscriptionService(session)

  async def connect_channel(
    self,
    organization_id: UUID,
    payload: ChannelConnectRequest,
  ) -> WhatsAppChannel:
    existing = await self.channels.get_by_organization(organization_id)
    if existing is not None:
      raise TraceException(
        "This organization already has a connected WhatsApp channel.",
        status_code=409,
        code="WHATSAPP_CHANNEL_ALREADY_EXISTS",
      )

    conflicting = await self.channels.get_by_phone_number_id(
      payload.phone_number_id
    )
    if conflicting is not None:
      raise TraceException(
        "This WhatsApp phone number is already connected to another organization.",
        status_code=409,
        code="WHATSAPP_PHONE_NUMBER_ALREADY_CONNECTED",
      )

    channel = WhatsAppChannel(
      id=uuid4(),
      organization_id=organization_id,
      phone_number_id=payload.phone_number_id,
      business_account_id=payload.business_account_id,
      display_phone_number=payload.display_phone_number,
      access_token=payload.access_token,
      is_active=True,
    )

    channel = await self.channels.create(channel)
    await self.session.commit()
    return channel

  async def get_channel(
    self,
    organization_id: UUID,
  ) -> WhatsAppChannel:
    channel = await self.channels.get_by_organization(organization_id)
    if channel is None:
      raise TraceException(
        "No WhatsApp channel connected for this organization.",
        status_code=404,
        code="WHATSAPP_CHANNEL_NOT_FOUND",
      )
    return channel

  async def disconnect_channel(
    self,
    organization_id: UUID,
  ) -> None:
    channel = await self.get_channel(organization_id)
    channel.is_active = False
    await self.channels.update(channel)
    await self.session.commit()

  @staticmethod
  def verify_subscription_challenge(
    mode: str | None,
    verify_token: str | None,
  ) -> bool:
    return (
      mode == "subscribe"
      and verify_token is not None
      and hmac.compare_digest(
        verify_token, settings.whatsapp_webhook_verify_token
      )
    )

  @staticmethod
  def verify_signature(
    raw_body: bytes,
    signature_header: str | None,
  ) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
      return False

    expected = hmac.new(
      settings.whatsapp_app_secret.encode("utf-8"),
      raw_body,
      hashlib.sha256,
    ).hexdigest()

    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)

  async def handle_webhook_payload(self, payload: dict) -> None:
    for entry in payload.get("entry", []):
      for change in entry.get("changes", []):
        value = change.get("value", {})
        phone_number_id = value.get("metadata", {}).get("phone_number_id")
        if not phone_number_id:
          continue

        channel = await self.channels.get_by_phone_number_id(phone_number_id)
        if channel is None:
          continue

        for raw_message in value.get("messages", []):
          await self._handle_inbound_message(channel, raw_message)

  async def _handle_inbound_message(
    self,
    channel: WhatsAppChannel,
    raw_message: dict,
  ) -> None:
    wa_message_id = raw_message.get("id")
    if not wa_message_id:
      return

    message_type_raw = raw_message.get("type", "")

    if message_type_raw == "interactive":
      await self._handle_interactive_reply(raw_message)
      return

    from_phone_number = raw_message.get("from", "")
    timestamp = raw_message.get("timestamp")
    received_at = (
      datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
      if timestamp
      else datetime.now(timezone.utc)
    )

    if message_type_raw == "image":
      message_type = WhatsAppMessageType.IMAGE
      media_id = raw_message.get("image", {}).get("id")
      caption_text = raw_message.get("image", {}).get("caption")
    elif message_type_raw == "text":
      message_type = WhatsAppMessageType.TEXT
      media_id = None
      caption_text = raw_message.get("text", {}).get("body")
    else:
      message_type = WhatsAppMessageType.OTHER
      media_id = None
      caption_text = None

    message = WhatsAppMessage(
      id=uuid4(),
      organization_id=channel.organization_id,
      channel_id=channel.id,
      wa_message_id=wa_message_id,
      from_phone_number=from_phone_number,
      message_type=message_type,
      caption_text=caption_text,
      media_id=media_id,
      status=WhatsAppMessageStatus.RECEIVED,
      received_at=received_at,
      raw_payload=raw_message,
    )

    created = await self.messages.try_create(message)
    if created is None:
      return

    await self.session.commit()

    if message_type == WhatsAppMessageType.IMAGE:
      process_whatsapp_photo_task.apply_async(
        args=[str(created.id)], queue="whatsapp_priority"
      )
    else:
      created.status = WhatsAppMessageStatus.IGNORED
      await self.messages.update(created)
      await self.session.commit()

  async def _handle_interactive_reply(self, raw_message: dict) -> None:
    interactive = raw_message.get("interactive", {})
    button_reply = interactive.get("button_reply") or interactive.get("list_reply")
    if not button_reply:
      return

    context_id = raw_message.get("context", {}).get("id")
    if not context_id:
      return

    pending_message = await self.messages.get_by_prompt_wa_message_id(context_id)
    if pending_message is None:
      return
    if pending_message.status != WhatsAppMessageStatus.AWAITING_PROJECT_SELECTION:
      return

    try:
      project_uuid = UUID(button_reply.get("id", ""))
    except (ValueError, TypeError):
      return

    project = await self.projects.get_by_id_and_org(
      project_uuid, pending_message.organization_id
    )
    if project is None:
      return

    await self._finalize_photo_for_message(pending_message, project.id)

  async def _finalize_photo_for_message(
    self,
    message: WhatsAppMessage,
    project_id: UUID,
  ) -> None:
    photo = await self.photos.get_by_whatsapp_message_id(message.id)
    if photo is None:
      return

    photo.project_id = project_id
    await self.photos.update(photo)

    message.status = WhatsAppMessageStatus.PROCESSED
    message.processed_at = datetime.now(timezone.utc)
    await self.messages.update(message)

    await self.session.commit()

  async def process_photo_message(self, message_id: UUID) -> None:
    message = await self.messages.get_by_id(message_id)
    if message is None:
      return

    if message.status != WhatsAppMessageStatus.RECEIVED:
      return

    channel = await self.channels.get_by_organization(message.organization_id)
    if channel is None or not channel.is_active:
      message.status = WhatsAppMessageStatus.FAILED
      message.error_message = "WhatsApp channel is no longer connected."
      await self.messages.update(message)
      await self.session.commit()
      return

    try:
      await self.subscriptions.check_quota(
        message.organization_id, "site_photos"
      )
    except TraceException as exc:
      message.status = WhatsAppMessageStatus.FAILED
      message.error_message = str(exc)[:2000]
      await self.messages.update(message)
      await self.session.commit()
      return

    message.status = WhatsAppMessageStatus.MEDIA_DOWNLOADING
    await self.messages.update(message)
    await self.session.commit()

    try:
      media_bytes, mime_type = await _download_whatsapp_media(
        channel.access_token, message.media_id
      )
    except Exception as exc:
      message.status = WhatsAppMessageStatus.FAILED
      message.error_message = f"Media download failed: {exc}"[:2000]
      await self.messages.update(message)
      await self.session.commit()
      return

    try:
      extension = _extension_for_mime_type(mime_type)
      storage_key = build_site_photo_storage_key(message.organization_id, f"{message.id}{extension}",)
      await asyncio.to_thread(
        upload_fileobj, storage_key, BytesIO(media_bytes), mime_type
      )

      caption_parsed: dict[str, Any] = {}
      project_match: UUID | None = None
      photo_date: date | None = None

      if message.caption_text and await self._is_ai_enabled(
        message.organization_id
      ):
        caption_parsed = await _call_ollama_parse_caption(
         message.caption_text
        ) or {}

        photo_date = _parse_photo_date(
         caption_parsed.get("date")
        )
        project_name_guess = caption_parsed.get("project")
        
        if project_name_guess:
          project_match = await self._match_project_by_name(message.organization_id, project_name_guess,)
      existing_photo = await self.photos.get_by_whatsapp_message_id(message.id)

      if existing_photo is not None:
       message.status = WhatsAppMessageStatus.PROCESSED
       message.processed_at = datetime.now(timezone.utc)
       await self.messages.update(message)
       await self.session.commit()

       return

      photo = SitePhoto(
        id=uuid4(),
        organization_id=message.organization_id,
        project_id=project_match,
        whatsapp_message_id=message.id,
        storage_key=storage_key,
        sender_phone_number=message.from_phone_number,
        caption_raw=message.caption_text,
        caption_parsed=caption_parsed,
        location_text=caption_parsed.get("location"),
        photo_date=photo_date,
      )
      await self.photos.create(photo)
      await self.subscriptions.increment_usage(
        message.organization_id, "site_photos"
      )
    except Exception as exc:
      await self.session.rollback()
      message.status = WhatsAppMessageStatus.FAILED
      message.error_message = str(exc)[:2000]
      await self.messages.update(message)
      await self.session.commit()
      return

    if project_match is not None:
      message.status = WhatsAppMessageStatus.PROCESSED
      message.processed_at = datetime.now(timezone.utc)
      await self.messages.update(message)
      await self.session.commit()
    else:
      message.status = WhatsAppMessageStatus.AWAITING_PROJECT_SELECTION
      await self.messages.update(message)
      await self.session.commit()
      await self._send_project_disambiguation_prompt(channel, message)

  async def _is_ai_enabled(self, organization_id: UUID) -> bool:
    result = await self.session.execute(
      select(Organization.ai_enabled).where(
        Organization.id == organization_id
      )
    )
    return bool(result.scalar_one_or_none())

  async def _match_project_by_name(
    self,
    organization_id: UUID,
    name_guess: str,
  ) -> UUID | None:
    projects = await self.projects.list_by_org(organization_id)
    normalized_guess = name_guess.strip().lower()

    matches = [
      p for p in projects if p.name.strip().lower() == normalized_guess
    ]
    return matches[0].id if len(matches) == 1 else None

  async def _send_project_disambiguation_prompt(
    self,
    channel: WhatsAppChannel,
    message: WhatsAppMessage,
  ) -> None:
    projects = await self.projects.list_by_org(message.organization_id)
    active_projects = [
      p for p in projects if p.status == ProjectStatus.ACTIVE
    ][:MAX_QUICK_REPLY_PROJECTS]

    if not active_projects:
      return

    body = {
      "messaging_product": "whatsapp",
      "to": message.from_phone_number,
      "type": "interactive",
      "interactive": {
        "type": "button",
        "body": {"text": "Which project is this photo for?"},
        "action": {
          "buttons": [
            {
              "type": "reply",
              "reply": {
                "id": str(project.id),
                "title": project.name[:20],
              },
            }
            for project in active_projects
          ]
        },
      },
    }

    try:
      prompt_wa_message_id = await _send_whatsapp_message(
        channel.phone_number_id, channel.access_token, body
      )
    except Exception:
      return

    if prompt_wa_message_id:
      message.prompt_wa_message_id = prompt_wa_message_id
      await self.messages.update(message)
      await self.session.commit()

  async def list_photos(
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
    photos = await self.photos.list_by_org(
      organization_id,
      project_id=project_id,
      photo_date_from=photo_date_from,
      photo_date_to=photo_date_to,
      tag=tag,
      unassigned_only=unassigned_only,
      skip=skip,
      limit=limit,
    )
    for photo in photos:
      photo.photo_url = generate_presigned_url(photo.storage_key)
    return photos

  async def get_photo(
    self,
    organization_id: UUID,
    photo_id: UUID,
  ) -> SitePhoto:
    photo = await self.photos.get_by_id_and_org(photo_id, organization_id)
    if photo is None:
      raise TraceException(
        "Site photo not found.",
        status_code=404,
        code="SITE_PHOTO_NOT_FOUND",
      )
    photo.photo_url = generate_presigned_url(photo.storage_key)
    return photo

  async def assign_project(
    self,
    organization_id: UUID,
    photo_id: UUID,
    payload: SitePhotoAssignProjectRequest,
  ) -> SitePhoto:
    photo = await self.get_photo(organization_id, photo_id)

    project = await self.projects.get_by_id_and_org(
      payload.project_id, organization_id
    )
    if project is None:
      raise TraceException(
        "Project not found in this organization.",
        status_code=404,
        code="PROJECT_NOT_FOUND",
      )

    photo.project_id = project.id
    await self.photos.update(photo)
    await self.session.commit()
    return photo

  async def update_photo(
    self,
    organization_id: UUID,
    photo_id: UUID,
    payload: SitePhotoUpdateRequest,
  ) -> SitePhoto:
    photo = await self.get_photo(organization_id, photo_id)

    if payload.location_text is not None:
      photo.location_text = payload.location_text
    if payload.photo_date is not None:
      photo.photo_date = payload.photo_date

    await self.photos.update(photo)
    await self.session.commit()
    return photo

  async def add_tag(
    self,
    organization_id: UUID,
    photo_id: UUID,
    payload: PhotoTagCreateRequest,
) -> PhotoTag:
    photo = await self.get_photo(organization_id, photo_id)

    tag_value = payload.tag.strip()
    if not tag_value:
      raise TraceException(
        "Photo tag cannot be empty.",
        status_code=400,
        code="PHOTO_TAG_EMPTY",
      )
    tag = PhotoTag(
      id=uuid4(),
      site_photo_id=photo.id,
      tag=tag_value,
      source=PhotoTagSource.MANUAL,
    )
    tag = await self.tags.create(tag)
    await self.session.commit()
    return tag

  async def remove_tag(
    self,
    organization_id: UUID,
    photo_id: UUID,
    tag_id: UUID,
  ) -> None:
    photo = await self.get_photo(organization_id, photo_id)
    matching = next((t for t in photo.tags if t.id == tag_id), None)
    if matching is None:
      raise TraceException(
        "Tag not found on this photo.",
        status_code=404,
        code="PHOTO_TAG_NOT_FOUND",
      )
    await self.tags.delete(matching)
    await self.session.commit()
    
def _extension_for_mime_type(mime_type: str) -> str:
  mapping = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
  }
  return mapping.get(mime_type.lower(), ".jpg")

async def _download_whatsapp_media(
  access_token: str,
  media_id: str | None,
) -> tuple[bytes, str]:
  if not media_id:
    raise ValueError("Message has no media_id to download.")

  async with httpx.AsyncClient(
    timeout=settings.whatsapp_media_download_timeout_seconds
  ) as client:
    meta_response = await client.get(
      f"{GRAPH_API_BASE}/{media_id}",
      headers={"Authorization": f"Bearer {access_token}"},
    )
    meta_response.raise_for_status()
    meta_data = meta_response.json()
    media_url = meta_data["url"]
    mime_type = meta_data.get("mime_type", "image/jpeg")

    media_response = await client.get(
      media_url,
      headers={"Authorization": f"Bearer {access_token}"},
    )
    media_response.raise_for_status()
    return media_response.content, mime_type

async def _send_whatsapp_message(
  phone_number_id: str,
  access_token: str,
  body: dict,
) -> str | None:
  async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.post(
      f"{GRAPH_API_BASE}/{phone_number_id}/messages",
      headers={"Authorization": f"Bearer {access_token}"},
      json=body,
    )
    response.raise_for_status()
    messages = response.json().get("messages", [])
    return messages[0]["id"] if messages else None

def _parse_photo_date(
  value: Any,
) -> date | None:
  if not value:
    return None
  try:
    return date.fromisoformat(str(value))
  except (TypeError, ValueError):
    return None

async def _call_ollama_parse_caption(caption_text: str) -> dict | None:
  import json

  prompt = (
    "Extract structured information from this WhatsApp caption sent by a "
    "site engineer along with a construction site photo. The caption may "
    "mix English and Urdu. Respond with strict JSON only: "
    '{"project": "... or null", "location": "... or null", '
    '"date": "... or null", "notes": "..."}. Caption: ' + caption_text
  )
  try:
    async with httpx.AsyncClient(timeout=30.0) as client:
      response = await client.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
          "model": settings.ollama_model,
          "prompt": prompt,
          "stream": False,
          "format": "json",
        },
      )
      response.raise_for_status()
      return json.loads(response.json()["response"])
  except Exception:
    return None