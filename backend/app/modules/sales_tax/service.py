from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.sales_tax.repository import SalesTaxRepository
from uuid import UUID, uuid4
from app.modules.sales_tax.schemas import SalesTaxRateCreateRequest, SalesTaxRateUpdateRequest
from decimal import Decimal
from app.modules.sales_tax.models import SalesTaxRate, SalesTaxAuthority, SalesTaxCharge, SalesTaxSourceType
from app.core.exceptions import TraceException
from app.modules.identity.models import Organization
from datetime import date

class SalesTaxService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = SalesTaxRepository(session)

  async def create_rate(self, organization_id: UUID, payload: SalesTaxRateCreateRequest) -> SalesTaxRate:
    existing_active = await self.repo.get_active_rate(organization_id, payload.authority)
    if existing_active is not None:
      existing_active.is_active = False

    rate = SalesTaxRate(
      id=uuid4(), organization_id=organization_id, authority=payload.authority,
      rate_percentage=payload.rate_percentage, effective_from=payload.effective_from,
      is_active=True, notes=payload.notes,
    )
    await self.repo.create_rate(rate)
    await self.session.commit()
    return rate

  async def update_rate(self, organization_id: UUID, rate_id: UUID, payload: SalesTaxRateUpdateRequest) -> SalesTaxRate:
    rate = await self.repo.get_rate(rate_id, organization_id)
    if rate is None:
      raise TraceException("Sales tax rate not found.", status_code=404, code="SALES_TAX_RATE_NOT_FOUND")
    for field_name in ("rate_percentage", "effective_from", "is_active", "notes"):
      value = getattr(payload, field_name)
      if value is not None:
        setattr(rate, field_name, value)
    await self.session.commit()
    return rate

  async def list_rates(self, organization_id: UUID) -> list[SalesTaxRate]:
    return await self.repo.list_rates(organization_id)

  async def calculate_preview(
    self, organization_id: UUID, authority: SalesTaxAuthority, taxable_amount: Decimal,
  ) -> tuple[Decimal, Decimal]:
    rate = await self.repo.get_active_rate(organization_id, authority)
    if rate is None:
      raise TraceException(
        f"No active sales tax rate is configured for {authority.value}. "
        f"Add one under Sales Tax settings first.",
        status_code=409, code="SALES_TAX_RATE_NOT_CONFIGURED",
      )
    tax_amount = (taxable_amount * rate.rate_percentage / Decimal("100")).quantize(Decimal("0.01"))
    return rate.rate_percentage, tax_amount

  async def calculate_and_record(
    self, *, organization_id: UUID, project_id: UUID, authority: SalesTaxAuthority, taxable_amount: Decimal,
    source_type: SalesTaxSourceType, source_id: UUID, charge_date: date, actor_user_id: UUID,
  ) -> tuple[Decimal, Decimal]:
    """
    Adds a SalesTaxCharge to the session but does NOT commit -- called
    from inside RunningBillService/SubcontractorService's issue_bill,
    so the tax charge and the bill status change commit atomically
    together, same pattern as WithholdingTaxService.calculate_and_record.
    """
    rate_percentage, tax_amount = await self.calculate_preview(organization_id, authority, taxable_amount)
    organization = await self.session.get(Organization, organization_id)

    charge = SalesTaxCharge(
      id=uuid4(), organization_id=organization_id, project_id=project_id, source_type=source_type,
      source_id=source_id, authority=authority, rate_percentage=rate_percentage,
      taxable_amount=taxable_amount, tax_amount=tax_amount, charge_date=charge_date,
      currency=organization.currency if organization else "PKR", created_by_user_id=actor_user_id,
    )
    await self.repo.create_charge(charge)
    return rate_percentage, tax_amount

  async def list_charges(
    self, organization_id: UUID, period_start: date | None, period_end: date | None, project_id: UUID | None,
  ) -> list[SalesTaxCharge]:
    return await self.repo.list_charges(organization_id, period_start, period_end, project_id)

  async def get_register_summary(self, organization_id: UUID, period_start: date, period_end: date) -> dict:
    rows = await self.repo.get_register_summary(organization_id, period_start, period_end)
    organization = await self.session.get(Organization, organization_id)
    total = sum((Decimal(str(row.tax_total)) for row in rows), Decimal("0"))
    return {
      "period_start": period_start, "period_end": period_end,
      "by_authority": [
        {"authority": row.authority, "total_taxable_amount": Decimal(str(row.taxable_total)),
         "total_tax_amount": Decimal(str(row.tax_total)), "charge_count": row.count}
        for row in rows
      ],
      "total_tax_amount": total,
      "currency": organization.currency if organization else "PKR",
    }