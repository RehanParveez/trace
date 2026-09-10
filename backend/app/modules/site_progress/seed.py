from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.identity.models import Organization, User
from app.modules.projects.models import Project
from app.modules.site_progress.models import SiteLogEntry
from uuid import uuid4
from datetime import date, timedelta
from app.core.database import AsyncSessionLocal
import asyncio

async def seed_site_progress(session: AsyncSession) -> None:
  org = (
    await session.execute(
      select(Organization).order_by(Organization.created_at.asc()).limit(1)
    )
  ).scalar_one_or_none()
  if org is None:
    print("Skipping site_progress seed: no organization exists.")
    return

  project = (
    await session.execute(
      select(Project)
      .where(Project.organization_id == org.id)
      .order_by(Project.created_at.asc())
      .limit(1)
    )
  ).scalar_one_or_none()
  if project is None:
    print("Skipping site_progress seed: no project exists.")
    return

  user = (
    await session.execute(
      select(User)
      .where(User.organization_id == org.id)
      .order_by(User.created_at.asc())
      .limit(1)
    )
  ).scalar_one_or_none()

  existing_count = (
    await session.execute(
      select(SiteLogEntry).where(
        SiteLogEntry.project_id == project.id,
        SiteLogEntry.organization_id == org.id,
      )
    )
  ).scalars().all()
  if existing_count:
    print(f"Site logs already exist for project {project.code or project.name}.")
    return

  today = date.today()
  samples = [
    SiteLogEntry(
      id=uuid4(),
      organization_id=org.id,
      project_id=project.id,
      log_date=today - timedelta(days=2),
      workforce_count=28,
      weather="Clear, 32°C",
      blockers=None,
      notes="Foundation formwork completed on grid A–C.",
      created_by=user.id if user else None,
    ),
    SiteLogEntry(
      id=uuid4(),
      organization_id=org.id,
      project_id=project.id,
      log_date=today - timedelta(days=1),
      workforce_count=34,
      weather="Partly cloudy",
      blockers="Steel delivery delayed until afternoon.",
      notes="Rebar placement ongoing; concrete pour scheduled tomorrow.",
      created_by=user.id if user else None,
    ),
    SiteLogEntry(
      id=uuid4(),
      organization_id=org.id,
      project_id=project.id,
      log_date=today,
      workforce_count=40,
      weather="Clear",
      blockers=None,
      notes="Slab pour completed for level 1. Curing in progress.",
      created_by=user.id if user else None,
    ),
  ]
  session.add_all(samples)
  await session.commit()
  print(f"Site progress seed completed ({len(samples)} logs) for project {project.code or project.name}.")

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_site_progress(session)

if __name__ == "__main__":
  asyncio.run(main())