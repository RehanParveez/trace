from __future__ import annotations
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

async def seed_procurement(session: AsyncSession) -> None:
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

  existing = (
    await session.execute(
      select(ProcurementRequest).where(
        ProcurementRequest.project_id == project.id,
        ProcurementRequest.organization_id == org.id,
      )
    )
  ).scalars().all()
  if existing:
    print(f"Procurement requests already exist for project {project.code or project.name}.")
    return

  today = date.today()
  samples = [
    ProcurementRequest(
      id=uuid4(),
      organization_id=org.id,
      project_id=project.id,
      material_name="Cement OPC 43",
      quantity=Decimal("500"),
      unit="bags",
      estimated_amount=Decimal("575000.00"),
      status=ProcurementStatus.REQUESTED,
      needed_by_date=today + timedelta(days=7),
      notes="For foundation and slab pours.",
      requested_by=user.id if user else None,
    ),
    ProcurementRequest(
      id=uuid4(),
      organization_id=org.id,
      project_id=project.id,
      material_name="TMT Rebar 12mm",
      quantity=Decimal("12.5"),
      unit="tons",
      estimated_amount=Decimal("1875000.00"),
      status=ProcurementStatus.APPROVED,
      needed_by_date=today + timedelta(days=5),
      notes="Approved by PM.",
      requested_by=user.id if user else None,
    ),
    ProcurementRequest(
      id=uuid4(),
      organization_id=org.id,
      project_id=project.id,
      material_name="Ready-mix Concrete M25",
      quantity=Decimal("80"),
      unit="m3",
      estimated_amount=Decimal("960000.00"),
      status=ProcurementStatus.ORDERED,
      needed_by_date=today + timedelta(days=3),
      notes=None,
      requested_by=user.id if user else None,
    ),
  ]
  session.add_all(samples)
  await session.commit()
  print(f"Procurement seed completed ({len(samples)} requests) for project {project.code or project.name}.")

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_procurement(session)

if __name__ == "__main__":
  asyncio.run(main())