from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.identity.models import Organization
from app.modules.projects.models import Project
from app.modules.budgets.schemas import BudgetCategoryInput, BudgetSaveRequest
from app.modules.budgets.service import BudgetService
import asyncio
from decimal import Decimal
from app.core.database import AsyncSessionLocal
from app.shared.seed_utils import seed_module_permissions
from app.modules.budgets.permissions import BUDGET_PERMISSIONS
import random
from datetime import datetime, timezone

BUDGET_CATEGORY_POOL = [
  "Civil works", "MEP", "Finishes", "Contingency", "Structural steel",
  "Earthworks", "Electrical", "Plumbing", "HVAC", "Scaffolding",
]

def _random_budget_categories(total: Decimal) -> list[BudgetCategoryInput]:
  chosen = random.sample(BUDGET_CATEGORY_POOL, k=random.randint(3, 5))
  allocable = (
    total * Decimal(random.randint(70, 95)) / Decimal(100)
  ).quantize(Decimal("0.01"))
  weights = [random.random() for _ in chosen]
  weight_total = sum(weights)
  categories: list[BudgetCategoryInput] = []
  running = Decimal("0")
  for index, (name, weight) in enumerate(zip(chosen, weights)):
    if index == len(chosen) - 1:
      amount = (allocable - running).quantize(Decimal("0.01"))
    else:
      amount = (
        allocable * Decimal(weight) / Decimal(weight_total)
      ).quantize(Decimal("0.01"))
      running += amount
    categories.append(
      BudgetCategoryInput(
        name=name,
        allocated_amount=max(amount, Decimal("0.00")),
      )
    )
  return categories

async def seed_budgets(session: AsyncSession) -> None:
  await seed_module_permissions(session, BUDGET_PERMISSIONS)
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

  service = BudgetService(session)
  existing = await service.list_budgets(org.id, project.id)
  current = existing[0] if existing else None

  approved_amount = Decimal(random.randint(8_000_000, 30_000_000)).quantize(Decimal("0.01"))
  categories = _random_budget_categories(approved_amount)

  payload = BudgetSaveRequest(project_id=project.id, approved_amount=approved_amount, currency=None,
    notes=f"Seed-generated budget ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC).",
    categories=categories,
    version=current.version if current is not None else None,
  )

  budget = await service.save_budget(org.id, payload)
  action = "Refreshed" if current is not None else "Created"
  print(
    f"{action} budget for project {project.code or project.name}: "
    f"{budget.approved_amount} {budget.currency} across {len(budget.categories)} categories."
  )

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_budgets(session)

if __name__ == "__main__":
  asyncio.run(main())