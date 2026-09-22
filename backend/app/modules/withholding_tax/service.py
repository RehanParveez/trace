from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.withholding_tax.repository import WithholdingTaxRepository
from app.modules.withholding_tax.schemas import WHTRateCreateRequest, WHTRateUpdateRequest
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import date
from app.core.exceptions import TraceException
from app.modules.identity.models import Organization
from app.modules.withholding_tax.models import WHTCategory, WHTSourceType, WithholdingTaxDeduction, WithholdingTaxRate

class WithholdingTaxService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = WithholdingTaxRepository(session)

  async def create_rate(self, organization_id: UUID, payload: WHTRateCreateRequest) -> WithholdingTaxRate:
    existing_active = await self.repo.get_active_rate(organization_id, payload.category)
    if existing_active is not None:
      existing_active.is_active = False

    rate = WithholdingTaxRate(
      id=uuid4(), organization_id=organization_id, category=payload.category,
      filer_rate_percentage=payload.filer_rate_percentage, non_filer_rate_percentage=payload.non_filer_rate_percentage,
      effective_from=payload.effective_from, is_active=True, notes=payload.notes,
    )
    await self.repo.create_rate(rate)
    await self.session.commit()
    return rate

  async def update_rate(self, organization_id: UUID, rate_id: UUID, payload: WHTRateUpdateRequest) -> WithholdingTaxRate:
    rate = await self.repo.get_rate(rate_id, organization_id)
    if rate is None:
      raise TraceException("Withholding tax rate not found.", status_code=404, code="WHT_RATE_NOT_FOUND")
    for field in ("filer_rate_percentage", "non_filer_rate_percentage", "effective_from", "is_active", "notes"):
      value = getattr(payload, field)
      if value is not None:
        setattr(rate, field, value)
    await self.session.commit()
    return rate

  async def list_rates(self, organization_id: UUID) -> list[WithholdingTaxRate]:
    return await self.repo.list_rates(organization_id)

  async def calculate_preview(
    self, organization_id: UUID, category: WHTCategory, gross_amount: Decimal, is_filer: bool,
  ) -> tuple[Decimal, Decimal]:
    rate = await self.repo.get_active_rate(organization_id, category)
    if rate is None:
      raise TraceException(
        f"No active withholding tax rate is configured for "
        f"{category.value.replace('_', ' ').title()}. Add one under Withholding Tax settings first.",
        status_code=409, code="WHT_RATE_NOT_CONFIGURED",
      )
    rate_percentage = rate.filer_rate_percentage if is_filer else rate.non_filer_rate_percentage
    deducted_amount = (gross_amount * rate_percentage / Decimal("100")).quantize(Decimal("0.01"))
    return rate_percentage, deducted_amount

  async def calculate_and_record(
    self, *, organization_id: UUID, project_id: UUID, category: WHTCategory, gross_amount: Decimal,
    is_filer: bool, payee_name: str, payee_ntn_or_cnic: str | None,
    source_type: WHTSourceType, source_id: UUID, actor_user_id: UUID,
  ) -> tuple[Decimal, Decimal]:

    rate_percentage, deducted_amount = await self.calculate_preview(organization_id, category, gross_amount, is_filer)
    organization = await self.session.get(Organization, organization_id)

    deduction = WithholdingTaxDeduction(
      id=uuid4(), organization_id=organization_id, project_id=project_id,
      source_type=source_type, source_id=source_id, payee_name=payee_name, payee_ntn_or_cnic=payee_ntn_or_cnic,
      category=category, gross_amount=gross_amount, rate_percentage=rate_percentage, is_filer=is_filer,
      deducted_amount=deducted_amount, deduction_date=date.today(),
      currency=organization.currency if organization else "PKR", created_by_user_id=actor_user_id,
    )
    await self.repo.create_deduction(deduction)
    return rate_percentage, deducted_amount

  async def list_deductions(
    self, organization_id: UUID, period_start: date | None, period_end: date | None, project_id: UUID | None,
  ) -> list[WithholdingTaxDeduction]:
    return await self.repo.list_deductions(organization_id, period_start, period_end, project_id)

  async def get_register_summary(self, organization_id: UUID, period_start: date, period_end: date) -> dict:
    rows = await self.repo.get_register_summary(organization_id, period_start, period_end)
    organization = await self.session.get(Organization, organization_id)
    total = sum((Decimal(str(row.deducted_total)) for row in rows), Decimal("0"))
    return {
      "period_start": period_start, "period_end": period_end,
      "by_category": [
        {
          "category": row.category, "total_gross_amount": Decimal(str(row.gross_total)),
          "total_deducted_amount": Decimal(str(row.deducted_total)), "deduction_count": row.count,
        }
        for row in rows
      ],
      "total_deducted_amount": total,
      "currency": organization.currency if organization else "PKR",
    }