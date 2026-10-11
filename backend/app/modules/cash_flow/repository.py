from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.cash_flow.models import CashFlowSettings
from uuid import UUID
from sqlalchemy import func, select
from app.modules.procurement.models import ProcurementRequest, ProcurementStatus
from decimal import Decimal
from datetime import date
from sqlalchemy import and_
from app.modules.labour.models import LabourAttendance, LabourDeployment, LabourPayment
from app.modules.subcontractors.models import SubcontractorBill, SubcontractorBillStatus, SubcontractorPayment
from app.modules.running_bills.models import RunningBill, RunningBillCollection, RunningBillStatus
from app.modules.procurement.models import ProcurementDelivery
from app.modules.sales_tax.models import SalesTaxCharge, SalesTaxSourceType
from app.modules.withholding_tax.models import WithholdingTaxDeduction

class CashFlowRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def get_or_create_settings(self, organization_id: UUID) -> CashFlowSettings:
    result = await self.session.execute(
      select(CashFlowSettings).where(CashFlowSettings.organization_id == organization_id)
    )
    settings = result.scalar_one_or_none()
    if settings is None:
      import uuid as _uuid
      settings = CashFlowSettings(id=_uuid.uuid4(), organization_id=organization_id)
      self.session.add(settings)
      await self.session.flush()
    return settings

  async def get_pending_procurement(
    self, organization_id: UUID, project_id: UUID | None,
  ) -> list[ProcurementRequest]:
    query = select(ProcurementRequest).where(
      ProcurementRequest.organization_id == organization_id,
      ProcurementRequest.status.in_([ProcurementStatus.APPROVED, ProcurementStatus.ORDERED]),
    )
    if project_id is not None:
      query = query.where(ProcurementRequest.project_id == project_id)
    result = await self.session.execute(query)
    return list(result.scalars().all())

  async def get_labour_run_rate_total(
    self, organization_id: UUID, project_id: UUID | None, lookback_start: date, lookback_end: date,
  ) -> Decimal:
    query = (
      select(func.coalesce(func.sum(LabourAttendance.units_present * LabourDeployment.daily_rate), 0))
      .join(LabourDeployment, LabourDeployment.id == LabourAttendance.deployment_id)
      .where(
        LabourAttendance.organization_id == organization_id,
        LabourAttendance.attendance_date >= lookback_start,
        LabourAttendance.attendance_date <= lookback_end,
      )
    )
    if project_id is not None:
      query = query.where(LabourAttendance.project_id == project_id)
    result = await self.session.execute(query)
    return Decimal(str(result.scalar_one()))

  async def get_outstanding_subcontractor_bills(
    self, organization_id: UUID, project_id: UUID | None,
  ) -> list[tuple[SubcontractorBill, Decimal]]:
    """Returns (bill, amount_already_paid_against_this_bill) pairs."""
    query = select(SubcontractorBill).where(
      SubcontractorBill.organization_id == organization_id,
      SubcontractorBill.status == SubcontractorBillStatus.ISSUED,
    )
    if project_id is not None:
      query = query.where(SubcontractorBill.project_id == project_id)
    bills = list((await self.session.execute(query)).scalars().all())

    paid_by_bill: dict[UUID, Decimal] = {}
    if bills:
      paid_result = await self.session.execute(
        select(SubcontractorPayment.bill_id, func.coalesce(func.sum(SubcontractorPayment.gross_amount), 0))
        .where(SubcontractorPayment.organization_id == organization_id, SubcontractorPayment.bill_id.in_([b.id for b in bills]))
        .group_by(SubcontractorPayment.bill_id)
      )
      paid_by_bill = {row[0]: Decimal(str(row[1])) for row in paid_result.all()}

    return [(bill, paid_by_bill.get(bill.id, Decimal("0"))) for bill in bills]

  async def get_outstanding_running_bills(
    self, organization_id: UUID, project_id: UUID | None,
  ) -> list[RunningBill]:
    query = select(RunningBill).where(
      RunningBill.organization_id == organization_id, RunningBill.status == RunningBillStatus.ISSUED,
    )
    if project_id is not None:
      query = query.where(RunningBill.project_id == project_id)
    result = await self.session.execute(query)
    return list(result.scalars().all())
  
  async def get_delivery_payables(
    self, organization_id: UUID, project_id: UUID | None, since: date,
  ) -> list[tuple[ProcurementDelivery, ProcurementRequest]]:
    """Deliveries received since `since` and not voided: goods on site that suppliers will want to be paid for."""
    query = (
      select(ProcurementDelivery, ProcurementRequest)
      .join(ProcurementRequest, ProcurementRequest.id == ProcurementDelivery.request_id)
      .where(
        ProcurementDelivery.organization_id == organization_id,
        ProcurementDelivery.voided_at.is_(None),
        ProcurementDelivery.received_date >= since,
      )
    )
    if project_id is not None:
      query = query.where(ProcurementDelivery.project_id == project_id)
    return [(d, r) for d, r in (await self.session.execute(query)).all()]

  async def get_delivered_by_request(self, organization_id: UUID, request_ids: list[UUID]) -> dict[UUID, Decimal]:
    if not request_ids:
      return {}
    rows = (await self.session.execute(
      select(ProcurementDelivery.request_id, func.sum(ProcurementDelivery.quantity)).where(
        ProcurementDelivery.organization_id == organization_id,
        ProcurementDelivery.request_id.in_(request_ids),
        ProcurementDelivery.voided_at.is_(None),
      ).group_by(ProcurementDelivery.request_id)
    )).all()
    return {row[0]: Decimal(str(row[1])) for row in rows}

  async def get_labour_wages_due(self, organization_id: UUID, project_id: UUID | None) -> Decimal:
    """Wages already earned from attendance minus what has been paid out (gross), never below zero per project."""
    accrued_q = (
      select(LabourAttendance.project_id, func.coalesce(func.sum(LabourAttendance.units_present * LabourDeployment.daily_rate), 0))
      .join(LabourDeployment, LabourDeployment.id == LabourAttendance.deployment_id)
      .where(LabourAttendance.organization_id == organization_id)
      .group_by(LabourAttendance.project_id)
    )
    paid_q = (
      select(LabourPayment.project_id, func.coalesce(func.sum(LabourPayment.gross_wage_amount), 0))
      .where(LabourPayment.organization_id == organization_id)
      .group_by(LabourPayment.project_id)
    )
    if project_id is not None:
      accrued_q = accrued_q.where(LabourAttendance.project_id == project_id)
      paid_q = paid_q.where(LabourPayment.project_id == project_id)
    accrued = {row[0]: Decimal(str(row[1])) for row in (await self.session.execute(accrued_q)).all()}
    paid = {row[0]: Decimal(str(row[1])) for row in (await self.session.execute(paid_q)).all()}
    return sum((max(value - paid.get(pid, Decimal("0")), Decimal("0")) for pid, value in accrued.items()), Decimal("0"))

  async def get_sales_tax_net_for_month(
    self, organization_id: UUID, project_id: UUID | None, month_start: date, month_end: date,
  ) -> Decimal:
    
    base = and_(
      SalesTaxCharge.organization_id == organization_id,
      SalesTaxCharge.charge_date >= month_start, SalesTaxCharge.charge_date <= month_end,
    )
    query = select(SalesTaxCharge.source_type, func.coalesce(func.sum(SalesTaxCharge.tax_amount), 0)).where(base).group_by(SalesTaxCharge.source_type)
    if project_id is not None:
      query = query.where(SalesTaxCharge.project_id == project_id)
    totals = {row[0]: Decimal(str(row[1])) for row in (await self.session.execute(query)).all()}
    return totals.get(SalesTaxSourceType.RUNNING_BILL, Decimal("0")) - totals.get(SalesTaxSourceType.SUBCONTRACTOR_BILL, Decimal("0"))

  async def get_wht_deducted_for_month(
    self, organization_id: UUID, project_id: UUID | None, month_start: date, month_end: date,
  ) -> Decimal:
    query = select(func.coalesce(func.sum(WithholdingTaxDeduction.deducted_amount), 0)).where(
      WithholdingTaxDeduction.organization_id == organization_id,
      WithholdingTaxDeduction.deduction_date >= month_start, WithholdingTaxDeduction.deduction_date <= month_end,
    )
    if project_id is not None:
      query = query.where(WithholdingTaxDeduction.project_id == project_id)
    return Decimal(str((await self.session.execute(query)).scalar_one()))

  async def get_observed_client_wht_percentage(self, organization_id: UUID, project_id: UUID | None) -> Decimal | None:
    query = select(
      func.coalesce(func.sum(RunningBillCollection.client_wht_amount), 0),
      func.coalesce(func.sum(RunningBillCollection.credited_amount), 0),
    ).where(RunningBillCollection.organization_id == organization_id, RunningBillCollection.voided_at.is_(None))
    
    if project_id is not None:
      query = query.where(RunningBillCollection.project_id == project_id)
    wht, credited = (await self.session.execute(query)).one()
    wht, credited = Decimal(str(wht)), Decimal(str(credited))
    if credited <= 0 or wht <= 0:
      return None
    return (wht * Decimal("100") / credited).quantize(Decimal("0.1"))