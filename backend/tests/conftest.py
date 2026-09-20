from __future__ import annotations
import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("DATABASE_URL", os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://trace:rehpostgre1@localhost:5441/trace_check",
  ),
)
os.environ.setdefault("MIGRATIONS_DATABASE_URL", os.environ["DATABASE_URL"])
os.environ.setdefault("REDIS_URL", "redis://localhost:6390/15")
os.environ.setdefault ("JWT_SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256",
)
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6390/14")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6390/14")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "trace")
os.environ.setdefault("MINIO_SECRET_KEY", "trace-dev-secret")
os.environ.setdefault("MINIO_BUCKET", "trace-check")
os.environ.setdefault("EMAIL_ENABLED", "false")
os.environ.setdefault("FRONTEND_BASE_URL", "http://localhost:5094")

import pytest
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from datetime import datetime, timezone
from app.core.config import settings
import pytest_asyncio
from sqlalchemy.pool import NullPool
from typing import Any
from uuid import uuid4
from httpx import ASGITransport, AsyncClient
from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.modules.identity.models import Organization, OrganizationMembership, Permission, Role, User
from app.main import app
from app.core.security import hash_password
from app.modules.identity.service import IdentityService
from app.modules.identity.token_store import IdentityTokenStore
from app.modules.identity.router import enforce_auth_rate_limit
from app.modules.organizations.service import OrganizationService
from app.modules.organizations.permissions import ORGANIZATION_PERMISSIONS
from app.modules.identity.enums import PermissionKey
from sqlalchemy import select
from sqlalchemy.orm.attributes import set_committed_value
from app.modules.subscriptions.models import Subscription, SubscriptionStatus, Plan, BillingInterval, UsageCounter, UsagePeriod
from datetime import timedelta
from decimal import Decimal
from app.modules.subscriptions.service import SubscriptionService
from app.modules.projects.models import Client, Project, ProjectMember, Milestone, ProjectStatus, ProjectMemberRole
from app.modules.projects.service import ProjectService
from datetime import date
from uuid import uuid4, UUID
from app.modules.whatsapp.models import SitePhoto, WhatsAppChannel, WhatsAppMessage, WhatsAppMessageStatus, WhatsAppMessageType
from app.modules.whatsapp.permissions import WHATSAPP_PERMISSIONS
from app.modules.whatsapp.service import WhatsAppService
from app.modules.verification.service import VerificationService
from app.modules.drawings_boq.models import BOQItem, BOQItemStatus, BOQVersion, BOQVersionStatus
from app.modules.verification.permissions import VERIFICATION_PERMISSIONS
from app.modules.verification.models import ProgressClaim, ProgressClaimStatus
from app.modules.notifications.service import NotificationService
from app.modules.notifications.permissions import NOTIFICATION_PERMISSIONS
from app.modules.notifications.models import NotificationType, Notification
from sqlalchemy.orm import selectinload
from app.modules.audit.service import AuditLogService
from app.modules.audit.models import AuditLog, AuditAction, AuditEntityType
from app.modules.audit.permissions import AUDIT_PERMISSIONS
from app.modules.ai_requests.permissions import AI_REQUEST_PERMISSIONS
from app.modules.ai_requests.service import AIOrchestratorService
from app.modules.budgets.service import BudgetService
from app.modules.budgets.models import Budget, BudgetCategory
from app.modules.budgets.permissions import BUDGET_PERMISSIONS

@pytest.fixture(scope="session")
def anyio_backend() -> str:
  return "asyncio"

@pytest_asyncio.fixture()
async def engine():
  eng = create_async_engine(
    settings.database_url,
    echo=False,
    poolclass=NullPool,
  )
  async with eng.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
  yield eng
  await eng.dispose()
  
@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
  connection = await engine.connect()
  transaction = await connection.begin()
  session_factory = async_sessionmaker(
    bind=connection,
    class_=AsyncSession,
    expire_on_commit=False,
    join_transaction_mode="create_savepoint",
  )
  session = session_factory()
  try:
    yield session
  finally:
    await session.close()
    await transaction.rollback()
    await connection.close()
