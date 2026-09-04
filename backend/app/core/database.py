from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase
from collections.abc import AsyncGenerator
from app.core.config import settings

class Base(DeclarativeBase):
  pass

engine = create_async_engine(
  settings.database_url,
  echo=settings.debug,
  pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
  bind=engine,
  class_=AsyncSession,
  expire_on_commit=False,
)

worker_engine = create_async_engine(
  settings.database_url,
  echo=settings.debug,
  poolclass=NullPool,
)
WorkerSessionLocal = async_sessionmaker(
  bind=worker_engine,
  class_=AsyncSession,
  expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
  async with AsyncSessionLocal() as session:
    yield session

async def dispose_engine() -> None:
  await engine.dispose()
  
async def dispose_worker_engine() -> None:
  await worker_engine.dispose()