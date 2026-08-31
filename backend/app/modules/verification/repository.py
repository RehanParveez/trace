from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.verification.models import PhotoBOQLink, ProgressClaim, ProgressClaimStatus

class ProgressClaimRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(
    self,
    claim: ProgressClaim,
  ) -> ProgressClaim:
    self.session.add(claim)
    await self.session.flush()
    return claim

  async def get_by_id_and_org(
    self,
    claim_id: UUID,
    organization_id: UUID,
  ) -> ProgressClaim | None:
    result = await self.session.execute(
      select(ProgressClaim).where(
        ProgressClaim.id == claim_id,
        ProgressClaim.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def list_by_org(
    self,
    organization_id: UUID,
    *,
    project_id: UUID | None = None,
    status: ProgressClaimStatus | None = None,
    skip: int = 0,
    limit: int = 100,
  ) -> list[ProgressClaim]:
    query = select(ProgressClaim).where(
      ProgressClaim.organization_id == organization_id,
    )

    if project_id is not None:
      query = query.where(
        ProgressClaim.project_id == project_id,
      )

    if status is not None:
      query = query.where(
        ProgressClaim.status == status,
      )

    query = (
      query
      .order_by(
        ProgressClaim.claim_date.desc(),
        ProgressClaim.created_at.desc(),
      )
      .offset(skip)
      .limit(limit)
    )

    result = await self.session.execute(query)

    return list(result.scalars().all())

  async def update(
    self,
    claim: ProgressClaim,
  ) -> ProgressClaim:
    self.session.add(claim)
    await self.session.flush()
    return claim

class PhotoBOQLinkRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(
    self,
    link: PhotoBOQLink,
  ) -> PhotoBOQLink:
    self.session.add(link)
    await self.session.flush()
    return link

  async def get_by_id_and_org(
    self,
    link_id: UUID,
    organization_id: UUID,
  ) -> PhotoBOQLink | None:
    result = await self.session.execute(
      select(PhotoBOQLink).where(
        PhotoBOQLink.id == link_id,
        PhotoBOQLink.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def get_existing(
    self,
    progress_claim_id: UUID,
    site_photo_id: UUID,
    boq_item_id: UUID,
  ) -> PhotoBOQLink | None:
    result = await self.session.execute(
      select(PhotoBOQLink).where(
        PhotoBOQLink.progress_claim_id == progress_claim_id,
        PhotoBOQLink.site_photo_id == site_photo_id,
        PhotoBOQLink.boq_item_id == boq_item_id,
      )
    )
    return result.scalar_one_or_none()

  async def list_by_org(
    self,
    organization_id: UUID,
    *,
    project_id: UUID | None = None,
    progress_claim_id: UUID | None = None,
    site_photo_id: UUID | None = None,
    boq_item_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
  ) -> list[PhotoBOQLink]:
    query = select(PhotoBOQLink).where(
      PhotoBOQLink.organization_id == organization_id,
    )

    if project_id is not None:
      query = query.where(
        PhotoBOQLink.project_id == project_id,
      )

    if progress_claim_id is not None:
      query = query.where(
        PhotoBOQLink.progress_claim_id == progress_claim_id,
      )

    if site_photo_id is not None:
      query = query.where(
        PhotoBOQLink.site_photo_id == site_photo_id,
      )

    if boq_item_id is not None:
      query = query.where(
        PhotoBOQLink.boq_item_id == boq_item_id,
      )

    query = (
      query
      .order_by(PhotoBOQLink.created_at.desc())
      .offset(skip)
      .limit(limit)
    )

    result = await self.session.execute(query)
    return list(result.scalars().all())

  async def delete(
    self,
    link: PhotoBOQLink,
  ) -> None:
    await self.session.delete(link)
    await self.session.flush()