class FakeRedis:
  def __init__(self) -> None:
    self._store: dict[str, tuple[str, float | None]] = {}
  async def set(self, key: str, value: str, ex: int | None = None) -> bool:
    expire_at = None
    if ex is not None:
      expire_at = datetime.now(timezone.utc).timestamp() + ex
    self._store[key] = (value, expire_at)
    return True
  async def get(self, key: str) -> str | None:
    item = self._store.get(key)
    if item is None:
      return None
    value, expire_at = item
    if expire_at is not None and datetime.now(timezone.utc).timestamp() > expire_at:
      del self._store[key]
      return None
    return value
  async def delete(self, *keys: str) -> int:
    count = 0
    for k in keys:
      if k in self._store:
        del self._store[k]
        count += 1
    return count

  async def eval(self, script: str, numkeys: int, *keys_and_args) -> Any:
    key = keys_and_args[0]
    value = await self.get(key)
    if value is not None:
      await self.delete(key)
    return value
  
  async def incr(self, key: str) -> int:
    raw = await self.get(key)
    val = int(raw or "0") + 1
    item = self._store.get(key)
    expire_at = item[1] if item else None
    self._store[key] = (str(val), expire_at)
    return val

  async def expire(self, key: str, seconds: int) -> bool:
   if key not in self._store:
    return False
   value, _ = self._store[key]
   self._store[key] = (
    value,
    datetime.now(timezone.utc).timestamp() + seconds,
   )
   return True

@pytest.fixture
def fake_redis() -> FakeRedis:
  return FakeRedis()

@pytest_asyncio.fixture
async def client(
  db_session: AsyncSession,
  fake_redis: FakeRedis,
) -> AsyncGenerator[AsyncClient, None]:
  async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    yield db_session
  async def _override_get_redis() -> AsyncGenerator[FakeRedis, None]:
    yield fake_redis
  async def _skip_rate_limit() -> None:
    return None
  app.dependency_overrides[get_db] = _override_get_db
  app.dependency_overrides[get_redis] = _override_get_redis
  app.dependency_overrides[enforce_auth_rate_limit] = _skip_rate_limit

  transport = ASGITransport(app=app)
  async with AsyncClient(transport=transport, base_url="http://test") as ac:
    yield ac
  app.dependency_overrides.clear()
  
@pytest_asyncio.fixture
async def make_organization(db_session: AsyncSession):
  async def _factory(
    *,
    name: str | None = None,
    slug: str | None = None,
    is_active: bool = True,
  ) -> Organization:
    org = Organization(
      id=uuid4(),
      name=name or f"Org {uuid4().hex[:8]}",
      slug=slug or f"org-{uuid4().hex[:8]}",
      is_active=is_active,
    )
    db_session.add(org)
    await db_session.flush()
    return org
  return _factory

@pytest_asyncio.fixture
async def make_role(db_session: AsyncSession):
  async def _factory(
    *,
    organization: Organization,
    name: str = "Company Admin",
    is_system: bool = True,
    permission_keys: list[str] | None = None,
  ) -> Role:
    role = Role(
      id=uuid4(),
      organization_id=organization.id,
      name=name,
      is_system=is_system,
    )
    if permission_keys:
      perms = []
      for key in permission_keys:
        p = Permission(id=uuid4(), key=key, description=key)
        db_session.add(p)
        perms.append(p)
      role.permissions = perms
    db_session.add(role)
    await db_session.flush()
    return role
  return _factory

@pytest_asyncio.fixture
async def user(
  organization,
  make_role,
  make_user,
  make_membership,
):
  role = await make_role(
    organization=organization,
    name="Member",
    is_system=False,
  )
  u = await make_user(
    organization=organization,
    role=role,
    email=f"member-{uuid4().hex[:6]}@example.com",
  )
  m = await make_membership(
    user=u,
    organization=organization,
    role=role,
    is_active=True,
  )
  u.active_membership = m
  return u

@pytest_asyncio.fixture
async def membership(user):
  return user.active_membership

@pytest_asyncio.fixture
async def make_user(db_session: AsyncSession):
  async def _factory(
    *,
    organization: Organization,
    role: Role,
    email: str | None = None,
    password: str = "admin12312!#1",
    is_active: bool = True,
    is_verified: bool = True,
    failed_login_attempts: int = 0,
    locked_until: datetime | None = None,
  ) -> User:
    user = User(
      id=uuid4(),
      organization_id=organization.id,
      role_id=role.id,
      email=(email or f"user-{uuid4().hex[:8]}@gmail.com").strip().lower(),
      password_hash=hash_password(password),
      first_name="Test",
      last_name="User",
      is_active=is_active,
      is_verified=is_verified,
      failed_login_attempts=failed_login_attempts,
      locked_until=locked_until,
    )
    db_session.add(user)
    await db_session.flush()
    return user
  return _factory

