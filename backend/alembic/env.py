from __future__ import annotations
from logging.config import fileConfig
from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from app.core.config import settings
from app.core.database import Base
from app.modules.identity import models as identity_models
from app.modules.subscriptions import models as subscriptions_models
from app.modules.projects import models as projects_models
from app.modules.drawings_boq import models as drawings_boq_models
from app.modules.whatsapp import models as whatsapp_models
from app.modules.verification import models as verification_models
from app.modules.notifications import models as notifications_models
from app.modules.audit import models as audit_models
from app.modules.ai_requests import models as ai_requests_models
from app.modules.budgets import models as budgets_models
from app.modules.site_progress import models as site_progress_models
from app.modules.procurement import models as procurement_models
from app.modules.expenses import models as expenses_models
from app.modules.running_bills import models as running_models
from app.modules.labour import models as labour_models
from app.modules.subcontractors import models as subcontractors_models
from app.modules.withholding_tax import models as withholding_tax_models
from app.modules.material_stock import models as material_stock_models
from app.modules.retention import models as retention_models
from app.modules.change_orders import models as change_orders_models
from app.modules.scheduling import models as scheduling_models
from app.modules.punch_lists import models as punch_lists_models
from app.modules.sales_tax import models as sales_tax_models

config = context.config

if config.config_file_name is not None:
  fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
  url = settings.migrations_database_url
  context.configure(
    url=url,
    target_metadata=target_metadata,
    literal_binds=True,
    dialect_opts={"paramstyle": "named"},
    compare_type=True,
    compare_server_default=True,
  )
  with context.begin_transaction():
    context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
  context.configure(
    connection=connection,
    target_metadata=target_metadata,
    compare_type=True,
    compare_server_default=True,
  )
  with context.begin_transaction():
    context.run_migrations()

async def run_migrations_online() -> None:
  configuration = config.get_section(
    config.config_ini_section
  ) or {}

  configuration["sqlalchemy.url"] = settings.database_url
  connectable = async_engine_from_config(
    configuration,
    prefix="sqlalchemy.",
    poolclass=pool.NullPool,
  )

  async with connectable.connect() as connection:
    await connection.run_sync(
      do_run_migrations
    )

  await connectable.dispose()

if context.is_offline_mode():
  run_migrations_offline()
else:
  import asyncio

  asyncio.run(
    run_migrations_online()
  )