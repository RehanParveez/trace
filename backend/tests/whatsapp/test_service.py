from __future__ import annotations
import hashlib
import hmac
from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
from app.core.exceptions import TraceException
from app.modules.projects.models import ProjectStatus
from app.modules.whatsapp.models import PhotoTag, PhotoTagSource, WhatsAppMessageStatus, WhatsAppMessageType
from app.modules.whatsapp.schemas import ChannelConnectRequest, PhotoTagCreateRequest, SitePhotoAssignProjectRequest, SitePhotoUpdateRequest
from app.modules.whatsapp.service import WhatsAppService, _parse_photo_date, _extension_for_mime_type

@pytest.mark.asyncio
async def test_connect_channel_creates_new(
  whatsapp_service,
  organization,
  whatsapp_admin_context,
):
  payload = ChannelConnectRequest(
    phone_number_id="pn-new-1",
    business_account_id="biz-1",
    access_token="tok-1",
    display_phone_number="+9230062085405",
  )
  with patch.object(whatsapp_service.audit, "log", new_callable=AsyncMock):
    channel = await whatsapp_service.connect_channel(
      organization.id, payload, whatsapp_admin_context.user.id
    )
  assert channel.phone_number_id == "pn-new-1"
  assert channel.is_active is True
  assert channel.organization_id == organization.id

@pytest.mark.asyncio
async def test_connect_channel_rejects_active_duplicate(
  whatsapp_service,
  organization,
  make_whatsapp_channel,
  whatsapp_admin_context,
):
  await make_whatsapp_channel(organization=organization, is_active=True)
  payload = ChannelConnectRequest(
    phone_number_id="any", business_account_id="b", access_token="t"
  )
  with pytest.raises(TraceException) as exc:
    await whatsapp_service.connect_channel(
      organization.id, payload, whatsapp_admin_context.user.id
    )
  assert exc.value.status_code == 409
  assert exc.value.code == "WHATSAPP_CHANNEL_ALREADY_EXISTS"

@pytest.mark.asyncio
async def test_connect_channel_rejects_phone_owned_by_other_org(
  whatsapp_service,
  organization,
  other_organization,
  make_whatsapp_channel,
  whatsapp_admin_context,
):
  await make_whatsapp_channel(
    organization=other_organization, phone_number_id="shared-phone"
  )
  payload = ChannelConnectRequest(
    phone_number_id="shared-phone", business_account_id="b", access_token="t"
  )
  with pytest.raises(TraceException) as exc:
    await whatsapp_service.connect_channel(
      organization.id, payload, whatsapp_admin_context.user.id
    )
  assert exc.value.code == "WHATSAPP_PHONE_NUMBER_ALREADY_CONNECTED"

@pytest.mark.asyncio
async def test_connect_channel_reactivates_inactive(
  whatsapp_service,
  organization,
  make_whatsapp_channel,
  whatsapp_admin_context,
):
  existing = await make_whatsapp_channel(
    organization=organization, phone_number_id="reactivate-me", is_active=False
  )
  payload = ChannelConnectRequest(
    phone_number_id="reactivate-me",
    business_account_id="new-biz",
    access_token="new-token",
    display_phone_number="++9230062085405",
  )
  with patch.object(whatsapp_service.audit, "log", new_callable=AsyncMock):
    channel = await whatsapp_service.connect_channel(
      organization.id, payload, whatsapp_admin_context.user.id
    )
  assert channel.id == existing.id
  assert channel.is_active is True
  assert channel.access_token == "new-token"

@pytest.mark.asyncio
async def test_get_channel_not_found(whatsapp_service, organization):
  with pytest.raises(TraceException) as exc:
    await whatsapp_service.get_channel(organization.id)
  assert exc.value.status_code == 404
  assert exc.value.code == "WHATSAPP_CHANNEL_NOT_FOUND"

@pytest.mark.asyncio
async def test_disconnect_channel(
  whatsapp_service,
  organization,
  make_whatsapp_channel,
  whatsapp_admin_context,
  db_session,
):
  channel = await make_whatsapp_channel(organization=organization, is_active=True)
  with patch.object(whatsapp_service.audit, "log", new_callable=AsyncMock):
    await whatsapp_service.disconnect_channel(
      organization.id, whatsapp_admin_context.user.id
    )
  await db_session.refresh(channel)
  refreshed = await whatsapp_service.channels.get_by_organization(organization.id)
  assert refreshed is not None
  assert refreshed.is_active is False

def test_verify_subscription_challenge(monkeypatch):
  monkeypatch.setattr(
    "app.modules.whatsapp.service.settings.whatsapp_webhook_verify_token",
    "secret-token",
  )
  assert WhatsAppService.verify_subscription_challenge("subscribe", "secret-token") is True
  assert WhatsAppService.verify_subscription_challenge("subscribe", "wrong") is False
  assert WhatsAppService.verify_subscription_challenge("not-subscribe", "secret-token") is False