@pytest_asyncio.fixture
async def make_membership(db_session: AsyncSession):
  async def _factory(
    *,
    user: User,
    organization: Organization,
    role: Role,
    is_active: bool = True,
  ) -> OrganizationMembership:
    m = OrganizationMembership(
      id=uuid4(),
      user_id=user.id,
      organization_id=organization.id,
      role_id=role.id,
      is_active=is_active,
    )
    db_session.add(m)
    await db_session.flush()
    return m
  return _factory

@pytest_asyncio.fixture
async def organization(make_organization) -> Organization:
  return await make_organization(name="Check Org")

@pytest_asyncio.fixture
async def other_organization(make_organization) -> Organization:
  return await make_organization(name="Other Org")

@pytest_asyncio.fixture
async def identity_service(
  db_session: AsyncSession,
  fake_redis: FakeRedis,
) -> IdentityService:
  return IdentityService(
    session=db_session,
    token_store=IdentityTokenStore(fake_redis),
  )
  
@pytest_asyncio.fixture
async def seed_org_permissions(db_session: AsyncSession) -> dict[str, Permission]:
  existing = {}
  for key, description in ORGANIZATION_PERMISSIONS.items():
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
async def organization_service(
  db_session: AsyncSession,
) -> OrganizationService:
  return OrganizationService(session=db_session)

@pytest_asyncio.fixture
async def admin_context(
  db_session: AsyncSession,
  make_organization,
  make_role,
  make_user,
  make_membership,
  seed_org_permissions,
):
  org = await make_organization(name="Acme Test", slug=f"acme-{uuid4().hex[:6]}")
  perms = list(seed_org_permissions.values())

  role = await make_role(
    organization=org,
    name="Admin",
    is_system=True,
  )
  set_committed_value(role, "permissions", perms)
  await db_session.flush()

  user = await make_user(
    organization=org,
    role=role,
    email=f"admin-{uuid4().hex[:6]}@gmail.com",
    password="admin12312!#1",
    is_active=True,
    is_verified=True,
  )
  membership = await make_membership(
    user=user,
    organization=org,
    role=role,
    is_active=True,
  )
  user.active_membership = membership

  class Ctx:
    pass

  ctx = Ctx()
  ctx.organization = org
  ctx.role = role
  ctx.user = user
  ctx.membership = membership
  return ctx

@pytest_asyncio.fixture
async def member_context(
  db_session: AsyncSession,
  admin_context,
  make_role,
  make_user,
  make_membership,
  seed_org_permissions,
):
  org = admin_context.organization
  read_perm = seed_org_permissions[str(PermissionKey.ORGANIZATION_READ)]

  role = await make_role(
    organization=org,
    name="Viewer",
    is_system=False,
  )
  set_committed_value(role, "permissions", [read_perm])
  await db_session.flush()

  user = await make_user(
    organization=org,
    role=role,
    email=f"viewer-{uuid4().hex[:6]}@gmail.com",
    is_active=True,
    is_verified=True,
  )
  membership = await make_membership(
    user=user,
    organization=org,
    role=role,
    is_active=True,
  )
  user.active_membership = membership

  class Ctx:
    pass

  ctx = Ctx()
  ctx.organization = org
  ctx.role = role
  ctx.user = user
  ctx.membership = membership
  return ctx

@pytest_asyncio.fixture
async def make_plan(db_session: AsyncSession):
  async def _factory(
    *,
    name: str | None = None,
    slug: str | None = None,
    price_monthly: Decimal = Decimal("0"),
    price_yearly: Decimal = Decimal("0"),
    is_active: bool = True,
    is_public: bool = True,
    features: dict | None = None,
    quotas: dict | None = None,
  ) -> Plan:
    plan = Plan(
      id=uuid4(),
      name=name or f"Plan {uuid4().hex[:6]}",
      slug=slug or f"plan-{uuid4().hex[:8]}",
      description="Test plan",
      price_monthly=price_monthly,
      price_yearly=price_yearly,
      currency="PKR",
      is_active=is_active,
      is_public=is_public,
      features=features or {"projects": True, "site_logs": True},
      quotas=quotas or {
        "projects": 5,
        "storage_bytes": 1_073_741_824,
        "ai_requests": 50,
        "drawings": 10,
        "site_photos": 200,
      },
    )
    db_session.add(plan)
    await db_session.flush()
    return plan
  return _factory

