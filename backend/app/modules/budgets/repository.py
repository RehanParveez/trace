from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.budgets.models import Budget, BudgetCategory
from sqlalchemy import select, func
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

  async def get_by_project_for_update(
    self, project_id: UUID, organization_id: UUID,
  ) -> Budget | None:
    result = await self.session.execute(
      select(Budget)
      .where(
        Budget.project_id == project_id,
        Budget.organization_id == organization_id,
      )
      .options(selectinload(Budget.categories))
      .with_for_update()
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
    
  async def list_by_org(self, organization_id: UUID) -> list[Budget]:
    result = await self.session.execute(
      select(Budget).where(Budget.organization_id == organization_id)
    )
    return list(result.scalars().all())
  
  async def get_organization_summary(
    self, organization_id: UUID,
  ) -> dict:
    result = await self.session.execute(
      select(
        func.coalesce(func.sum(Budget.approved_amount), 0).label(
          "total_approved_amount",
        ),
        func.count(Budget.id).label("budget_count"),
      ).where(Budget.organization_id == organization_id)
    )
    row = result.one()
    return {
      "total_approved_amount": row.total_approved_amount,
      "budget_count": row.budget_count,
    }
    
  async def get_category_for_project(
    self, category_id: UUID, project_id: UUID, organization_id: UUID,
  ) -> BudgetCategory | None:
    result = await self.session.execute(
      select(BudgetCategory)
      .join(Budget, Budget.id == BudgetCategory.budget_id)
      .where(
        BudgetCategory.id == category_id,
        Budget.project_id == project_id,
        Budget.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def find_categories_by_name(
    self, project_id: UUID, organization_id: UUID, name: str,
  ) -> list[BudgetCategory]:
    result = await self.session.execute(
      select(BudgetCategory)
      .join(Budget, Budget.id == BudgetCategory.budget_id)
      .where(
        Budget.project_id == project_id,
        Budget.organization_id == organization_id,
        func.lower(func.trim(BudgetCategory.name)) == name.strip().lower(),
      )
    )
    return list(result.scalars().all())
  
