from __future__ import annotations
import asyncio
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.modules.identity.models import Organization, User
from app.modules.projects.models import Project
from app.modules.site_progress.models import SiteLogEntry
from uuid import uuid4
from datetime import date, timedelta
from app.core.database import AsyncSessionLocal
import asyncio
from app.shared.seed_utils import seed_module_permissions
from app.modules.site_progress.permissions import SITE_PROGRESS_PERMISSIONS

WEATHER_POOL = [
  "Clear, 32°C", "Partly cloudy", "Overcast", "Light rain", "Hot, 38°C", "Clear",
]
BLOCKER_POOL = [
  None, None, None, 
  "Steel delivery delayed until afternoon.",
  "Concrete pump unavailable, rescheduled.",
  "Labour shortage due to local event.",
  "Awaiting client sign-off on drawing revision.",
]
NOTE_POOL = [
  "Foundation formwork progressing on schedule.",
  "Rebar placement ongoing; concrete pour scheduled next.",
  "Slab pour completed for this level. Curing in progress.",
  "Brickwork advancing on ground floor.",
  "Plumbing rough-in started in wet areas.",
  "Electrical conduit laid for first floor.",
  "Site cleared and ready for next phase.",
]

async def seed_site_progress(session: AsyncSession) -> None:
  await seed_module_permissions(session, SITE_PROGRESS_PERMISSIONS)
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

  latest_logged_date = await session.scalar(
    select(func.max(SiteLogEntry.log_date)).where(
      SiteLogEntry.project_id == project.id,
      SiteLogEntry.organization_id == org.id,
    )
  )
  start_date = (latest_logged_date + timedelta(days=1)) if latest_logged_date else date.today() - timedelta(days=2)
  entries_to_add = random.randint(1, 3)
  samples = []
  for offset in range(entries_to_add):
    log_date = start_date + timedelta(days=offset)
    samples.append(
      SiteLogEntry(
        id=uuid4(),
        organization_id=org.id,
        project_id=project.id,
        log_date=log_date,
        workforce_count=random.randint(15, 55),
        weather=random.choice(WEATHER_POOL),
        blockers=random.choice(BLOCKER_POOL),
        notes=random.choice(NOTE_POOL),
        created_by=user.id if user else None,
      )
    )
  session.add_all(samples)
  await session.commit()
  
  print(
    f"Site progress seed added {len(samples)} log(s) for project "
    f"{project.code or project.name}, dated {samples[0].log_date} through {samples[-1].log_date}."
  )
async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_site_progress(session)

if __name__ == "__main__":
  asyncio.run(main())