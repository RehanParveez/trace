from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.running_bills.models import RunningBill, RunningBillLineItem, RunningBillStatus
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from datetime import date
from app.modules.drawings_boq.models import BOQItem, BOQItemStatus
from app.modules.verification.models import ProgressClaim, ProgressClaimStatus

class RunningBillRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def get_by_id(self, bill_id: UUID, organization_id: UUID) -> RunningBill | None:
    result = await self.session.execute(
      select(RunningBill)
      .where(RunningBill.id == bill_id, RunningBill.organization_id == organization_id)
      .options(selectinload(RunningBill.line_items))
    )
    return result.scalar_one_or_none()

  async def get_by_id_for_update(self, bill_id: UUID, organization_id: UUID) -> RunningBill | None:
    result = await self.session.execute(
      select(RunningBill)
      .where(RunningBill.id == bill_id, RunningBill.organization_id == organization_id)
      .options(selectinload(RunningBill.line_items))
      .with_for_update()
    )
    return result.scalar_one_or_none()

  async def list_by_project(self, organization_id: UUID, project_id: UUID) -> list[RunningBill]:
    result = await self.session.execute(
      select(RunningBill)
      .where(RunningBill.organization_id == organization_id, RunningBill.project_id == project_id)
      .order_by(RunningBill.bill_number.desc())
    )
    return list(result.scalars().all())

  async def get_last_issued_bill(
    self, organization_id: UUID, project_id: UUID, boq_version_id: UUID,
  ) -> RunningBill | None:
    result = await self.session.execute(
      select(RunningBill)
      .where(
        RunningBill.organization_id == organization_id,
        RunningBill.project_id == project_id,
        RunningBill.boq_version_id == boq_version_id,
        RunningBill.status == RunningBillStatus.ISSUED,
      )
      .options(selectinload(RunningBill.line_items))
      .order_by(RunningBill.bill_number.desc())
      .limit(1)
    )
    return result.scalar_one_or_none()

  async def get_max_bill_number(self, organization_id: UUID, project_id: UUID) -> int:
    result = await self.session.execute(
      select(func.max(RunningBill.bill_number)).where(
        RunningBill.organization_id == organization_id, RunningBill.project_id == project_id,
      )
    )
    return result.scalar() or 0

  async def create(self, bill: RunningBill) -> RunningBill:
    self.session.add(bill)
    await self.session.flush()
    return bill

  async def create_line_items(self, line_items: list[RunningBillLineItem]) -> None:
    self.session.add_all(line_items)
    await self.session.flush()

  async def get_billable_boq_items(self, organization_id: UUID, boq_version_id: UUID) -> list[BOQItem]:
    result = await self.session.execute(
      select(BOQItem)
      .where(
        BOQItem.organization_id == organization_id,
        BOQItem.boq_version_id == boq_version_id,
        BOQItem.status == BOQItemStatus.APPROVED,
      )
      .order_by(BOQItem.material_name.asc())
    )
    return list(result.scalars().all())

  async def get_latest_approved_claims_as_of(
    self, organization_id: UUID, project_id: UUID, as_of_date: date | None,
  ) -> dict[UUID, ProgressClaim]:
    if as_of_date is None:
      return {}

    result = await self.session.execute(
      select(ProgressClaim)
      .distinct(ProgressClaim.boq_item_id)
      .where(
        ProgressClaim.organization_id == organization_id,
        ProgressClaim.project_id == project_id,
        ProgressClaim.status == ProgressClaimStatus.APPROVED,
        ProgressClaim.claim_date <= as_of_date,
      )
      .order_by(ProgressClaim.boq_item_id, ProgressClaim.claim_date.desc(), ProgressClaim.created_at.desc())
    )
    claims = result.scalars().unique().all()
    return {claim.boq_item_id: claim for claim in claims}