from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.identity.models import Organization, User
from app.modules.projects.models import Project
from app.modules.expenses.models import Expense, ExpenseStatus
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4
from app.core.database import AsyncSessionLocal
import asyncio

async def seed_expenses(session: AsyncSession) -> None:
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

  existing = (
    await session.execute(
      select(Expense).where(
        Expense.project_id == project.id,
        Expense.organization_id == org.id,
      )
    )
  ).scalars().all()
  if existing:
    print(f"Expenses already exist for project {project.code or project.name}.")
    return

  today = date.today()
  samples = [
    Expense(
      id=uuid4(),
      organization_id=org.id,
      project_id=project.id,
      category="Site transport",
      description="Diesel for site vehicles — week of 1–7 Sep.",
      amount=Decimal("48500.00"),
      expense_date=today - timedelta(days=5),
      status=ExpenseStatus.PENDING,
      submitted_by=user.id if user else None,
    ),
    Expense(
      id=uuid4(),
      organization_id=org.id,
      project_id=project.id,
      category="Temporary works",
      description="Scaffolding hire — first month.",
      amount=Decimal("125000.00"),
      expense_date=today - timedelta(days=3),
      status=ExpenseStatus.APPROVED,
      submitted_by=user.id if user else None,
      reviewed_by=user.id if user else None,
      review_note="Within contingency allowance.",
    ),
    Expense(
      id=uuid4(),
      organization_id=org.id,
      project_id=project.id,
      category="Miscellaneous",
      description="Unplanned equipment rental — rejected as personal use.",
      amount=Decimal("15000.00"),
      expense_date=today - timedelta(days=2),
      status=ExpenseStatus.REJECTED,
      submitted_by=user.id if user else None,
      reviewed_by=user.id if user else None,
      review_note="Not a project cost.",
    ),
  ]
  session.add_all(samples)
  await session.commit()
  print(f"Expenses seed completed ({len(samples)} entries) for project {project.code or project.name}.")

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await seed_expenses(session)

if __name__ == "__main__":
  asyncio.run(main())