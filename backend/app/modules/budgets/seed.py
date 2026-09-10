from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.identity.models import Organization
from app.modules.projects.models import Project
from app.modules.budgets.models import Budget, BudgetCategory
from uuid import uuid4
import asyncio
from decimal import Decimal
from app.core.database import AsyncSessionLocal

async def seed_budgets(session: AsyncSession) -> None:
  org = (
    await session.execute(
      select(Organization).order_by(Organization.created_at.asc()).limit(1)
    )
  ).scalar_one_or_none()
  if org is None:
    print("Skipping budgets seed: no organization exists.")
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
    print("Skipping budgets seed: no project exists.")
    return

  existing = (
    await session.execute(
      select(Budget).where(
        Budget.project_id == project.id,
        Budget.organization_id == org.id,
      )
    )
  ).scalar_one_or_none()

  if existing is not None:
    print(f"Budget already exists for project {project.code or project.name}.")
    return

  budget = Budget(
    id=uuid4(),
    organization_id=org.id,
    project_id=project.id,
    approved_amount=Decimal("12500000.00"),
    currency="PKR",
    notes="Approved construction budget for the seed project.",
  )
  session.add(budget)
  await session.flush()

  session.add_all(
    [
      BudgetCategory(
        id=uuid4(),
        budget_id=budget.id,
        name="Civil works",
        allocated_amount=Decimal("6500000.00"),
      ),
      BudgetCategory(
        id=uuid4(),
        budget_id=budget.id,
        name="MEP",
        allocated_amount=Decimal("3200000.00"),
      ),
      BudgetCategory(
        id=uuid4(),
        budget_id=budget.id,
        name="Finishes",
        allocated_amount=Decimal("1800000.00"),
      ),
      BudgetCategory(
        id=uuid4(),
        budget_id=budget.id,
        name="Contingency",
        allocated_amount=Decimal("1000000.00"),
      ),
    ]
  )
  await session.commit()
  print(f"Budgets seed completed for project {project.code or project.name}.")

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_budgets(session)

if __name__ == "__main__":
  asyncio.run(main())