from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import select, func
from app.modules.procurement.models import ProcurementRequest, ProcurementStatus

class ProcurementRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def list_requests(
    self,
    organization_id: UUID,
    project_id: UUID | None = None,
    status: ProcurementStatus | None = None,
    skip: int = 0,
    limit: int = 100,
  ) -> list[ProcurementRequest]:
    q = select(ProcurementRequest).where(
      ProcurementRequest.organization_id == organization_id,
    )
    if project_id is not None:
      q = q.where(ProcurementRequest.project_id == project_id)
    if status is not None:
      q = q.where(ProcurementRequest.status == status)
    q = q.order_by(ProcurementRequest.created_at.desc())
    q = q.offset(skip).limit(limit)
    result = await self.session.execute(q)
    return list(result.scalars().all())

  async def get_by_id(
    self, request_id: UUID, organization_id: UUID,
  ) -> ProcurementRequest | None:
    result = await self.session.execute(
      select(ProcurementRequest).where(
        ProcurementRequest.id == request_id,
        ProcurementRequest.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def create(self, req: ProcurementRequest) -> ProcurementRequest:
    self.session.add(req)
    await self.session.flush()
    return req
  
  async def get_organization_summary(
    self, organization_id: UUID,
  ) -> dict:
    result = await self.session.execute(
      select(
        func.coalesce(
          func.sum(ProcurementRequest.estimated_amount), 0,
        ).label("total_committed_amount"),
        func.count(ProcurementRequest.id).label("request_count"),
      ).where(
        ProcurementRequest.organization_id == organization_id,
        ProcurementRequest.status.in_(
          [ProcurementStatus.APPROVED, ProcurementStatus.ORDERED],
        ),
      )
    )
    row = result.one()
    return {
      "total_committed_amount": row.total_committed_amount,
      "request_count": row.request_count,
    }