from __future__ import annotations
import asyncio
import random
from app.modules.expenses.models import ExpenseStatus, Expense
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.identity.models import Organization, User
from app.modules.projects.models import Project
from app.core.database import AsyncSessionLocal
import asyncio
from app.shared.seed_utils import seed_module_permissions
from app.modules.expenses.permissions import EXPENSE_PERMISSIONS
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

EXPENSE_CATEGORY_POOL = [
  ("Site transport", (10_000, 80_000)),
  ("Temporary works", (50_000, 200_000)),
  ("Labour wages", (100_000, 500_000)),
  ("Equipment rental", (30_000, 250_000)),
  ("Utilities", (5_000, 40_000)),
  ("Site security", (20_000, 60_000)),
  ("Miscellaneous", (5_000, 50_000)),
]

STATUS_WEIGHTS = [
  (ExpenseStatus.PENDING, 40),
  (ExpenseStatus.APPROVED, 45),
  (ExpenseStatus.REJECTED, 15),
]

def _random_expenses(
  *,
  organization_id,
  project_id,
  submitted_by,
  reviewer_id,
  count: int,
) -> list[Expense]:
  today = date.today()
  chosen = random.sample(
    EXPENSE_CATEGORY_POOL, k=min(count, len(EXPENSE_CATEGORY_POOL))
  )
  statuses, weights = zip(*STATUS_WEIGHTS)
  expenses = []
  for category, amount_range in chosen:
    status = random.choices(statuses, weights=weights, k=1)[0]
    reviewed_by = reviewer_id if status != ExpenseStatus.PENDING else None
    review_note = (
      "Approved during seed generation."
      if status == ExpenseStatus.APPROVED
      else "Rejected during seed generation."
      if status == ExpenseStatus.REJECTED
      else None
    )
    expenses.append(
      Expense(
        id=uuid4(),
        organization_id=organization_id,
        project_id=project_id,
        category=category,
        description=f"Seed-generated {category.lower()} expense.",
        amount=Decimal(random.randint(*amount_range)).quantize(Decimal("0.01")),
        expense_date=today - timedelta(days=random.randint(0, 14)),
        status=status,
        submitted_by=submitted_by,
        reviewed_by=reviewed_by,
        review_note=review_note,
      )
    )
  return expenses

async def seed_expenses(session: AsyncSession) -> None:
  await seed_module_permissions(session, EXPENSE_PERMISSIONS)
  org = (
    await session.execute(
      select(Organization).order_by(Organization.created_at.asc()).limit(1)
    )
  ).scalar_one_or_none()
  if org is None:
    print("Skipping expenses seed: no organization exists.")
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
    print("Skipping expenses seed: no project exists.")
    return
  user = (
    await session.execute(
      select(User)
      .where(User.organization_id == org.id)
      .order_by(User.created_at.asc())
      .limit(1)
    )
  ).scalar_one_or_none()
  samples = _random_expenses(
    organization_id=org.id,
    project_id=project.id,
    submitted_by=user.id if user else None,
    reviewer_id=user.id if user else None,
    count=random.randint(1, 3),
  )
  session.add_all(samples)
  await session.commit()
  print(
    f"Expenses seed added {len(samples)} entr(y/ies) "
    f"for project {project.code or project.name}."
  )

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_expenses(session)

if __name__ == "__main__":
  asyncio.run(main())