@pytest_asyncio.fixture
async def make_subscription(db_session: AsyncSession, make_plan):
  async def _factory(
    *,
    organization: Organization,
    plan: Plan | None = None,
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
    billing_interval: BillingInterval = BillingInterval.MONTHLY,
    cancel_at_period_end: bool = False,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    started_at: datetime | None = None,
    trial_ends_at: datetime | None = None,
  ) -> Subscription:
    if plan is None:
      plan = await make_plan()
    now = datetime.now(timezone.utc)
    start = period_start or now
    end = period_end or (start + timedelta(days=30))
    sub = Subscription(
      id=uuid4(),
      organization_id=organization.id,
      plan_id=plan.id,
      status=status,
      billing_interval=billing_interval,
      started_at=started_at or start,
      current_period_start=start,
      current_period_end=end,
      trial_ends_at=trial_ends_at,
      cancel_at_period_end=cancel_at_period_end,
      provider="manual",
    )
    db_session.add(sub)
    await db_session.flush()
    await db_session.refresh(sub, attribute_names=["plan"])
    return sub
  return _factory

@pytest_asyncio.fixture
async def subscription_service(db_session) -> SubscriptionService:
  return SubscriptionService(session=db_session)

@pytest_asyncio.fixture
async def seeded_free_plan(make_plan):
    
  return await make_plan(
    name="Free",
    slug="free",
    quotas={
      "projects": 3,
      "storage_bytes": 1_073_741_824,
      "site_photos": 100,
      "drawings": 3,
      "ai_requests": 10,
    },
  )

@pytest_asyncio.fixture
async def make_usage_counter(db_session: AsyncSession):
  async def _factory(
    *,
    organization,
    metric: str,
    period_start: datetime,
    period_end: datetime,
    quantity: int = 0,
    period: UsagePeriod = UsagePeriod.MONTH,
  ) -> UsageCounter:
    counter = UsageCounter(
      id=uuid4(),
      organization_id=organization.id,
      metric=metric,
      period=period,
      period_start=period_start,
      period_end=period_end,
      quantity=quantity,
    )
    db_session.add(counter)
    await db_session.flush()
    return counter
  return _factory

@pytest.fixture
async def project_service(db_session: AsyncSession) -> ProjectService:
  return ProjectService(db_session)

@pytest.fixture
async def client_factory(db_session: AsyncSession, organization: Organization):
  async def _create(**kwargs) -> Client:
    data = {
      "id": uuid4(),
      "organization_id": organization.id,
      "name": f"Client-{uuid4().hex[:8]}",
      "contact_name": "Test Contact",
      "email": "client@example.com",
      "phone": "+1234567890",
      "address": "Test Address",
      "notes": "Test notes",
      **kwargs,
    }
    client = Client(**data)
    db_session.add(client)
    await db_session.flush()
    return client
  return _create

@pytest.fixture
async def project_factory(db_session: AsyncSession, organization: Organization, client_factory):
  async def _create(client: Client | None = None, **kwargs) -> Project:
    if client is None:
      client = await client_factory()
    data = {
      "id": uuid4(),
      "organization_id": organization.id,
      "client_id": client.id if client else None,
      "name": f"Project-{uuid4().hex[:8]}",
      "code": f"PRJ-{uuid4().hex[:6].upper()}",
      "description": "Test project",
      "location": "Test Location",
      "status": ProjectStatus.PLANNING,
      "start_date": date.today(),
      "expected_end_date": date.today() + timedelta(days=90),
      **kwargs,
    }
    project = Project(**data)
    db_session.add(project)
    await db_session.flush()
    return project
  return _create

