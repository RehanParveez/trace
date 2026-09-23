from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.retention.models import  RetentionRelease, RetentionHolderType
from sqlalchemy import func, select
from app.modules.running_bills.models import RunningBill, RunningBillStatus
from app.modules.subcontractors.models import SubcontractorBill, SubcontractorBillStatus
from uuid import UUID
from decimal import Decimal

class RetentionRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create_release(self, release: RetentionRelease) -> RetentionRelease:
    self.session.add(release)
    await self.session.flush()
    return release

  async def list_releases(self, organization_id: UUID, project_id: UUID | None = None) -> list[RetentionRelease]:
    query = select(RetentionRelease).where(RetentionRelease.organization_id == organization_id)
    if project_id is not None:
      query = query.where(RetentionRelease.project_id == project_id)
    result = await self.session.execute(query.order_by(RetentionRelease.release_date.desc()))
    return list(result.scalars().all())

  async def get_latest_issued_running_bills(
    self, organization_id: UUID, project_id: UUID | None = None,
  ) -> list[RunningBill]:
    query = select(RunningBill).distinct(RunningBill.boq_version_id).where(
      RunningBill.organization_id == organization_id, RunningBill.status == RunningBillStatus.ISSUED,
    )
    if project_id is not None:
      query = query.where(RunningBill.project_id == project_id)
    result = await self.session.execute(query.order_by(RunningBill.boq_version_id, RunningBill.bill_number.desc()))
    return list(result.scalars().unique())

  async def get_latest_issued_subcontractor_bills(
    self, organization_id: UUID, project_id: UUID | None = None,
  ) -> list[SubcontractorBill]:
    query = select(SubcontractorBill).distinct(SubcontractorBill.agreement_id).where(
      SubcontractorBill.organization_id == organization_id, SubcontractorBill.status == SubcontractorBillStatus.ISSUED,
    )
    if project_id is not None:
      query = query.where(SubcontractorBill.project_id == project_id)
    result = await self.session.execute(query.order_by(SubcontractorBill.agreement_id, SubcontractorBill.bill_number.desc()))
    return list(result.scalars().unique())

  async def get_latest_issued_running_bill(self, organization_id: UUID, boq_version_id: UUID) -> RunningBill | None:
    result = await self.session.execute(
      select(RunningBill).where(
        RunningBill.organization_id == organization_id, RunningBill.boq_version_id == boq_version_id,
        RunningBill.status == RunningBillStatus.ISSUED,
      ).order_by(RunningBill.bill_number.desc()).limit(1)
    )
    return result.scalar_one_or_none()

  async def get_latest_issued_subcontractor_bill(self, organization_id: UUID, agreement_id: UUID) -> SubcontractorBill | None:
    result = await self.session.execute(
      select(SubcontractorBill).where(
        SubcontractorBill.organization_id == organization_id, SubcontractorBill.agreement_id == agreement_id,
        SubcontractorBill.status == SubcontractorBillStatus.ISSUED,
      ).order_by(SubcontractorBill.bill_number.desc()).limit(1)
    )
    return result.scalar_one_or_none()

  async def get_client_releases_total(
    self, organization_id: UUID, boq_version_id: UUID | None = None, project_id: UUID | None = None,
  ) -> Decimal:
    query = select(func.coalesce(func.sum(RetentionRelease.amount), 0)).where(
      RetentionRelease.organization_id == organization_id, RetentionRelease.holder_type == RetentionHolderType.CLIENT,
    )
    if boq_version_id is not None:
      query = query.where(RetentionRelease.boq_version_id == boq_version_id)
    if project_id is not None:
      query = query.where(RetentionRelease.project_id == project_id)
    return Decimal(str((await self.session.execute(query)).scalar_one()))

  async def get_subcontractor_releases_total(
    self, organization_id: UUID, agreement_id: UUID | None = None, project_id: UUID | None = None,
  ) -> Decimal:
    query = select(func.coalesce(func.sum(RetentionRelease.amount), 0)).where(
      RetentionRelease.organization_id == organization_id, RetentionRelease.holder_type == RetentionHolderType.SUBCONTRACTOR,
    )
    if agreement_id is not None:
      query = query.where(RetentionRelease.agreement_id == agreement_id)
    if project_id is not None:
      query = query.where(RetentionRelease.project_id == project_id)
    return Decimal(str((await self.session.execute(query)).scalar_one()))