def test_verify_signature(monkeypatch):
  secret = "app-secret"
  monkeypatch.setattr(
    "app.modules.whatsapp.service.settings.whatsapp_app_secret", secret
  )
  body = b'{"entry":[]}'
  expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
  assert WhatsAppService.verify_signature(body, f"sha256={expected}") is True
  assert WhatsAppService.verify_signature(body, None) is False
  assert WhatsAppService.verify_signature(body, "sha256=deadbeef") is False
  assert WhatsAppService.verify_signature(body, "md5=whatever") is False

@pytest.mark.asyncio
async def test_process_photo_skips_when_status_not_received(
  whatsapp_service,
  organization,
  make_whatsapp_channel,
  make_whatsapp_message,
):
  channel = await make_whatsapp_channel(organization=organization)
  msg = await make_whatsapp_message(
    organization=organization,
    channel=channel,
    status=WhatsAppMessageStatus.PROCESSED,
  )
  await whatsapp_service.process_photo_message(msg.id)

@pytest.mark.asyncio
async def test_process_photo_fails_when_channel_inactive(
  whatsapp_service,
  organization,
  make_whatsapp_channel,
  make_whatsapp_message,
  db_session,
):
  channel = await make_whatsapp_channel(organization=organization, is_active=False)
  msg = await make_whatsapp_message(organization=organization, channel=channel)
  await whatsapp_service.process_photo_message(msg.id)
  await db_session.refresh(msg)
  assert msg.status == WhatsAppMessageStatus.FAILED
  assert "no longer connected" in (msg.error_message or "")

@pytest.mark.asyncio
async def test_process_photo_quota_rejection(
  whatsapp_service,
  organization,
  make_whatsapp_channel,
  make_whatsapp_message,
  db_session,
):
  channel = await make_whatsapp_channel(organization=organization)
  msg = await make_whatsapp_message(organization=organization, channel=channel)

  with patch.object(
    whatsapp_service.subscriptions,
    "check_quota",
    new_callable=AsyncMock,
    side_effect=TraceException("quota exceeded", 403, "QUOTA_EXCEEDED"),
  ):
    await whatsapp_service.process_photo_message(msg.id)

  await db_session.refresh(msg)
  assert msg.status == WhatsAppMessageStatus.FAILED

@pytest.mark.asyncio
async def test_process_photo_happy_path_project_matched(
  whatsapp_service,
  organization,
  make_whatsapp_channel,
  make_whatsapp_message,
  project_factory,
  db_session,
):
  channel = await make_whatsapp_channel(organization=organization)
  project = await project_factory(status=ProjectStatus.ACTIVE, name="Alpha Tower")
  msg = await make_whatsapp_message(
    organization=organization,
    channel=channel,
    caption_text="Alpha Tower – foundation",
  )

  media_bytes = b"fake-jpeg-bytes"
  with (
    patch("app.modules.whatsapp.service._download_whatsapp_media", new_callable=AsyncMock, return_value=(media_bytes, "image/jpeg")),
    patch("app.modules.whatsapp.service.upload_fileobj"),
    patch("app.modules.whatsapp.service.build_site_photo_storage_key", return_value=f"{organization.id}/photos/{msg.id}.jpg"),
    patch.object(whatsapp_service, "_is_ai_enabled", new_callable=AsyncMock, return_value=True),
    patch("app.modules.whatsapp.service._parse_caption", new_callable=AsyncMock, return_value={"project": "Alpha Tower", "location": "foundation"}),
    patch.object(whatsapp_service.subscriptions, "check_quota", new_callable=AsyncMock),
    patch.object(whatsapp_service.subscriptions, "increment_usage_many", new_callable=AsyncMock),
    patch.object(whatsapp_service, "_send_project_disambiguation_prompt", new_callable=AsyncMock) as mock_prompt,
  ):
    await whatsapp_service.process_photo_message(msg.id)

  await db_session.refresh(msg)
  assert msg.status == WhatsAppMessageStatus.PROCESSED
  mock_prompt.assert_not_awaited()

  photo = await whatsapp_service.photos.get_by_whatsapp_message_id(msg.id, organization.id)
  assert photo is not None
  assert photo.project_id == project.id
  assert photo.is_ai_tagged is True

@pytest.mark.asyncio
async def test_process_photo_no_match_sets_awaiting_and_sends_prompt(
  whatsapp_service,
  organization,
  make_whatsapp_channel,
  make_whatsapp_message,
  db_session,
):
  channel = await make_whatsapp_channel(organization=organization)
  msg = await make_whatsapp_message(organization=organization, channel=channel)

  with (
    patch("app.modules.whatsapp.service._download_whatsapp_media", new_callable=AsyncMock, return_value=(b"img", "image/jpeg")),
    patch("app.modules.whatsapp.service.upload_fileobj"),
    patch("app.modules.whatsapp.service.build_site_photo_storage_key", return_value="key.jpg"),
    patch.object(whatsapp_service, "_is_ai_enabled", new_callable=AsyncMock, return_value=False),
    patch.object(whatsapp_service.subscriptions, "check_quota", new_callable=AsyncMock),
    patch.object(whatsapp_service.subscriptions, "increment_usage_many", new_callable=AsyncMock),
    patch.object(whatsapp_service, "_send_project_disambiguation_prompt", new_callable=AsyncMock) as mock_prompt,
  ):
    await whatsapp_service.process_photo_message(msg.id)
  await db_session.refresh(msg)
  assert msg.status == WhatsAppMessageStatus.AWAITING_PROJECT_SELECTION
  mock_prompt.assert_awaited_once()

