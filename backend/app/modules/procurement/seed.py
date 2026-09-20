from __future__ import annotations
import asyncio
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.identity.models import Organization, User
from app.modules.projects.models import Project
from app.modules.procurement.models import ProcurementRequest, ProcurementStatus
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4
from app.core.database import AsyncSessionLocal
import asyncio
from app.shared.seed_utils import seed_module_permissions
from app.modules.procurement.permissions import PROCUREMENT_PERMISSIONS

PROCUREMENT_MATERIAL_POOL = [
  ("Cement OPC 43", "bags", (300, 800), (400_000, 950_000)),
  ("TMT Rebar 12mm", "tons", (5, 20), (750_000, 3_000_000)),
  ("Ready-mix Concrete M25", "m3", (30, 150), (350_000, 1_800_000)),
  ("Burnt Clay Bricks", "units", (5000, 20000), (125_000, 500_000)),
  ("Structural Steel Sections", "tons", (2, 10), (600_000, 3_000_000)),
  ("Sand (fine)", "m3", (50, 300), (75_000, 450_000)),
  ("Crushed Stone Aggregate", "m3", (50, 300), (100_000, 600_000)),
]

STATUS_WEIGHTS = [
  (ProcurementStatus.REQUESTED, 35),
  (ProcurementStatus.APPROVED, 25),
  (ProcurementStatus.ORDERED, 20),
  (ProcurementStatus.RECEIVED, 15),
  (ProcurementStatus.CANCELLED, 5),
]

def _random_procurement_requests(
  *,
  organization_id,
  project_id,
  requested_by,
  count: int,
) -> list[ProcurementRequest]:
  today = date.today()
  chosen = random.sample(
    PROCUREMENT_MATERIAL_POOL, k=min(count, len(PROCUREMENT_MATERIAL_POOL))
  )
  statuses, weights = zip(*STATUS_WEIGHTS)
  requests = []
  for material_name, unit, quantity_range, amount_range in chosen:
    requests.append(
      ProcurementRequest(
        id=uuid4(),
        organization_id=organization_id,
        project_id=project_id,
        material_name=material_name,
        quantity=Decimal(random.randint(*quantity_range)),
        unit=unit,
        estimated_amount=Decimal(random.randint(*amount_range)).quantize(Decimal("0.01")),
        status=random.choices(statuses, weights=weights, k=1)[0],
        needed_by_date=today + timedelta(days=random.randint(-5, 21)),
        notes=random.choice([None, "Seed-generated sample request."]),
        requested_by=requested_by,
      )
    )
  return requests

async def seed_procurement(session: AsyncSession) -> None:
  await seed_module_permissions(session, PROCUREMENT_PERMISSIONS)
  org = (
    await session.execute(
      select(Organization).order_by(Organization.created_at.asc()).limit(1)
    )
  ).scalar_one_or_none()
  if org is None:
    print("Skipping procurement seed: no organization exists.")
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
    print("Skipping procurement seed: no project exists.")
    return

  user = (
    await session.execute(
      select(User)
      .where(User.organization_id == org.id)
      .order_by(User.created_at.asc())
      .limit(1)
    )
  ).scalar_one_or_none()

  samples = _random_procurement_requests(
    organization_id=org.id,
    project_id=project.id,
    requested_by=user.id if user else None,
    count=random.randint(1, 3),
  )
  session.add_all(samples)
  await session.commit()
  print(
    f"Procurement seed added {len(samples)} request(s) "
    f"for project {project.code or project.name}."
  )

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_procurement(session)

if __name__ == "__main__":
  asyncio.run(main())