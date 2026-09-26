from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.punch_lists.models import PunchList, PunchListItem, PunchListItemPhoto, PunchListItemStatus, PunchListStatus
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

class PunchListRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, punch_list: PunchList) -> PunchList:
    self.session.add(punch_list)
    await self.session.flush()
    return punch_list

  async def get_by_id(self, punch_list_id: UUID, organization_id: UUID) -> PunchList | None:
    result = await self.session.execute(
      select(PunchList)
      .where(PunchList.id == punch_list_id, PunchList.organization_id == organization_id)
      .options(selectinload(PunchList.items).selectinload(PunchListItem.photos))
    )
    return result.scalar_one_or_none()

  async def list_by_project(self, organization_id: UUID, project_id: UUID) -> list[PunchList]:
    result = await self.session.execute(
      select(PunchList)
      .where(PunchList.organization_id == organization_id, PunchList.project_id == project_id)
      .options(selectinload(PunchList.items).selectinload(PunchListItem.photos))
      .order_by(PunchList.inspection_date.desc())
    )
    return list(result.scalars().all())

  async def create_item(self, item: PunchListItem) -> PunchListItem:
    self.session.add(item)
    await self.session.flush()
    return item

  async def get_item(self, item_id: UUID, organization_id: UUID) -> PunchListItem | None:
    result = await self.session.execute(
      select(PunchListItem)
      .where(PunchListItem.id == item_id, PunchListItem.organization_id == organization_id)
      .options(selectinload(PunchListItem.photos))
    )
    return result.scalar_one_or_none()

  async def create_photo_link(self, photo: PunchListItemPhoto) -> PunchListItemPhoto:
    self.session.add(photo)
    await self.session.flush()
    return photo

  async def delete_photo_link(self, photo: PunchListItemPhoto) -> None:
    await self.session.delete(photo)
    await self.session.flush()

  async def get_photo_link(self, link_id: UUID, organization_id: UUID) -> PunchListItemPhoto | None:
    result = await self.session.execute(
      select(PunchListItemPhoto).where(
        PunchListItemPhoto.id == link_id, PunchListItemPhoto.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def get_open_lists_and_items_count(self, organization_id: UUID, project_id: UUID) -> tuple[int, int]:
    open_lists = await self.session.execute(
      select(func.count()).select_from(PunchList).where(
        PunchList.organization_id == organization_id, PunchList.project_id == project_id,
        PunchList.status == PunchListStatus.OPEN,
      )
    )
    open_items = await self.session.execute(
      select(func.count()).select_from(PunchListItem)
      .join(PunchList, PunchList.id == PunchListItem.punch_list_id)
      .where(
        PunchListItem.organization_id == organization_id, PunchList.project_id == project_id,
        PunchListItem.status.in_([PunchListItemStatus.OPEN, PunchListItemStatus.IN_PROGRESS]),
      )
    )
    return open_lists.scalar_one(), open_items.scalar_one()

  async def get_total_lists_count(self, organization_id: UUID, project_id: UUID) -> int:
    result = await self.session.execute(
      select(func.count()).select_from(PunchList).where(
        PunchList.organization_id == organization_id, PunchList.project_id == project_id,
      )
    )
    return result.scalar_one()

  async def get_subcontractor_open_items_count(
    self, organization_id: UUID, project_id: UUID, subcontractor_id: UUID,
  ) -> int:
    result = await self.session.execute(
      select(func.count()).select_from(PunchListItem)
      .join(PunchList, PunchList.id == PunchListItem.punch_list_id)
      .where(
        PunchListItem.organization_id == organization_id, PunchList.project_id == project_id,
        PunchListItem.assigned_to_subcontractor_id == subcontractor_id,
        PunchListItem.status.in_([PunchListItemStatus.OPEN, PunchListItemStatus.IN_PROGRESS]),
      )
    )
    return result.scalar_one()