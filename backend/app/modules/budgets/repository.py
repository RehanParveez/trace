from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.budgets.models import Budget, BudgetCategory
from sqlalchemy import select
from sqlalchemy.orm import selectinload

class BudgetRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def list_by_project(
    self, project_id: UUID, organization_id: UUID,
  ) -> list[Budget]:
    result = await self.session.execute(
      select(Budget)
      .where(
        Budget.project_id == project_id,
        Budget.organization_id == organization_id,
      )
      .options(selectinload(Budget.categories))
      .order_by(Budget.created_at.desc())
    )
    return list(result.scalars().unique().all())

  async def get_by_project(
    self, project_id: UUID, organization_id: UUID,
  ) -> Budget | None:
    result = await self.session.execute(
      select(Budget)
      .where(
        Budget.project_id == project_id,
        Budget.organization_id == organization_id,
      )
      .options(selectinload(Budget.categories))
    )
    return result.scalar_one_or_none()

  async def create(self, budget: Budget) -> Budget:
    self.session.add(budget)
    await self.session.flush()
    return budget

  async def delete_categories(self, budget: Budget) -> None:
    for category in list(budget.categories):
      await self.session.delete(category)
    await self.session.flush()