@pytest.fixture
async def member_factory(db_session: AsyncSession, project_factory, user: User):
  async def _create(
    project: Project | None = None,
    target_user: User | None = None,
    role=ProjectMemberRole.MEMBER,
  ) -> ProjectMember:
    if project is None:
      project = await project_factory()
    if target_user is None:
      target_user = user
    member = ProjectMember(
      id=uuid4(),
      project_id=project.id,
      user_id=target_user.id,
      role=role,
    )
    db_session.add(member)
    await db_session.flush()
    await db_session.refresh(member, attribute_names=["user"])
    return member
  return _create

@pytest.fixture
async def milestone_factory(db_session: AsyncSession, project_factory):
  async def _create(project: Project | None = None, **kwargs) -> Milestone:
    if project is None:
      project = await project_factory()
    data = {
      "id": uuid4(),
      "project_id": project.id,
      "name": f"Milestone-{uuid4().hex[:6]}",
      "description": "Test milestone",
      "due_date": date.today() + timedelta(days=30),
      **kwargs,
    }
    ms = Milestone(**data)
    db_session.add(ms)
    await db_session.flush()
    return ms
  return _create

@pytest_asyncio.fixture
async def seed_whatsapp_permissions(db_session: AsyncSession) -> dict[str, Permission]:
  existing: dict[str, Permission] = {}
  for key, description in WHATSAPP_PERMISSIONS.items():
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
async def whatsapp_service(db_session: AsyncSession) -> WhatsAppService:
  return WhatsAppService(db_session)

@pytest_asyncio.fixture
async def make_whatsapp_channel(db_session: AsyncSession):
  async def _factory(
    *,
    organization: Organization,
    phone_number_id: str | None = None,
    business_account_id: str = "biz-acc-1",
    display_phone_number: str | None = "+923001234567",
    access_token: str = "test-access-token",
    is_active: bool = True,
  ) -> WhatsAppChannel:
    channel = WhatsAppChannel(
      id=uuid4(),
      organization_id=organization.id,
      phone_number_id=phone_number_id or f"phone-{uuid4().hex[:10]}",
      business_account_id=business_account_id,
      display_phone_number=display_phone_number,
      access_token=access_token,
      is_active=is_active,
    )
    db_session.add(channel)
    await db_session.flush()
    return channel
  return _factory

@pytest_asyncio.fixture
async def make_whatsapp_message(db_session: AsyncSession):
  async def _factory(
    *,
    organization: Organization,
    channel: WhatsAppChannel,
    message_type: WhatsAppMessageType = WhatsAppMessageType.IMAGE,
    status: WhatsAppMessageStatus = WhatsAppMessageStatus.RECEIVED,
    media_id: str | None = "media-123",
    caption_text: str | None = None,
    from_phone_number: str = "923009998877",
    wa_message_id: str | None = None,
    prompt_wa_message_id: str | None = None,
    raw_payload: dict | None = None,
    received_at: datetime | None = None,
  ) -> WhatsAppMessage:
    msg = WhatsAppMessage(
      id=uuid4(),
      organization_id=organization.id,
      channel_id=channel.id,
      wa_message_id=wa_message_id or f"wamid.{uuid4().hex}",
      from_phone_number=from_phone_number,
      message_type=message_type,
      caption_text=caption_text,
      media_id=media_id,
      status=status,
      received_at=received_at or datetime.now(timezone.utc),
      raw_payload=raw_payload or {},
      prompt_wa_message_id=prompt_wa_message_id,
    )
    db_session.add(msg)
    await db_session.flush()
    return msg
  return _factory

@pytest_asyncio.fixture
async def make_site_photo(db_session: AsyncSession):
  async def _factory(
    *,
    organization: Organization,
    project_id: UUID | None = None,
    whatsapp_message_id: UUID | None = None,
    storage_key: str | None = None,
    sender_phone_number: str | None = "923009998877",
    caption_raw: str | None = None,
    caption_parsed: dict | None = None,
    location_text: str | None = None,
    photo_date: date | None = None,
    is_ai_tagged: bool = False,
  ) -> SitePhoto:
    photo = SitePhoto(
      id=uuid4(),
      organization_id=organization.id,
      project_id=project_id,
      whatsapp_message_id=whatsapp_message_id,
      storage_key=storage_key or f"{organization.id}/photos/{uuid4().hex}.jpg",
      sender_phone_number=sender_phone_number,
      caption_raw=caption_raw,
      caption_parsed=caption_parsed or {},
      location_text=location_text,
      photo_date=photo_date or date.today(),
      is_ai_tagged=is_ai_tagged,
    )
    db_session.add(photo)
    await db_session.flush()
    return photo
  return _factory

