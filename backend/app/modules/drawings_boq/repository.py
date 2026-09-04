from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.models import BOQItem, BOQItemType, BOQVersionStatus, BOQVersion, LabourRate, Drawing, DrawingElement, MaterialLibrary, MaterialNormalizationCache

class DrawingRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, drawing: Drawing) -> Drawing:
    self.session.add(drawing)
    await self.session.flush()
    return drawing

  async def get_by_id(self, drawing_id: UUID) -> Drawing | None:
    result = await self.session.execute(
      select(Drawing).where(Drawing.id == drawing_id)
    )
    return result.scalar_one_or_none()

  async def get_by_id_and_org(
    self,
    drawing_id: UUID,
    organization_id: UUID,
  ) -> Drawing | None:
    result = await self.session.execute(
      select(Drawing).where(
        Drawing.id == drawing_id,
        Drawing.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def list_by_project(
    self,
    organization_id: UUID,
    project_id: UUID,
  ) -> list[Drawing]:
    result = await self.session.execute(
      select(Drawing)
      .where(
        Drawing.organization_id == organization_id,
        Drawing.project_id == project_id,
      )
      .order_by(Drawing.created_at.desc())
    )
    return list(result.scalars().all())

  async def update(self, drawing: Drawing) -> Drawing:
    self.session.add(drawing)
    await self.session.flush()
    return drawing

class DrawingElementRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def bulk_create(
    self,
    elements: list[DrawingElement],
  ) -> list[DrawingElement]:
    self.session.add_all(elements)
    await self.session.flush()
    return elements

  async def list_by_drawing(
    self,
    drawing_id: UUID,
  ) -> list[DrawingElement]:
    result = await self.session.execute(
      select(DrawingElement)
      .where(DrawingElement.drawing_id == drawing_id)
      .order_by(DrawingElement.ifc_type.asc())
    )
    return list(result.scalars().all())

class BOQVersionRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, boq_version: BOQVersion) -> BOQVersion:
    self.session.add(boq_version)
    await self.session.flush()
    return boq_version

  async def get_by_id_and_org(
    self,
    boq_version_id: UUID,
    organization_id: UUID,
  ) -> BOQVersion | None:
    result = await self.session.execute(
      select(BOQVersion).where(
        BOQVersion.id == boq_version_id,
        BOQVersion.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def list_by_project(
    self,
    organization_id: UUID,
    project_id: UUID,
  ) -> list[BOQVersion]:
    result = await self.session.execute(
      select(BOQVersion)
      .where(
        BOQVersion.organization_id == organization_id,
        BOQVersion.project_id == project_id,
      )
      .order_by(BOQVersion.created_at.desc())
    )
    return list(result.scalars().all())
  
  async def update(self, boq_version: BOQVersion) -> BOQVersion:
    self.session.add(boq_version)
    await self.session.flush()
    return boq_version

  async def supersede_active_for_project(
    self,
    organization_id: UUID,
    project_id: UUID,
    exclude_id: UUID,
  ) -> None:
    result = await self.session.execute(
      select(BOQVersion).where(
        BOQVersion.organization_id == organization_id,
        BOQVersion.project_id == project_id,
        BOQVersion.status == BOQVersionStatus.ACTIVE,
        BOQVersion.id != exclude_id,
      )
    )
    for version in result.scalars().all():
      version.status = BOQVersionStatus.SUPERSEDED
    await self.session.flush()

class BOQItemRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def bulk_create(self, items: list[BOQItem]) -> list[BOQItem]:
    self.session.add_all(items)
    await self.session.flush()
    return items

  async def create(self, item: BOQItem) -> BOQItem:
    self.session.add(item)
    await self.session.flush()
    return item
  
  async def get_by_id_and_org_for_update(
    self,
    item_id: UUID,
    organization_id: UUID,
  ) -> BOQItem | None:
    result = await self.session.execute(
      select(BOQItem)
      .where(
        BOQItem.id == item_id,
        BOQItem.organization_id == organization_id,
      )
      .with_for_update()
    )
    return result.scalar_one_or_none()

  async def list_by_version(
    self,
    boq_version_id: UUID,
  ) -> list[BOQItem]:
    result = await self.session.execute(
      select(BOQItem)
      .where(BOQItem.boq_version_id == boq_version_id)
      .order_by(BOQItem.material_name.asc())
    )
    return list(result.scalars().all())

  async def update(self, item: BOQItem) -> BOQItem:
    self.session.add(item)
    await self.session.flush()
    return item

class MaterialLibraryRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def get_by_raw_text(
    self,
    organization_id: UUID,
    raw_text: str,
  ) -> MaterialLibrary | None:
    result = await self.session.execute(
      select(MaterialLibrary).where(
        MaterialLibrary.organization_id == organization_id,
        MaterialLibrary.raw_text == raw_text,
      )
    )
    return result.scalar_one_or_none()

  async def list_by_org(
    self,
    organization_id: UUID,
  ) -> list[MaterialLibrary]:
    result = await self.session.execute(
      select(MaterialLibrary)
      .where(MaterialLibrary.organization_id == organization_id)
      .order_by(MaterialLibrary.normalized_name.asc())
    )
    return list(result.scalars().all())

  async def create(
    self,
    entry: MaterialLibrary,
  ) -> MaterialLibrary:
    self.session.add(entry)
    await self.session.flush()
    return entry
  
  async def get_by_id_and_org(
    self,
    entry_id: UUID,
    organization_id: UUID,
  ) -> MaterialLibrary | None:
    result = await self.session.execute(
      select(MaterialLibrary).where(
        MaterialLibrary.id == entry_id,
        MaterialLibrary.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def update(self, entry: MaterialLibrary) -> MaterialLibrary:
    self.session.add(entry)
    await self.session.flush()
    return entry

class MaterialNormalizationCacheRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def get_by_hash(
    self,
    input_hash: str,
  ) -> MaterialNormalizationCache | None:
    result = await self.session.execute(
      select(MaterialNormalizationCache).where(
        MaterialNormalizationCache.input_hash == input_hash
      )
    )
    return result.scalar_one_or_none()

  async def create(
    self,
    entry: MaterialNormalizationCache,
  ) -> MaterialNormalizationCache:
    self.session.add(entry)
    await self.session.flush()
    return entry
  
class LabourRateRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def list_by_org(self, organization_id: UUID) -> list[LabourRate]:
    result = await self.session.execute(
      select(LabourRate)
      .where(LabourRate.organization_id == organization_id)
      .order_by(LabourRate.trade.asc())
    )
    return list(result.scalars().all())

  async def get_by_id_and_org(
    self,
    rate_id: UUID,
    organization_id: UUID,
  ) -> LabourRate | None:
    result = await self.session.execute(
      select(LabourRate).where(
        LabourRate.id == rate_id,
        LabourRate.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def get_by_trade(
    self,
    organization_id: UUID,
    trade: str,
  ) -> LabourRate | None:
    result = await self.session.execute(
      select(LabourRate).where(
        LabourRate.organization_id == organization_id,
        LabourRate.trade == trade,
      )
    )
    return result.scalar_one_or_none()

  async def create(self, rate: LabourRate) -> LabourRate:
    self.session.add(rate)
    await self.session.flush()
    return rate

  async def update(self, rate: LabourRate) -> LabourRate:
    self.session.add(rate)
    await self.session.flush()
    return rate