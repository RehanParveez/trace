from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.bank_guarantees.models import BankGuarantee, BankGuaranteePurpose, BankGuaranteeStatus
from uuid import UUID
from sqlalchemy import select

class BankGuaranteeRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, guarantee: BankGuarantee) -> BankGuarantee:
    self.session.add(guarantee)
    await self.session.flush()
    return guarantee

  async def get_by_id(self, guarantee_id: UUID, organization_id: UUID) -> BankGuarantee | None:
    result = await self.session.execute(
      select(BankGuarantee).where(BankGuarantee.id == guarantee_id, BankGuarantee.organization_id == organization_id)
    )
    return result.scalar_one_or_none()

  async def get_by_id_for_update(self, guarantee_id: UUID, organization_id: UUID) -> BankGuarantee | None:
    result = await self.session.execute(
      select(BankGuarantee)
      .where(BankGuarantee.id == guarantee_id, BankGuarantee.organization_id == organization_id)
      .with_for_update()
    )
    return result.scalar_one_or_none()

  async def list_by_project(self, organization_id: UUID, project_id: UUID) -> list[BankGuarantee]:
    result = await self.session.execute(
      select(BankGuarantee)
      .where(BankGuarantee.organization_id == organization_id, BankGuarantee.project_id == project_id)
      .order_by(BankGuarantee.status.asc(), BankGuarantee.expiry_date.asc())
    )
    return list(result.scalars().all())

  async def get_active_for_boq_version(self, organization_id: UUID, boq_version_id: UUID) -> BankGuarantee | None:
    result = await self.session.execute(
      select(BankGuarantee)
      .where(
        BankGuarantee.organization_id == organization_id, BankGuarantee.boq_version_id == boq_version_id,
        BankGuarantee.purpose == BankGuaranteePurpose.RETENTION,
        BankGuarantee.status == BankGuaranteeStatus.ACTIVE,
      )
      .order_by(BankGuarantee.expiry_date.desc())
      .limit(1)
    )
    return result.scalar_one_or_none()

  async def get_active_for_agreement(self, organization_id: UUID, agreement_id: UUID) -> BankGuarantee | None:
    result = await self.session.execute(
      select(BankGuarantee)
      .where(
        BankGuarantee.organization_id == organization_id, BankGuarantee.agreement_id == agreement_id,
        BankGuarantee.purpose == BankGuaranteePurpose.RETENTION,
        BankGuarantee.status == BankGuaranteeStatus.ACTIVE,
      )
      .order_by(BankGuarantee.expiry_date.desc())
      .limit(1)
    )
    return result.scalar_one_or_none()

  async def get_active_for_project(self, organization_id: UUID, project_id: UUID) -> list[BankGuarantee]:
    result = await self.session.execute(
      select(BankGuarantee).where(
        BankGuarantee.organization_id == organization_id, BankGuarantee.project_id == project_id,
        BankGuarantee.status == BankGuaranteeStatus.ACTIVE,
      )
    )
    return list(result.scalars().all())