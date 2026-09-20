from __future__ import annotations
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value
from app.core.config import settings
from app.modules.ai_requests.models import AIProvider, AIRequest, AIRequestPurpose, AIResponse, AIResponseStatus
from app.modules.ai_requests.permissions import AI_REQUEST_PERMISSIONS
from app.modules.ai_requests.service import AIOrchestratorService
from app.modules.identity.models import Permission
from app.modules.subscriptions.models import SubscriptionStatus

@pytest_asyncio.fixture
async def seed_ai_permissions(db_session: AsyncSession) -> dict[str, Permission]:
  existing: dict[str, Permission] = {}
  for key, description in AI_REQUEST_PERMISSIONS.items():
    key_str = str(key)
    result = await db_session.execute(
      select(Permission).where(Permission.key == key_str)
    )
    perm = result.scalar_one_or_none()
    if perm is None:
      perm = Permission(id=uuid4(), key=key_str, description=description)
      db_session.add(perm)
      await db_session.flush()
    existing[key_str] = perm
  return existing

@pytest_asyncio.fixture
async def ai_admin_context(
  db_session: AsyncSession,
  make_organization,
  make_role,
  make_user,
  make_membership,
  seed_ai_permissions,
  seed_org_permissions,
):
  org = await make_organization(name="AI Test Org", slug=f"ai-{uuid4().hex[:6]}")
  org.ai_enabled = True
  await db_session.flush()

  all_perms = list(seed_ai_permissions.values()) + list(seed_org_permissions.values())
  role = await make_role(organization=org, name="AI Admin", is_system=True)
  set_committed_value(role, "permissions", all_perms)
  await db_session.flush()

  user = await make_user(
    organization=org,
    role=role,
    email=f"ai-admin-{uuid4().hex[:6]}@example.com",
    password="admin12312!#1",
    is_active=True,
    is_verified=True,
  )
  membership = await make_membership(
    user=user, organization=org, role=role, is_active=True
  )
  user.active_membership = membership

  class Ctx:
    pass

  ctx = Ctx()
  ctx.organization = org
  ctx.user = user
  return ctx

@pytest_asyncio.fixture
async def ai_service(db_session: AsyncSession) -> AIOrchestratorService:
  return AIOrchestratorService(db_session)

@pytest_asyncio.fixture
async def active_subscription(
  make_plan,
  make_subscription,
  ai_admin_context,
):
  plan = await make_plan(
    quotas={"ai_requests": 100, "projects": 10, "storage_bytes": 1_737_418_24}
  )
  return await make_subscription(
    organization=ai_admin_context.organization,
    plan=plan,
    status=SubscriptionStatus.ACTIVE,
  )

@pytest.mark.asyncio
async def test_run_rejects_when_ai_disabled(
  db_session: AsyncSession,
  ai_service: AIOrchestratorService,
  ai_admin_context,
):
  org = ai_admin_context.organization
  org.ai_enabled = False
  await db_session.flush()

  result = await ai_service.run(
    organization_id=org.id,
    purpose=AIRequestPurpose.MATERIAL_NORMALIZATION,
    prompt="test",
  )
  assert result.success is False
  assert "AI is not enabled" in (result.error_message or "")

@pytest.mark.asyncio
async def test_run_success_persists_request_and_response(
  db_session: AsyncSession,
  ai_service: AIOrchestratorService,
  ai_admin_context,
  monkeypatch,
):
  org = ai_admin_context.organization
  monkeypatch.setattr(settings, "ai_provider", "OLLAMA")
  monkeypatch.setattr(settings, "ollama_model", "llama3.2")

  fake_raw = '{"ok": true}'
  fake_parsed = {"ok": True}

  with (
    patch.object(
      ai_service.subscriptions,
      "check_quota",
      new_callable=AsyncMock,
      return_value=None,
    ),
    patch.object(
      ai_service.subscriptions,
      "increment_usage",
      new_callable=AsyncMock,
      return_value=None,
    ),
    patch.object(
      AIOrchestratorService,
      "_call_provider",
      new_callable=AsyncMock,
      return_value=(fake_raw, fake_parsed),
    ),
  ):
    result = await ai_service.run(
      organization_id=org.id,
      purpose=AIRequestPurpose.MATERIAL_NORMALIZATION,
      prompt="normalize materials",
      requested_by=ai_admin_context.user.id,
    )
  assert result.success is True
  assert result.parsed_output == fake_parsed

  req = (
    await db_session.execute(
      select(AIRequest).where(AIRequest.organization_id == org.id)
    )
  ).scalars().one()
  assert req.purpose == AIRequestPurpose.MATERIAL_NORMALIZATION
  assert req.provider == AIProvider.OLLAMA

  resp = (
    await db_session.execute(
      select(AIResponse).where(AIResponse.ai_request_id == req.id)
    )
  ).scalars().one()
  assert resp.status == AIResponseStatus.SUCCEEDED
  assert resp.parsed_output == fake_parsed

@pytest.mark.asyncio
async def test_run_provider_failure_writes_failed_response(
  db_session: AsyncSession,
  ai_service: AIOrchestratorService,
  ai_admin_context,
  monkeypatch,
):
  org = ai_admin_context.organization
  monkeypatch.setattr(settings, "ai_provider", "OLLAMA")

  with (
    patch.object(
      ai_service.subscriptions,
      "check_quota",
      new_callable=AsyncMock,
      return_value=None,
    ),
    patch.object(
      ai_service.subscriptions,
      "increment_usage",
      new_callable=AsyncMock,
      return_value=None,
    ),
    patch.object(
      AIOrchestratorService,
      "_call_provider",
      new_callable=AsyncMock,
      side_effect=RuntimeError("provider down"),
    ),
  ):
    result = await ai_service.run(
      organization_id=org.id,
      purpose=AIRequestPurpose.CAPTION_PARSING,
      prompt="parse caption",
    )

  assert result.success is False
  assert "provider down" in (result.error_message or "")

  req = (
    await db_session.execute(
      select(AIRequest).where(AIRequest.organization_id == org.id)
    )
  ).scalars().one()

  resp = (
    await db_session.execute(
      select(AIResponse).where(AIResponse.ai_request_id == req.id)
    )
  ).scalars().one()
  assert resp.status == AIResponseStatus.FAILED
  assert "provider down" in (resp.error_message or "")

@pytest.mark.asyncio
async def test_get_usage_summary(
  db_session: AsyncSession,
  ai_service: AIOrchestratorService,
  ai_admin_context,
):
  org = ai_admin_context.organization

  for status, latency in [
    (AIResponseStatus.SUCCEEDED, 100),
    (AIResponseStatus.FAILED, 50),
  ]:
    req = AIRequest(
      id=uuid4(),
      organization_id=org.id,
      purpose=AIRequestPurpose.PHOTO_TAGGING,
      provider=AIProvider.OLLAMA,
      model="llama3.2",
      prompt_text="x",
    )
    db_session.add(req)
    await db_session.flush()
    db_session.add(
      AIResponse(
        id=uuid4(),
        organization_id=org.id,
        ai_request_id=req.id,
        status=status,
        latency_ms=latency,
      )
    )
  await db_session.flush()

  summary = await ai_service.get_usage_summary(org.id)

  assert summary["total_requests"] == 2
  assert summary["succeeded"] == 1
  assert summary["failed"] == 1
  assert summary["average_latency_ms"] is not None