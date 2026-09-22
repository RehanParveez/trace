from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from app.modules.subcontractors.models import Subcontractor, SubcontractAgreement, SubcontractAgreementItem, SubcontractorAdvance, SubcontractorBill, SubcontractorBillLineItem, SubcontractorBillStatus, SubcontractorPayment

class SubcontractorRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, subcontractor: Subcontractor) -> Subcontractor:
    self.session.add(subcontractor)
    await self.session.flush()
    return subcontractor

  async def get(self, subcontractor_id: UUID, organization_id: UUID) -> Subcontractor | None:
    result = await self.session.execute(
      select(Subcontractor).where(
        Subcontractor.id == subcontractor_id, Subcontractor.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def list_all(self, organization_id: UUID) -> list[Subcontractor]:
    result = await self.session.execute(
      select(Subcontractor).where(Subcontractor.organization_id == organization_id).order_by(Subcontractor.name.asc())
    )
    return list(result.scalars().all())

  async def create_agreement(self, agreement: SubcontractAgreement) -> SubcontractAgreement:
    self.session.add(agreement)
    await self.session.flush()
    return agreement

  async def create_agreement_items(self, items: list[SubcontractAgreementItem]) -> None:
    self.session.add_all(items)
    await self.session.flush()

  async def get_agreement(self, agreement_id: UUID, organization_id: UUID) -> SubcontractAgreement | None:
    result = await self.session.execute(
      select(SubcontractAgreement)
      .where(SubcontractAgreement.id == agreement_id, SubcontractAgreement.organization_id == organization_id)
      .options(selectinload(SubcontractAgreement.items))
    )
    return result.scalar_one_or_none()

  async def get_agreement_for_update(self, agreement_id: UUID, organization_id: UUID) -> SubcontractAgreement | None:
    result = await self.session.execute(
      select(SubcontractAgreement)
      .where(SubcontractAgreement.id == agreement_id, SubcontractAgreement.organization_id == organization_id)
      .options(selectinload(SubcontractAgreement.items))
      .with_for_update()
    )
    return result.scalar_one_or_none()

  async def list_agreements_by_project(self, organization_id: UUID, project_id: UUID) -> list[SubcontractAgreement]:
    result = await self.session.execute(
      select(SubcontractAgreement)
      .where(SubcontractAgreement.organization_id == organization_id, SubcontractAgreement.project_id == project_id)
      .options(selectinload(SubcontractAgreement.items))
      .order_by(SubcontractAgreement.status.asc(), SubcontractAgreement.start_date.desc())
    )
    return list(result.scalars().all())

  async def create_bill(self, bill: SubcontractorBill) -> SubcontractorBill:
    self.session.add(bill)
    await self.session.flush()
    return bill

  async def create_bill_line_items(self, items: list[SubcontractorBillLineItem]) -> None:
    self.session.add_all(items)
    await self.session.flush()

  async def get_bill(self, bill_id: UUID, organization_id: UUID) -> SubcontractorBill | None:
    result = await self.session.execute(
      select(SubcontractorBill)
      .where(SubcontractorBill.id == bill_id, SubcontractorBill.organization_id == organization_id)
      .options(selectinload(SubcontractorBill.line_items))
    )
    return result.scalar_one_or_none()

  async def get_bill_for_update(self, bill_id: UUID, organization_id: UUID) -> SubcontractorBill | None:
    result = await self.session.execute(
      select(SubcontractorBill)
      .where(SubcontractorBill.id == bill_id, SubcontractorBill.organization_id == organization_id)
      .options(selectinload(SubcontractorBill.line_items))
      .with_for_update()
    )
    return result.scalar_one_or_none()

  async def list_bills_by_agreement(self, organization_id: UUID, agreement_id: UUID) -> list[SubcontractorBill]:
    result = await self.session.execute(
      select(SubcontractorBill)
      .where(SubcontractorBill.organization_id == organization_id, SubcontractorBill.agreement_id == agreement_id)
      .order_by(SubcontractorBill.bill_number.desc())
    )
    return list(result.scalars().all())

  async def get_last_issued_bill(self, organization_id: UUID, agreement_id: UUID) -> SubcontractorBill | None:
    result = await self.session.execute(
      select(SubcontractorBill)
      .where(
        SubcontractorBill.organization_id == organization_id,
        SubcontractorBill.agreement_id == agreement_id,
        SubcontractorBill.status == SubcontractorBillStatus.ISSUED,
      )
      .options(selectinload(SubcontractorBill.line_items))
      .order_by(SubcontractorBill.bill_number.desc())
      .limit(1)
    )
    return result.scalar_one_or_none()

  async def get_max_bill_number(self, organization_id: UUID, agreement_id: UUID) -> int:
    result = await self.session.execute(
      select(func.max(SubcontractorBill.bill_number)).where(
        SubcontractorBill.organization_id == organization_id, SubcontractorBill.agreement_id == agreement_id,
      )
    )
    return result.scalar() or 0

  async def create_advance(self, advance: SubcontractorAdvance) -> SubcontractorAdvance:
    self.session.add(advance)
    await self.session.flush()
    return advance

  async def list_advances(self, organization_id: UUID, agreement_id: UUID) -> list[SubcontractorAdvance]:
    result = await self.session.execute(
      select(SubcontractorAdvance)
      .where(SubcontractorAdvance.organization_id == organization_id, SubcontractorAdvance.agreement_id == agreement_id)
      .order_by(SubcontractorAdvance.advance_date.desc())
    )
    return list(result.scalars().all())

  async def create_payment(self, payment: SubcontractorPayment) -> SubcontractorPayment:
    self.session.add(payment)
    await self.session.flush()
    return payment

  async def list_payments(self, organization_id: UUID, agreement_id: UUID) -> list[SubcontractorPayment]:
    result = await self.session.execute(
      select(SubcontractorPayment)
      .where(SubcontractorPayment.organization_id == organization_id, SubcontractorPayment.agreement_id == agreement_id)
      .order_by(SubcontractorPayment.payment_date.desc())
    )
    return list(result.scalars().all())

  async def get_ledger_totals(self, organization_id: UUID, agreement_id: UUID) -> tuple[float, float, float, float]:
    total_billed = (await self.session.execute(
      select(func.coalesce(func.sum(SubcontractorBill.net_payable), 0)).where(
        SubcontractorBill.organization_id == organization_id, SubcontractorBill.agreement_id == agreement_id,
        SubcontractorBill.status == SubcontractorBillStatus.ISSUED,
      )
    )).scalar_one()
    total_paid = (await self.session.execute(
      select(func.coalesce(func.sum(SubcontractorPayment.net_paid_amount), 0)).where(
        SubcontractorPayment.organization_id == organization_id, SubcontractorPayment.agreement_id == agreement_id,
      )
    )).scalar_one()
    total_advances = (await self.session.execute(
      select(func.coalesce(func.sum(SubcontractorAdvance.amount), 0)).where(
        SubcontractorAdvance.organization_id == organization_id, SubcontractorAdvance.agreement_id == agreement_id,
      )
    )).scalar_one()
    total_recovered = (await self.session.execute(
      select(func.coalesce(func.sum(SubcontractorPayment.advance_recovered_amount), 0)).where(
        SubcontractorPayment.organization_id == organization_id, SubcontractorPayment.agreement_id == agreement_id,
      )
    )).scalar_one()
    return float(total_billed), float(total_paid), float(total_advances), float(total_recovered)

  async def get_project_billed_total(self, organization_id: UUID, project_id: UUID) -> float:
    result = await self.session.execute(
      select(func.coalesce(func.sum(SubcontractorBill.net_payable), 0)).where(
        SubcontractorBill.organization_id == organization_id, SubcontractorBill.project_id == project_id,
        SubcontractorBill.status == SubcontractorBillStatus.ISSUED,
      )
    )
    return float(result.scalar_one())