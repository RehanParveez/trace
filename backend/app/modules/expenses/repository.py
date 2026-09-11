from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.expenses.models import Expense, ExpenseStatus
from uuid import UUID
from sqlalchemy import select, func

class ExpenseRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def list_expenses(
    self,
    organization_id: UUID,
    project_id: UUID | None = None,
    status: ExpenseStatus | None = None,
    skip: int = 0,
    limit: int = 100,
  ) -> list[Expense]:
    q = select(Expense).where(Expense.organization_id == organization_id)
    if project_id is not None:
      q = q.where(Expense.project_id == project_id)
    if status is not None:
      q = q.where(Expense.status == status)
    q = q.order_by(Expense.expense_date.desc(), Expense.created_at.desc())
    q = q.offset(skip).limit(limit)
    result = await self.session.execute(q)
    return list(result.scalars().all())

  async def get_by_id(
    self, expense_id: UUID, organization_id: UUID,
  ) -> Expense | None:
    result = await self.session.execute(
      select(Expense).where(
        Expense.id == expense_id,
        Expense.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def create(self, expense: Expense) -> Expense:
    self.session.add(expense)
    await self.session.flush()
    return expense

  async def get_organization_summary(
    self, organization_id: UUID,
  ) -> dict:
    result = await self.session.execute(
      select(
        func.coalesce(func.sum(Expense.amount), 0).label(
          "total_approved_amount",
        ),
        func.count(Expense.id).label("expense_count"),
      ).where(
        Expense.organization_id == organization_id,
        Expense.status == ExpenseStatus.APPROVED,
      )
    )
    row = result.one()
    return {
      "total_approved_amount": row.total_approved_amount,
      "expense_count": row.expense_count,
    }