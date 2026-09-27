from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.cash_flow.models import CashFlowSettings
from uuid import UUID
from sqlalchemy import func, select
from app.modules.procurement.models import ProcurementRequest, ProcurementStatus
from decimal import Decimal
from datetime import date
from app.modules.labour.models import LabourAttendance, LabourDeployment
from app.modules.subcontractors.models import SubcontractorBill, SubcontractorBillStatus, SubcontractorPayment
from app.modules.running_bills.models import RunningBill, RunningBillStatus

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
        select(SubcontractorPayment.bill_id, func.coalesce(func.sum(SubcontractorPayment.net_paid_amount), 0))
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