from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.modules.site_progress.models import SiteLogEntry
from datetime import date
from decimal import Decimal
from sqlalchemy import func, select
from app.modules.labour.models import LabourAttendance, LabourDeployment
from app.modules.material_stock.models import MaterialIssue
from app.modules.whatsapp.models import SitePhoto

class SiteProgressRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def list_logs(
    self,
    organization_id: UUID,
    project_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
  ) -> list[SiteLogEntry]:
    q = select(SiteLogEntry).where(
      SiteLogEntry.organization_id == organization_id,
    )
    if project_id is not None:
      q = q.where(SiteLogEntry.project_id == project_id)
    q = q.order_by(SiteLogEntry.log_date.desc(), SiteLogEntry.created_at.desc())
    q = q.offset(skip).limit(limit)
    result = await self.session.execute(q)
    return list(result.scalars().all())

  async def get_by_id(
    self, log_id: UUID, organization_id: UUID,
  ) -> SiteLogEntry | None:
    result = await self.session.execute(
      select(SiteLogEntry).where(
        SiteLogEntry.id == log_id,
        SiteLogEntry.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def create(self, entry: SiteLogEntry) -> SiteLogEntry:
    self.session.add(entry)
    await self.session.flush()
    return entry

  async def delete(self, entry: SiteLogEntry) -> None:
    await self.session.delete(entry)
    await self.session.flush()
    
  async def list_logs_for_date(
    self, organization_id: UUID, project_id: UUID, log_date: date,
  ) -> list[SiteLogEntry]:
    result = await self.session.execute(
      select(SiteLogEntry)
      .where(
        SiteLogEntry.organization_id == organization_id,
        SiteLogEntry.project_id == project_id,
        SiteLogEntry.log_date == log_date,
      )
      .order_by(SiteLogEntry.created_at.asc())
    )
    return list(result.scalars().all())

  async def get_manpower_for_date(
    self, organization_id: UUID, project_id: UUID, on_date: date,
  ) -> list[tuple[str, Decimal]]:
    result = await self.session.execute(
      select(LabourDeployment.trade, func.coalesce(func.sum(LabourAttendance.units_present), 0))
      .join(LabourDeployment, LabourDeployment.id == LabourAttendance.deployment_id)
      .where(
        LabourAttendance.organization_id == organization_id,
        LabourAttendance.project_id == project_id,
        LabourAttendance.attendance_date == on_date,
      )
      .group_by(LabourDeployment.trade)
      .order_by(LabourDeployment.trade.asc())
    )
    return [(trade, Decimal(str(units))) for trade, units in result.all() if Decimal(str(units)) > 0]

  async def list_issues_for_date(
    self, organization_id: UUID, project_id: UUID, on_date: date,
  ) -> list[MaterialIssue]:
    result = await self.session.execute(
      select(MaterialIssue)
      .where(
        MaterialIssue.organization_id == organization_id,
        MaterialIssue.project_id == project_id,
        MaterialIssue.issue_date == on_date,
      )
      .order_by(MaterialIssue.created_at.asc())
    )
    return list(result.scalars().all())

  async def list_photos_for_date(
    self, organization_id: UUID, project_id: UUID, on_date: date, limit: int = 12,
  ) -> tuple[list[SitePhoto], int]:
    base = (
      SitePhoto.organization_id == organization_id,
      SitePhoto.project_id == project_id,
      SitePhoto.photo_date == on_date,
    )
    total = (await self.session.execute(select(func.count(SitePhoto.id)).where(*base))).scalar_one()
    result = await self.session.execute(
      select(SitePhoto).where(*base).order_by(SitePhoto.created_at.asc()).limit(limit)
    )
    return list(result.scalars().all()), int(total)