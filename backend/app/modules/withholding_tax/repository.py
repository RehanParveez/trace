from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.withholding_tax.models import WithholdingTaxRate, WHTCategory, WithholdingTaxDeduction
from sqlalchemy import func, select
from uuid import UUID
from datetime import date

class WithholdingTaxRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create_rate(self, rate: WithholdingTaxRate) -> WithholdingTaxRate:
    self.session.add(rate)
    await self.session.flush()
    return rate

  async def get_rate(self, rate_id: UUID, organization_id: UUID) -> WithholdingTaxRate | None:
    result = await self.session.execute(
      select(WithholdingTaxRate).where(
        WithholdingTaxRate.id == rate_id, WithholdingTaxRate.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def get_active_rate(self, organization_id: UUID, category: WHTCategory) -> WithholdingTaxRate | None:
    result = await self.session.execute(
      select(WithholdingTaxRate)
      .where(
        WithholdingTaxRate.organization_id == organization_id,
        WithholdingTaxRate.category == category,
        WithholdingTaxRate.is_active.is_(True),
      )
      .order_by(WithholdingTaxRate.updated_at.desc())
      .limit(1)
    )
    return result.scalar_one_or_none()

  async def list_rates(self, organization_id: UUID) -> list[WithholdingTaxRate]:
    result = await self.session.execute(
      select(WithholdingTaxRate)
      .where(WithholdingTaxRate.organization_id == organization_id)
      .order_by(WithholdingTaxRate.category.asc(), WithholdingTaxRate.is_active.desc())
    )
    return list(result.scalars().all())

  async def create_deduction(self, deduction: WithholdingTaxDeduction) -> WithholdingTaxDeduction:
    self.session.add(deduction)
    await self.session.flush()
    return deduction

  async def list_deductions(
    self, organization_id: UUID, period_start: date | None, period_end: date | None, project_id: UUID | None,
  ) -> list[WithholdingTaxDeduction]:
    query = select(WithholdingTaxDeduction).where(WithholdingTaxDeduction.organization_id == organization_id)
    if period_start is not None:
      query = query.where(WithholdingTaxDeduction.deduction_date >= period_start)
    if period_end is not None:
      query = query.where(WithholdingTaxDeduction.deduction_date <= period_end)
    if project_id is not None:
      query = query.where(WithholdingTaxDeduction.project_id == project_id)
    result = await self.session.execute(query.order_by(WithholdingTaxDeduction.deduction_date.desc()))
    return list(result.scalars().all())

  async def get_register_summary(self, organization_id: UUID, period_start: date, period_end: date):
    result = await self.session.execute(
      select(
        WithholdingTaxDeduction.category,
        func.sum(WithholdingTaxDeduction.gross_amount).label("gross_total"),
        func.sum(WithholdingTaxDeduction.deducted_amount).label("deducted_total"),
        func.count(WithholdingTaxDeduction.id).label("count"),
      )
      .where(
        WithholdingTaxDeduction.organization_id == organization_id,
        WithholdingTaxDeduction.deduction_date >= period_start,
        WithholdingTaxDeduction.deduction_date <= period_end,
      )
      .group_by(WithholdingTaxDeduction.category)
    )
    return result.all()