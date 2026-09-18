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
async def make_user(db_session: AsyncSession):
  async def _factory(
    *,
    organization: Organization,
    role: Role,
    email: str | None = None,
    password: str = "SecurePass123!",
    is_active: bool = True,
    is_verified: bool = True,
    failed_login_attempts: int = 0,
    locked_until: datetime | None = None,
  ) -> User:
    user = User(
      id=uuid4(),
      organization_id=organization.id,
      role_id=role.id,
      email=(email or f"user-{uuid4().hex[:8]}@example.com").strip().lower(),
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
async def identity_service(
  db_session: AsyncSession,
  fake_redis: FakeRedis,
) -> IdentityService:
  return IdentityService(
    session=db_session,
    token_store=IdentityTokenStore(fake_redis),
  )