from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.change_orders.models import ChangeOrder, ChangeOrderLineItem, ChangeOrderStatus
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from app.modules.drawings_boq.models import BOQItem

class ChangeOrderRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, change_order: ChangeOrder) -> ChangeOrder:
    self.session.add(change_order)
    await self.session.flush()
    return change_order

  async def create_line_items(self, items: list[ChangeOrderLineItem]) -> None:
    self.session.add_all(items)
    await self.session.flush()

  async def get_by_id(self, change_order_id: UUID, organization_id: UUID) -> ChangeOrder | None:
    result = await self.session.execute(
      select(ChangeOrder)
      .where(ChangeOrder.id == change_order_id, ChangeOrder.organization_id == organization_id)
      .options(selectinload(ChangeOrder.line_items))
    )
    return result.scalar_one_or_none()

  async def get_by_id_for_update(self, change_order_id: UUID, organization_id: UUID) -> ChangeOrder | None:
    result = await self.session.execute(
      select(ChangeOrder)
      .where(ChangeOrder.id == change_order_id, ChangeOrder.organization_id == organization_id)
      .options(selectinload(ChangeOrder.line_items))
      .with_for_update()
    )
    return result.scalar_one_or_none()

  async def list_by_project(self, organization_id: UUID, project_id: UUID) -> list[ChangeOrder]:
    result = await self.session.execute(
      select(ChangeOrder)
      .where(ChangeOrder.organization_id == organization_id, ChangeOrder.project_id == project_id)
      .options(selectinload(ChangeOrder.line_items))
      .order_by(ChangeOrder.change_order_number.desc())
    )
    return list(result.scalars().all())

  async def get_max_number(self, organization_id: UUID, project_id: UUID) -> int:
    result = await self.session.execute(
      select(func.max(ChangeOrder.change_order_number)).where(
        ChangeOrder.organization_id == organization_id, ChangeOrder.project_id == project_id,
      )
    )
    return result.scalar() or 0

  async def get_approval_summary(self, organization_id: UUID, project_id: UUID) -> tuple[int, float, int]:
    approved = await self.session.execute(
      select(func.count(), func.coalesce(func.sum(ChangeOrder.value_impact), 0)).where(
        ChangeOrder.organization_id == organization_id, ChangeOrder.project_id == project_id,
        ChangeOrder.status == ChangeOrderStatus.APPROVED,
      )
    )
    approved_count, approved_total = approved.one()
    draft_count = await self.session.execute(
      select(func.count()).select_from(ChangeOrder).where(
        ChangeOrder.organization_id == organization_id, ChangeOrder.project_id == project_id,
        ChangeOrder.status == ChangeOrderStatus.DRAFT,
      )
    )
    return approved_count, float(approved_total), draft_count.scalar_one()

  async def get_boq_item(self, boq_item_id: UUID, organization_id: UUID, boq_version_id: UUID) -> BOQItem | None:
    result = await self.session.execute(
      select(BOQItem).where(
        BOQItem.id == boq_item_id, BOQItem.organization_id == organization_id,
        BOQItem.boq_version_id == boq_version_id,
      )
    )
    return result.scalar_one_or_none()

  async def create_boq_item(self, boq_item: BOQItem) -> BOQItem:
    self.session.add(boq_item)
    await self.session.flush()
    return boq_item