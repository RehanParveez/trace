from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.labour.models import LabourSource, LabourAdvance, LabourAttendance, LabourDeployment, LabourPayment, LabourWorker
from uuid import UUID
from sqlalchemy import func, select
from datetime import date

class LabourRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create_source(self, source: LabourSource) -> LabourSource:
    self.session.add(source)
    await self.session.flush()
    return source

  async def get_source(self, source_id: UUID, organization_id: UUID) -> LabourSource | None:
    result = await self.session.execute(
      select(LabourSource).where(LabourSource.id == source_id, LabourSource.organization_id == organization_id)
    )
    return result.scalar_one_or_none()

  async def list_sources(self, organization_id: UUID) -> list[LabourSource]:
    result = await self.session.execute(
      select(LabourSource).where(LabourSource.organization_id == organization_id).order_by(LabourSource.name.asc())
    )
    return list(result.scalars().all())

  async def create_worker(self, worker: LabourWorker) -> LabourWorker:
    self.session.add(worker)
    await self.session.flush()
    return worker

  async def get_worker(self, worker_id: UUID, organization_id: UUID) -> LabourWorker | None:
    result = await self.session.execute(
      select(LabourWorker).where(LabourWorker.id == worker_id, LabourWorker.organization_id == organization_id)
    )
    return result.scalar_one_or_none()

  async def list_workers(self, organization_id: UUID, source_id: UUID | None = None) -> list[LabourWorker]:
    query = select(LabourWorker).where(LabourWorker.organization_id == organization_id)
    if source_id is not None:
      query = query.where(LabourWorker.source_id == source_id)
    result = await self.session.execute(query.order_by(LabourWorker.name.asc()))
    return list(result.scalars().all())

  async def create_deployment(self, deployment: LabourDeployment) -> LabourDeployment:
    self.session.add(deployment)
    await self.session.flush()
    return deployment

  async def get_deployment(self, deployment_id: UUID, organization_id: UUID) -> LabourDeployment | None:
    result = await self.session.execute(
      select(LabourDeployment).where(
        LabourDeployment.id == deployment_id, LabourDeployment.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def list_deployments(self, organization_id: UUID, project_id: UUID) -> list[LabourDeployment]:
    result = await self.session.execute(
      select(LabourDeployment)
      .where(LabourDeployment.organization_id == organization_id, LabourDeployment.project_id == project_id)
      .order_by(LabourDeployment.status.asc(), LabourDeployment.trade.asc())
    )
    return list(result.scalars().all())

  async def has_attendance(self, deployment_id: UUID) -> bool:
    result = await self.session.execute(
      select(func.count()).select_from(LabourAttendance).where(LabourAttendance.deployment_id == deployment_id)
    )
    return result.scalar_one() > 0

  async def get_attendance_for_deployment_date(
    self, deployment_id: UUID, attendance_date: date,
  ) -> LabourAttendance | None:
    result = await self.session.execute(
      select(LabourAttendance).where(
        LabourAttendance.deployment_id == deployment_id, LabourAttendance.attendance_date == attendance_date,
      )
    )
    return result.scalar_one_or_none()

  async def list_attendance(
    self, organization_id: UUID, project_id: UUID, period_start: date | None, period_end: date | None,
  ) -> list[LabourAttendance]:
    query = select(LabourAttendance).where(
      LabourAttendance.organization_id == organization_id, LabourAttendance.project_id == project_id,
    )
    if period_start is not None:
      query = query.where(LabourAttendance.attendance_date >= period_start)
    if period_end is not None:
      query = query.where(LabourAttendance.attendance_date <= period_end)
    result = await self.session.execute(query.order_by(LabourAttendance.attendance_date.desc()))
    return list(result.scalars().all())

  async def get_accrued_cost(
    self, organization_id: UUID, project_id: UUID, period_start: date, period_end: date,
    source_id: UUID | None = None, worker_id: UUID | None = None,
  ) -> list[tuple[str, float]]:
    query = (
      select(
        LabourDeployment.trade,
        func.sum(LabourAttendance.units_present * LabourDeployment.daily_rate).label("cost"),
      )
      .join(LabourDeployment, LabourDeployment.id == LabourAttendance.deployment_id)
      .where(
        LabourAttendance.organization_id == organization_id,
        LabourAttendance.project_id == project_id,
        LabourAttendance.attendance_date >= period_start,
        LabourAttendance.attendance_date <= period_end,
      )
      .group_by(LabourDeployment.trade)
    )
    if source_id is not None:
      query = query.where(LabourDeployment.source_id == source_id)
    if worker_id is not None:
      query = query.where(LabourDeployment.worker_id == worker_id)
    result = await self.session.execute(query)
    return [(row.trade, row.cost or 0) for row in result.all()]

  async def create_advance(self, advance: LabourAdvance) -> LabourAdvance:
    self.session.add(advance)
    await self.session.flush()
    return advance

  async def list_advances(self, organization_id: UUID, project_id: UUID) -> list[LabourAdvance]:
    result = await self.session.execute(
      select(LabourAdvance)
      .where(LabourAdvance.organization_id == organization_id, LabourAdvance.project_id == project_id)
      .order_by(LabourAdvance.advance_date.desc())
    )
    return list(result.scalars().all())

  async def create_payment(self, payment: LabourPayment) -> LabourPayment:
    self.session.add(payment)
    await self.session.flush()
    return payment

  async def list_payments(self, organization_id: UUID, project_id: UUID) -> list[LabourPayment]:
    result = await self.session.execute(
      select(LabourPayment)
      .where(LabourPayment.organization_id == organization_id, LabourPayment.project_id == project_id)
      .order_by(LabourPayment.payment_date.desc())
    )
    return list(result.scalars().all())

  async def get_advance_balance(
    self, organization_id: UUID, project_id: UUID, source_id: UUID, worker_id: UUID | None,
  ) -> tuple[float, float]:
    advance_query = select(func.coalesce(func.sum(LabourAdvance.amount), 0)).where(
      LabourAdvance.organization_id == organization_id, LabourAdvance.project_id == project_id,
      LabourAdvance.source_id == source_id, LabourAdvance.worker_id == worker_id,
    )
    payment_query = select(func.coalesce(func.sum(LabourPayment.advance_recovered_amount), 0)).where(
      LabourPayment.organization_id == organization_id, LabourPayment.project_id == project_id,
      LabourPayment.source_id == source_id, LabourPayment.worker_id == worker_id,
    )
    total_advances = (await self.session.execute(advance_query)).scalar_one()
    total_recovered = (await self.session.execute(payment_query)).scalar_one()
    return float(total_advances), float(total_recovered)

  async def get_project_labour_totals(
    self, organization_id: UUID, project_id: UUID,
  ) -> tuple[float, float]:
    advance_total = (await self.session.execute(
      select(func.coalesce(func.sum(LabourAdvance.amount), 0)).where(
        LabourAdvance.organization_id == organization_id, LabourAdvance.project_id == project_id,
      )
    )).scalar_one()
    payment_total = (await self.session.execute(
      select(func.coalesce(func.sum(LabourPayment.advance_recovered_amount), 0)).where(
        LabourPayment.organization_id == organization_id, LabourPayment.project_id == project_id,
      )
    )).scalar_one()
    return float(advance_total), float(payment_total)