@pytest_asyncio.fixture
async def whatsapp_admin_context(
  db_session: AsyncSession,
  make_organization,
  make_role,
  make_user,
  make_membership,
  seed_whatsapp_permissions,
  seed_org_permissions,
):
  org = await make_organization(name="WA Test Org", slug=f"wa-{uuid4().hex[:6]}")
  all_perms = list(seed_whatsapp_permissions.values()) + list(seed_org_permissions.values())
  role = await make_role(organization=org, name="WA Admin", is_system=True)
  set_committed_value(role, "permissions", all_perms)
  await db_session.flush()
  user = await make_user(
    organization=org,
    role=role,
    email=f"wa-admin-{uuid4().hex[:6]}@gmail.com",
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
  ctx.role = role
  ctx.user = user
  ctx.membership = membership
  return ctx

@pytest_asyncio.fixture
async def seed_verification_permissions(db_session) -> dict[str, Permission]:
  existing: dict[str, Permission] = {}
  for key, description in VERIFICATION_PERMISSIONS.items():
    key_str = str(key.value if hasattr(key, "value") else key)
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
async def verification_admin_context(
  db_session,
  make_organization,
  make_role,
  make_user,
  make_membership,
  seed_verification_permissions,
  seed_org_permissions,
):
  """User with full verification + org permissions."""
  org = await make_organization(name="Verif Org", slug=f"verif-{uuid4().hex[:6]}")
  all_perms = (
    list(seed_verification_permissions.values())
    + list(seed_org_permissions.values())
  )
  role = await make_role(organization=org, name="Verif Admin", is_system=True)
  set_committed_value(role, "permissions", all_perms)
  await db_session.flush()

  user = await make_user(
    organization=org,
    role=role,
    email=f"verif-admin-{uuid4().hex[:6]}@gmail.com",
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
  ctx.role = role
  ctx.user = user
  ctx.membership = membership
  return ctx

@pytest_asyncio.fixture
async def make_boq_version(db_session: AsyncSession):
  async def _factory(
    *,
    organization_id: UUID,
    project_id: UUID,
    drawing_id: UUID | None = None,
    label: str | None = None,
    status: BOQVersionStatus = BOQVersionStatus.ACTIVE,
    covered_area_sqft: Decimal | None = None,
    export_meta: dict | None = None,
  ) -> BOQVersion:
    version = BOQVersion(
      id=uuid4(),
      organization_id=organization_id,
      project_id=project_id,
      drawing_id=drawing_id,
      label=label or f"BOQ v{uuid4().hex[:4]}",
      status=status,
      covered_area_sqft=covered_area_sqft,
      export_meta=export_meta or {},
    )
    db_session.add(version)
    await db_session.flush()
    return version
  return _factory

@pytest_asyncio.fixture
async def make_boq_item(db_session, make_boq_version):
  async def _factory(
    *,
    organization_id: UUID,
    project_id: UUID,
    status: BOQItemStatus = BOQItemStatus.APPROVED,
    material_name: str = "Concrete C30",
    unit: str = "m3",
    category: str | None = "Structural",
    quantity: Decimal = Decimal("100.0000"),
  ) -> BOQItem:
    version = await make_boq_version(
      organization_id=organization_id,
      project_id=project_id,
    )
    item = BOQItem(
      id=uuid4(),
      organization_id=organization_id,
      boq_version_id=version.id,
      material_name=material_name,
      unit=unit,
      category=category,
      quantity=quantity,
      status=status,
    )
    db_session.add(item)
    await db_session.flush()
    return item
  return _factory

@pytest_asyncio.fixture
async def make_progress_claim(db_session):

  async def _factory(
    *,
    organization_id: UUID,
    project_id: UUID,
    boq_item_id: UUID,
    status: ProgressClaimStatus = ProgressClaimStatus.DRAFT,
    claimed_quantity: Decimal = Decimal("10.0000"),
    claimed_percentage: Decimal = Decimal("10.0000"),
    claim_date: date | None = None,
    version: int = 1,
    submitted_by: UUID | None = None,
    notes: str | None = None,
  ) -> ProgressClaim:
    claim = ProgressClaim(
      id=uuid4(),
      organization_id=organization_id,
      project_id=project_id,
      boq_item_id=boq_item_id,
      claim_date=claim_date or date.today(),
      claimed_quantity=claimed_quantity,
      claimed_percentage=claimed_percentage,
      notes=notes,
      status=status,
      version=version,
      submitted_by=submitted_by,
    )
    db_session.add(claim)
    await db_session.flush()
    return claim
  return _factory

@pytest_asyncio.fixture
async def verification_service(db_session) -> VerificationService:
  return VerificationService(db_session)

@pytest_asyncio.fixture
async def notification_service(
  db_session: AsyncSession,
) -> NotificationService:
  return NotificationService(db_session)

@pytest_asyncio.fixture
async def seed_notification_permissions(
  db_session: AsyncSession,
) -> dict[str, Permission]:
  existing: dict[str, Permission] = {}
  for key, description in NOTIFICATION_PERMISSIONS.items():
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
async def make_notification(
  db_session: AsyncSession,
):
  async def _factory(
    *,
    organization: Organization,
    user: User,
    type: NotificationType = NotificationType.MEMBER_JOINED,
    title: str = "Test notification",
    body: str | None = "Body",
    link_path: str | None = "/some/path",
    is_read: bool = False,
    read_at: datetime | None = None,
  ) -> Notification:
    n = Notification(
      id=uuid4(),
      organization_id=organization.id,
      user_id=user.id,
      type=type,
      title=title,
      body=body,
      link_path=link_path,
      is_read=is_read,
      read_at=read_at,
    )
    db_session.add(n)
    await db_session.flush()
    return n

  return _factory

@pytest_asyncio.fixture
async def notifications_admin_context(
  db_session: AsyncSession,
  make_organization,
  make_role,
  make_user,
  make_membership,
  seed_notification_permissions,
  seed_org_permissions,
):
  org = await make_organization(
    name="Notif Org",
    slug=f"notif-{uuid4().hex[:6]}",
  )
  all_perms = list(seed_notification_permissions.values()) + list(
    seed_org_permissions.values()
  )

  role = await make_role(
    organization=org,
    name="Notif Admin",
    is_system=True,
  )

  result = await db_session.execute(
    select(Role)
    .where(Role.id == role.id)
    .options(selectinload(Role.permissions))
  )
  role = result.scalar_one()
  role.permissions = list(all_perms)
  await db_session.flush()

  user = await make_user(
    organization=org,
    role=role,
    email=f"notif-admin-{uuid4().hex[:6]}@gmail.com",
    password="admin12312!#1",
    is_active=True,
    is_verified=True,
  )
  membership = await make_membership(
    user=user,
    organization=org,
    role=role,
    is_active=True,
  )
  user.active_membership = membership

  class Ctx:
    pass

  ctx = Ctx()
  ctx.organization = org
  ctx.role = role
  ctx.user = user
  ctx.membership = membership
  return ctx

@pytest_asyncio.fixture
async def seed_audit_permissions(db_session) -> dict[str, Permission]:
  existing: dict[str, Permission] = {}
  for key, description in AUDIT_PERMISSIONS.items():
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
async def audit_service(db_session) -> AuditLogService:
  return AuditLogService(db_session)

@pytest_asyncio.fixture
async def make_audit_log(db_session):
  async def _factory(
    *,
    organization: Organization,
    actor_user_id=None,
    entity_type: AuditEntityType = AuditEntityType.PROJECT,
    entity_id=None,
    action: AuditAction = AuditAction.CREATE,
    summary: str = "Test audit entry",
    changes: dict | None = None,
    ip_address: str | None = "127.0.0.1",
    created_at: datetime | None = None,
  ) -> AuditLog:
    entry = AuditLog(
      id=uuid4(),
      organization_id=organization.id,
      actor_user_id=actor_user_id,
      entity_type=entity_type,
      entity_id=entity_id or uuid4(),
      action=action,
      summary=summary,
      changes=changes or {},
      ip_address=ip_address,
    )
    if created_at is not None:
      entry.created_at = created_at
    db_session.add(entry)
    await db_session.flush()
    return entry
  return _factory

@pytest_asyncio.fixture
async def audit_admin_context(
  db_session,
  make_organization,
  make_role,
  make_user,
  make_membership,
  seed_audit_permissions,
  seed_org_permissions,
):
  org = await make_organization(name="Audit Test Org", slug=f"audit-{uuid4().hex[:6]}")
  all_perms = list(seed_audit_permissions.values()) + list(seed_org_permissions.values())
  role = await make_role(organization=org, name="Audit Admin", is_system=True)
  set_committed_value(role, "permissions", all_perms)
  await db_session.flush()
  user = await make_user(
    organization=org,
    role=role,
    email=f"audit-admin-{uuid4().hex[:6]}@example.com",
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
  ctx.role = role
  ctx.user = user
  ctx.membership = membership
  return ctx

@pytest_asyncio.fixture
async def audit_viewer_context(
  db_session,
  audit_admin_context,
  make_role,
  make_user,
  make_membership,
  seed_audit_permissions,
):
  org = audit_admin_context.organization
  read_perm = seed_audit_permissions[str(PermissionKey.AUDIT_LOG_READ)]
  role = await make_role(organization=org, name="Audit Viewer", is_system=False)
  set_committed_value(role, "permissions", [read_perm])
  await db_session.flush()
  user = await make_user(
    organization=org,
    role=role,
    email=f"audit-viewer-{uuid4().hex[:6]}@gmail.com",
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
  ctx.role = role
  ctx.user = user
  ctx.membership = membership
  return ctx

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
  org = await make_organization(name="AI Check Org", slug=f"ai-{uuid4().hex[:6]}")
  org.ai_enabled = True
  await db_session.flush()
  all_perms = list(seed_ai_permissions.values()) + list(seed_org_permissions.values())
  role = await make_role(organization=org, name="AI Admin", is_system=True)
  set_committed_value(role, "permissions", all_perms)
  await db_session.flush()
  user = await make_user(
    organization=org,
    role=role,
    email=f"ai-admin-{uuid4().hex[:6]}@gmail.com",
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
async def seed_budget_permissions(db_session: AsyncSession) -> dict[str, Permission]:
  existing: dict[str, Permission] = {}
  for key, description in BUDGET_PERMISSIONS.items():
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
async def budget_admin_context(
  db_session: AsyncSession,
  make_organization,
  make_role,
  make_user,
  make_membership,
  seed_budget_permissions,
  seed_org_permissions,
):
  org = await make_organization(
    name="Budget Org",
    slug=f"budget-{uuid4().hex[:6]}",
  )
  if not getattr(org, "currency", None):
    org.currency = "PKR"
    await db_session.flush()
  all_perms = (
    list(seed_budget_permissions.values())
    + list(seed_org_permissions.values())
  )
  role = await make_role(organization=org, name="Budget Admin", is_system=True)
  set_committed_value(role, "permissions", all_perms)
  await db_session.flush()
  user = await make_user(
    organization=org,
    role=role,
    email=f"budget-admin-{uuid4().hex[:6]}@gmail.com",
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
  ctx.role = role
  ctx.user = user
  ctx.membership = membership
  return ctx

@pytest_asyncio.fixture
async def budget_service(db_session: AsyncSession) -> BudgetService:
  return BudgetService(db_session)

@pytest_asyncio.fixture
async def make_budget(db_session: AsyncSession):
  async def _factory(
    *,
    organization: Organization,
    project: Project,
    approved_amount: Decimal = Decimal("1000000.00"),
    currency: str = "PKR",
    notes: str | None = None,
    version: int = 1,
    categories: list[tuple[str, Decimal]] | None = None,
  ) -> Budget:
    budget = Budget(
      id=uuid4(),
      organization_id=organization.id,
      project_id=project.id,
      approved_amount=approved_amount,
      currency=currency,
      notes=notes,
      version=version,
    )
    db_session.add(budget)
    await db_session.flush()
    if categories:
      for name, amount in categories:
        db_session.add(
          BudgetCategory(
            id=uuid4(),
            organization_id=organization.id,
            budget_id=budget.id,
            name=name,
            allocated_amount=amount,
          )
        )
      await db_session.flush()
    result = await db_session.execute(
      select(Budget)
      .where(Budget.id == budget.id)
      .options(selectinload(Budget.categories))
    )
    return result.scalar_one()
  return _factory