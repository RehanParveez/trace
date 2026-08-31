from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import TraceException
from app.modules.drawings_boq.models import BOQItem, BOQVersion, BOQItemStatus
from app.modules.projects.repository import ProjectRepository
from app.modules.verification.models import PhotoBOQLink, ProgressClaim, ProgressClaimStatus
from app.modules.whatsapp.models import SitePhoto
from app.modules.verification.repository import PhotoBOQLinkRepository, ProgressClaimRepository
from app.modules.verification.schemas import PhotoBOQLinkCreateRequest, ProgressClaimCreateRequest, ProgressClaimReviewRequest, ProgressClaimUpdateRequest

class VerificationService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.claims = ProgressClaimRepository(session)
    self.photo_boq_links = PhotoBOQLinkRepository(session)
    self.projects = ProjectRepository(session)

  async def _get_project(
    self,
    organization_id: UUID,
    project_id: UUID,
  ):
    project = await self.projects.get_by_id_and_org(
      project_id,
      organization_id,
    )

    if project is None:
      raise TraceException(
        "Project not found in this organization.",
        status_code=404,
        code="PROJECT_NOT_FOUND",
      )

    return project

  async def _get_boq_item(
    self,
    organization_id: UUID,
    project_id: UUID,
    boq_item_id: UUID,
) -> BOQItem:
    result = await self.session.execute(
      select(BOQItem)
      .join(
        BOQVersion,
        BOQItem.boq_version_id == BOQVersion.id,
      )
      .where(
        BOQItem.id == boq_item_id,
        BOQItem.organization_id == organization_id,
        BOQVersion.project_id == project_id,
        BOQItem.status == BOQItemStatus.APPROVED,
       )
    )
    item = result.scalar_one_or_none()
    if item is None:
      raise TraceException(
        "BOQ item not found, does not belong to this project, or is not approved.",
        status_code=404,
        code="BOQ_ITEM_NOT_FOUND",
      )
    return item

  async def get_claim(
    self,
    organization_id: UUID,
    claim_id: UUID,
  ) -> ProgressClaim:
    claim = await self.claims.get_by_id_and_org(
      claim_id,
      organization_id,
    )

    if claim is None:
      raise TraceException(
        "Progress claim not found.",
        status_code=404,
        code="PROGRESS_CLAIM_NOT_FOUND",
      )
    return claim

  async def create_claim(
    self,
    organization_id: UUID,
    user_id: UUID,
    payload: ProgressClaimCreateRequest,
  ) -> ProgressClaim:
    await self._get_project(
      organization_id,
      payload.project_id,
    )

    await self._get_boq_item(
      organization_id,
      payload.project_id,
      payload.boq_item_id,
    )

    claim = ProgressClaim(
      id=uuid4(),
      organization_id=organization_id,
      project_id=payload.project_id,
      boq_item_id=payload.boq_item_id,
      claim_date=payload.claim_date,
      claimed_quantity=payload.claimed_quantity,
      claimed_percentage=payload.claimed_percentage,
      notes=payload.notes,
      status=ProgressClaimStatus.DRAFT,
      version=1,
    )

    claim = await self.claims.create(claim)

    await self.session.commit()
    await self.session.refresh(claim)

    return claim

  async def update_claim(
    self,
    organization_id: UUID,
    claim_id: UUID,
    payload: ProgressClaimUpdateRequest,
  ) -> ProgressClaim:
    claim = await self.get_claim(
      organization_id,
      claim_id,
    )

    if claim.status != ProgressClaimStatus.DRAFT:
      raise TraceException(
        "Only draft progress claims can be updated.",
        status_code=409,
        code="PROGRESS_CLAIM_NOT_DRAFT",
      )

    if claim.version != payload.version:
      raise TraceException(
        "The progress claim was modified by another user.",
        status_code=409,
        code="CONCURRENT_MODIFICATION",
      )

    if payload.claimed_quantity is not None:
      claim.claimed_quantity = payload.claimed_quantity

    if payload.claimed_percentage is not None:
      claim.claimed_percentage = payload.claimed_percentage

    if payload.claim_date is not None:
      claim.claim_date = payload.claim_date

    if payload.notes is not None:
      claim.notes = payload.notes

    claim.version += 1

    await self.claims.update(claim)
    await self.session.commit()
    await self.session.refresh(claim)

    return claim

  async def submit_claim(
    self,
    organization_id: UUID,
    claim_id: UUID,
    user_id: UUID,
  ) -> ProgressClaim:
    claim = await self.get_claim(
      organization_id,
      claim_id,
    )

    if claim.status != ProgressClaimStatus.DRAFT:
      raise TraceException(
        "Only draft progress claims can be submitted.",
        status_code=409,
        code="PROGRESS_CLAIM_NOT_DRAFT",
      )

    claim.status = ProgressClaimStatus.SUBMITTED
    claim.submitted_by = user_id
    claim.submitted_at = datetime.now(timezone.utc)
    claim.version += 1

    await self.claims.update(claim)
    await self.session.commit()
    await self.session.refresh(claim)

    return claim

  async def approve_claim(
    self,
    organization_id: UUID,
    claim_id: UUID,
    user_id: UUID,
    payload: ProgressClaimReviewRequest,
  ) -> ProgressClaim:
    claim = await self.get_claim(
      organization_id,
      claim_id,
    )

    if claim.status != ProgressClaimStatus.SUBMITTED:
      raise TraceException(
        "Only submitted progress claims can be approved.",
        status_code=409,
        code="PROGRESS_CLAIM_NOT_SUBMITTED",
      )

    if claim.version != payload.version:
      raise TraceException(
        "The progress claim was modified by another user.",
        status_code=409,
        code="CONCURRENT_MODIFICATION",
      )

    claim.status = ProgressClaimStatus.APPROVED
    claim.reviewed_by = user_id
    claim.reviewed_at = datetime.now(timezone.utc)
    claim.review_note = payload.note
    claim.version += 1

    await self.claims.update(claim)
    await self.session.commit()
    await self.session.refresh(claim)

    return claim

  async def reject_claim(
    self,
    organization_id: UUID,
    claim_id: UUID,
    user_id: UUID,
    payload: ProgressClaimReviewRequest,
  ) -> ProgressClaim:
    claim = await self.get_claim(
      organization_id,
      claim_id,
    )

    if claim.status != ProgressClaimStatus.SUBMITTED:
      raise TraceException(
        "Only submitted progress claims can be rejected.",
        status_code=409,
        code="PROGRESS_CLAIM_NOT_SUBMITTED",
      )

    if claim.version != payload.version:
      raise TraceException(
        "The progress claim was modified by another user.",
        status_code=409,
        code="CONCURRENT_MODIFICATION",
      )

    claim.status = ProgressClaimStatus.REJECTED
    claim.reviewed_by = user_id
    claim.reviewed_at = datetime.now(timezone.utc)
    claim.review_note = payload.note
    claim.version += 1

    await self.claims.update(claim)
    await self.session.commit()
    await self.session.refresh(claim)

    return claim

  async def list_claims(
    self,
    organization_id: UUID,
    *,
    project_id: UUID | None = None,
    status: ProgressClaimStatus | None = None,
    skip: int = 0,
    limit: int = 100,
  ) -> list[ProgressClaim]:
    return await self.claims.list_by_org(
      organization_id,
      project_id=project_id,
      status=status,
      skip=skip,
      limit=limit,
    )

  async def create_photo_boq_link(
    self,
    organization_id: UUID,
    user_id: UUID,
    payload: PhotoBOQLinkCreateRequest,
  ) -> PhotoBOQLink:
    claim = await self.get_claim(
      organization_id,
      payload.progress_claim_id,
    )

    if claim.project_id is None:
      raise TraceException(
        "Progress claim has no project.",
        status_code=409,
        code="PROGRESS_CLAIM_PROJECT_MISSING",
      )

    if claim.boq_item_id != payload.boq_item_id:
      raise TraceException(
        "The BOQ item must match the progress claim.",
        status_code=400,
        code="BOQ_ITEM_MISMATCH",
      )

    await self._get_boq_item(
      organization_id,
      claim.project_id,
      payload.boq_item_id,
    )

    photo = await self._get_site_photo(
      organization_id,
      claim.project_id,
      payload.site_photo_id,
    )

    if photo.project_id is not None and photo.project_id != claim.project_id:
      raise TraceException(
        "Site photo belongs to another project.",
        status_code=400,
        code="SITE_PHOTO_PROJECT_MISMATCH",
      )

    existing = await self.photo_boq_links.get_existing(
      claim.id,
      payload.site_photo_id,
      payload.boq_item_id,
    )

    if existing is not None:
      raise TraceException(
        "This photo is already linked to this BOQ item for the claim.",
        status_code=409,
        code="PHOTO_BOQ_LINK_ALREADY_EXISTS",
      )

    link = PhotoBOQLink(
      id=uuid4(),
      organization_id=organization_id,
      project_id=claim.project_id,
      progress_claim_id=claim.id,
      site_photo_id=payload.site_photo_id,
      boq_item_id=payload.boq_item_id,
      note=payload.note,
      created_by=user_id,
    )

    link = await self.photo_boq_links.create(link)

    await self.session.commit()
    await self.session.refresh(link)

    return link

  async def _get_site_photo(
    self,
    organization_id: UUID,
    project_id: UUID,
    site_photo_id: UUID,
  ):

    result = await self.session.execute(
      select(SitePhoto).where(
        SitePhoto.id == site_photo_id,
        SitePhoto.organization_id == organization_id,
      )
    )
    photo = result.scalar_one_or_none()

    if photo is None:
      raise TraceException(
        "Site photo is not present.",
        status_code=404,
        code="SITE_PHOTO_NOT_FOUND",
      )

    if photo.project_id is not None and photo.project_id != project_id:
      raise TraceException(
        "Site photo belongs to another project.",
        status_code=400,
        code="SITE_PHOTO_PROJECT_MISMATCH",
      )
    return photo

  async def list_photo_boq_links(
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
    return await self.photo_boq_links.list_by_org(
      organization_id,
      project_id=project_id,
      progress_claim_id=progress_claim_id,
      site_photo_id=site_photo_id,
      boq_item_id=boq_item_id,
      skip=skip,
      limit=limit,
    )

  async def delete_photo_boq_link(
    self,
    organization_id: UUID,
    link_id: UUID,
  ) -> None:
    link = await self.photo_boq_links.get_by_id_and_org(
      link_id,
      organization_id,
    )

    if link is None:
      raise TraceException(
        "Photo BOQ link not found.",
        status_code=404,
        code="PHOTO_BOQ_LINK_NOT_FOUND",
      )
    await self.photo_boq_links.delete(link)

    await self.session.commit()