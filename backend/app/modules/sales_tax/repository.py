from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.sales_tax.models import SalesTaxRate, SalesTaxAuthority, SalesTaxCharge
from uuid import UUID
from sqlalchemy import func, select
from datetime import date

class SalesTaxRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create_rate(self, rate: SalesTaxRate) -> SalesTaxRate:
    self.session.add(rate)
    await self.session.flush()
    return rate

  async def get_rate(self, rate_id: UUID, organization_id: UUID) -> SalesTaxRate | None:
    result = await self.session.execute(
      select(SalesTaxRate).where(SalesTaxRate.id == rate_id, SalesTaxRate.organization_id == organization_id)
    )
    return result.scalar_one_or_none()

  async def get_active_rate(self, organization_id: UUID, authority: SalesTaxAuthority) -> SalesTaxRate | None:
    result = await self.session.execute(
      select(SalesTaxRate)
      .where(
        SalesTaxRate.organization_id == organization_id,
        SalesTaxRate.authority == authority,
        SalesTaxRate.is_active.is_(True),
      )
      .order_by(SalesTaxRate.updated_at.desc())
      .limit(1)
    )
    return result.scalar_one_or_none()

  async def list_rates(self, organization_id: UUID) -> list[SalesTaxRate]:
    result = await self.session.execute(
      select(SalesTaxRate)
      .where(SalesTaxRate.organization_id == organization_id)
      .order_by(SalesTaxRate.authority.asc(), SalesTaxRate.is_active.desc())
    )
    return list(result.scalars().all())

  async def create_charge(self, charge: SalesTaxCharge) -> SalesTaxCharge:
    self.session.add(charge)
    await self.session.flush()
    return charge

  async def list_charges(
    self, organization_id: UUID, period_start: date | None, period_end: date | None, project_id: UUID | None,
  ) -> list[SalesTaxCharge]:
    query = select(SalesTaxCharge).where(SalesTaxCharge.organization_id == organization_id)
    if period_start is not None:
      query = query.where(SalesTaxCharge.charge_date >= period_start)
    if period_end is not None:
      query = query.where(SalesTaxCharge.charge_date <= period_end)
    if project_id is not None:
      query = query.where(SalesTaxCharge.project_id == project_id)
    result = await self.session.execute(query.order_by(SalesTaxCharge.charge_date.desc()))
    return list(result.scalars().all())

  async def get_register_summary(self, organization_id: UUID, period_start: date, period_end: date):
    result = await self.session.execute(
      select(
        SalesTaxCharge.authority,
        func.sum(SalesTaxCharge.taxable_amount).label("taxable_total"),
        func.sum(SalesTaxCharge.tax_amount).label("tax_total"),
        func.count(SalesTaxCharge.id).label("count"),
      )
      .where(
        SalesTaxCharge.organization_id == organization_id,
        SalesTaxCharge.charge_date >= period_start,
        SalesTaxCharge.charge_date <= period_end,
      )
      .group_by(SalesTaxCharge.authority)
    )
    return result.all()