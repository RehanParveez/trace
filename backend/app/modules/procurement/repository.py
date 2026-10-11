from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from collections import defaultdict
from datetime import date
from decimal import Decimal
from sqlalchemy import select, func
from app.modules.procurement.models import ProcurementDelivery, ProcurementRequest, ProcurementStatus

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

  async def get_by_id_for_update(
    self, request_id: UUID, organization_id: UUID,
  ) -> ProcurementRequest | None:
    result = await self.session.execute(
      select(ProcurementRequest)
      .where(
        ProcurementRequest.id == request_id,
        ProcurementRequest.organization_id == organization_id,
      )
      .with_for_update()
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
    
  async def get_status_counts(
    self,
    organization_id: UUID,
    project_id: UUID | None = None,
  ) -> dict[ProcurementStatus, int]:
    filters = [ProcurementRequest.organization_id == organization_id]
    if project_id is not None:
      filters.append(ProcurementRequest.project_id == project_id)

    result = await self.session.execute(
      select(ProcurementRequest.status, func.count(ProcurementRequest.id))
      .where(*filters)
      .group_by(ProcurementRequest.status)
    )
    return {status: count for status, count in result.all()}
  
  async def create_delivery(self, delivery: ProcurementDelivery) -> ProcurementDelivery:
    self.session.add(delivery)
    await self.session.flush()
    return delivery

  async def get_delivery_for_update(
    self, delivery_id: UUID, organization_id: UUID,
  ) -> ProcurementDelivery | None:
    result = await self.session.execute(
      select(ProcurementDelivery)
      .where(
        ProcurementDelivery.id == delivery_id,
        ProcurementDelivery.organization_id == organization_id,
      )
      .with_for_update()
    )
    return result.scalar_one_or_none()

  async def get_delivered_quantity(self, request_id: UUID, organization_id: UUID) -> Decimal:
    result = await self.session.execute(
      select(func.coalesce(func.sum(ProcurementDelivery.quantity), 0)).where(
        ProcurementDelivery.organization_id == organization_id,
        ProcurementDelivery.request_id == request_id,
        ProcurementDelivery.voided_at.is_(None),
      )
    )
    return Decimal(str(result.scalar_one()))

  async def get_delivered_quantities(
    self, organization_id: UUID, request_ids: list[UUID],
  ) -> dict[UUID, Decimal]:
    if not request_ids:
      return {}
    result = await self.session.execute(
      select(ProcurementDelivery.request_id, func.sum(ProcurementDelivery.quantity))
      .where(
        ProcurementDelivery.organization_id == organization_id,
        ProcurementDelivery.request_id.in_(request_ids),
        ProcurementDelivery.voided_at.is_(None),
      )
      .group_by(ProcurementDelivery.request_id)
    )
    return {rid: Decimal(str(total)) for rid, total in result.all()}

  async def has_deliveries(self, request_id: UUID, organization_id: UUID) -> bool:
    result = await self.session.execute(
      select(func.count(ProcurementDelivery.id)).where(
        ProcurementDelivery.organization_id == organization_id,
        ProcurementDelivery.request_id == request_id,
        ProcurementDelivery.voided_at.is_(None),
      )
    )
    return result.scalar_one() > 0

  async def list_deliveries(
    self,
    organization_id: UUID,
    *,
    request_id: UUID | None = None,
    project_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    include_voided: bool = True,
  ) -> list[tuple[ProcurementDelivery, ProcurementRequest]]:
    
    q = (
      select(ProcurementDelivery, ProcurementRequest)
      .join(ProcurementRequest, ProcurementRequest.id == ProcurementDelivery.request_id)
      .where(ProcurementDelivery.organization_id == organization_id)
    )
    if request_id is not None:
      q = q.where(ProcurementDelivery.request_id == request_id)
    if project_id is not None:
      q = q.where(ProcurementDelivery.project_id == project_id)
    if date_from is not None:
      q = q.where(ProcurementDelivery.received_date >= date_from)
    if date_to is not None:
      q = q.where(ProcurementDelivery.received_date <= date_to)
    if not include_voided:
      q = q.where(ProcurementDelivery.voided_at.is_(None))
    q = q.order_by(ProcurementDelivery.received_date.desc(), ProcurementDelivery.created_at.desc())
    result = await self.session.execute(q)
    return [(delivery, request) for delivery, request in result.all()]

  async def get_project_materials_money(
    self, organization_id: UUID, project_id: UUID,
  ) -> tuple[Decimal, Decimal]:
    requests = (await self.session.execute(
      select(ProcurementRequest).where(
        ProcurementRequest.organization_id == organization_id,
        ProcurementRequest.project_id == project_id,
      )
      
    )).scalars().all()
    deliveries = (await self.session.execute(
      select(ProcurementDelivery).where(
        ProcurementDelivery.organization_id == organization_id,
        ProcurementDelivery.project_id == project_id,
        ProcurementDelivery.voided_at.is_(None),
      )
    )).scalars().all()

    by_request: dict[UUID, list[ProcurementDelivery]] = defaultdict(list)
    for delivery in deliveries:
      by_request[delivery.request_id].append(delivery)

    received = Decimal("0")
    committed = Decimal("0")
    for req in requests:
      estimate = req.estimated_amount
      rows = by_request.get(req.id, [])
      delivered_qty = sum((d.quantity for d in rows), Decimal("0"))
      for d in rows:
        if d.amount is not None:
          received += d.amount
        elif estimate is not None and req.quantity > 0:
          received += estimate * d.quantity / req.quantity
      if not rows and req.status == ProcurementStatus.RECEIVED and estimate is not None:
        received += estimate
      if req.status in (ProcurementStatus.APPROVED, ProcurementStatus.ORDERED) and estimate is not None and req.quantity > 0:
        remaining_share = max(Decimal("0"), Decimal("1") - delivered_qty / req.quantity)
        committed += estimate * remaining_share
    return received.quantize(Decimal("0.01")), committed.quantize(Decimal("0.01"))