@pytest.mark.asyncio
async def test_interactive_reply_assigns_project(
  whatsapp_service,
  organization,
  make_whatsapp_channel,
  make_whatsapp_message,
  make_site_photo,
  project_factory,
  db_session,
):
  channel = await make_whatsapp_channel(organization=organization)
  project = await project_factory(status=ProjectStatus.ACTIVE)
  pending = await make_whatsapp_message(
    organization=organization,
    channel=channel,
    status=WhatsAppMessageStatus.AWAITING_PROJECT_SELECTION,
    prompt_wa_message_id="prompt-wamid-1",
  )
  photo = await make_site_photo(
    organization=organization, whatsapp_message_id=pending.id
  )

  interactive = await make_whatsapp_message(
    organization=organization,
    channel=channel,
    message_type=WhatsAppMessageType.INTERACTIVE,
    raw_payload={
      "interactive": {"button_reply": {"id": str(project.id)}},
      "context": {"id": "prompt-wamid-1"},
    },
  )

  await whatsapp_service._handle_interactive_reply(interactive)

  await db_session.refresh(photo)
  await db_session.refresh(pending)
  assert photo.project_id == project.id
  assert pending.status == WhatsAppMessageStatus.PROCESSED

@pytest.mark.asyncio
async def test_assign_project(
  whatsapp_service,
  organization,
  make_site_photo,
  project_factory,
  whatsapp_admin_context,
):
  photo = await make_site_photo(organization=organization)
  project = await project_factory()
  payload = SitePhotoAssignProjectRequest(project_id=project.id)

  with (
    patch.object(whatsapp_service.audit, "log", new_callable=AsyncMock),
    patch("app.modules.whatsapp.service.generate_presigned_url", return_value="https://cdn/test.jpg"),
  ):
    result = await whatsapp_service.assign_project(
      organization.id, photo.id, payload, whatsapp_admin_context.user.id
    )
  assert result.project_id == project.id

@pytest.mark.asyncio
async def test_add_tag_rejects_duplicate(
  whatsapp_service,
  organization,
  make_site_photo,
  whatsapp_admin_context,
  db_session,
):
  photo = await make_site_photo(organization=organization)
  tag = PhotoTag(
    id=uuid4(),
    organization_id=organization.id,
    site_photo_id=photo.id,
    tag="foundation",
    source=PhotoTagSource.MANUAL,
  )
  db_session.add(tag)
  await db_session.flush()
  photo = await whatsapp_service.photos.get_by_id_and_org(photo.id, organization.id)

  with pytest.raises(TraceException) as exc:
    await whatsapp_service.add_tag(
      organization.id,
      photo.id,
      PhotoTagCreateRequest(tag="foundation"),
      whatsapp_admin_context.user.id,
    )
  assert exc.value.code == "PHOTO_TAG_ALREADY_EXISTS"

@pytest.mark.asyncio
async def test_add_tag_success(
  whatsapp_service,
  organization,
  make_site_photo,
  whatsapp_admin_context,
):
  photo = await make_site_photo(organization=organization)
  with patch.object(whatsapp_service.audit, "log", new_callable=AsyncMock):
    result = await whatsapp_service.add_tag(
      organization.id,
      photo.id,
      PhotoTagCreateRequest(tag="rebar"),
      whatsapp_admin_context.user.id,
    )
  assert result.tag == "rebar"
  assert result.source == PhotoTagSource.MANUAL

@pytest.mark.asyncio
async def test_update_photo_partial(
  whatsapp_service,
  organization,
  make_site_photo,
  whatsapp_admin_context,
):
  photo = await make_site_photo(
    organization=organization, location_text="old", photo_date=date(2025, 1, 1)
  )
  payload = SitePhotoUpdateRequest(
    location_text="new location", photo_date=date(2026, 3, 15)
  )
  with (
    patch.object(whatsapp_service.audit, "log", new_callable=AsyncMock),
    patch("app.modules.whatsapp.service.generate_presigned_url", return_value="https://cdn/x.jpg"),
  ):
    result = await whatsapp_service.update_photo(
      organization.id, photo.id, payload, whatsapp_admin_context.user.id
    )
  assert result.location_text == "new location"
  assert result.photo_date == date(2026, 3, 15)

def test_extension_for_mime_type():
  assert _extension_for_mime_type("image/jpeg") == ".jpg"
  assert _extension_for_mime_type("image/png") == ".png"
  with pytest.raises(ValueError):
    _extension_for_mime_type("application/pdf")

def test_parse_photo_date():
  assert _parse_photo_date("2026-09-19") == date(2026, 9, 19)
  assert _parse_photo_date(None) is None
  assert _parse_photo_date("not-a-date") is None