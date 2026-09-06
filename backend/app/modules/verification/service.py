from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from pathlib import PurePosixPath
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.exceptions import TraceException
from app.modules.drawings_boq.models import BOQItem, BOQVersion, BOQItemStatus
from app.modules.projects.repository import ProjectRepository
from app.modules.verification.models import PhotoBOQLink, ProgressClaim, ProgressClaimStatus
from app.modules.whatsapp.models import PhotoTag, PhotoTagSource ,SitePhoto
from app.modules.whatsapp.repository import PhotoTagRepository
from app.modules.verification.repository import PhotoBOQLinkRepository, ProgressClaimRepository
from app.modules.verification.schemas import PhotoBOQLinkCreateRequest, ProgressClaimCreateRequest, ProgressClaimReviewRequest, ProgressClaimUpdateRequest
from app.modules.notifications.service import NotificationService, NotificationType
from app.modules.audit.models import AuditAction, AuditEntityType
from app.modules.audit.service import AuditLogService
from app.modules.ai_requests.models import AIEntityType, AIRequestPurpose
from app.modules.ai_requests.service import AIOrchestratorService, AIRunResult
from app.shared.storage import download_bytes

_MIME_BY_EXTENSION = {
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
}

def _guess_mime_type(storage_key: str) -> str:
  suffix = PurePosixPath(storage_key).suffix.lower()
  return _MIME_BY_EXTENSION.get(suffix, "image/jpeg")

class VerificationService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.claims = ProgressClaimRepository(session)
    self.photo_boq_links = PhotoBOQLinkRepository(session)
    self.photo_tags = PhotoTagRepository(session)
    self.projects = ProjectRepository(session)
    self.notifications = NotificationService(session)
    self.audit = AuditLogService(session)
    self.ai = AIOrchestratorService(session)

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

    await self.notifications.notify_by_permission(
     organization_id,
     "progress_claim:review",
     NotificationType.PROGRESS_CLAIM_SUBMITTED,
     "A progress claim was submitted for review",
     body=f"Claim dated {claim.claim_date.isoformat()} is awaiting review.",
     link_path=f"/app/projects/{claim.project_id}",
     exclude_user_id=user_id,
    )

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

    await self.audit.log(
      organization_id,
      user_id,
      AuditEntityType.PROGRESS_CLAIM,
      claim.id,
      AuditAction.APPROVE,
      f"Approved progress claim dated {claim.claim_date.isoformat()}",
      changes={
        "status": {
          "old": "SUBMITTED",
          "new": claim.status.value,
        }
      },
    )
    
    if claim.submitted_by is not None:
      await self.notifications.notify_user(
        organization_id, claim.submitted_by,
        NotificationType.PROGRESS_CLAIM_APPROVED,
        "Your progress claim was approved",
        body=f"Claim dated {claim.claim_date.isoformat()} was approved.",
        link_path=f"/app/projects/{claim.project_id}",
      )

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

    await self.audit.log(
      organization_id,
      user_id,
      AuditEntityType.PROGRESS_CLAIM,
      claim.id,
      AuditAction.REJECT,
      f"Rejected progress claim dated {claim.claim_date.isoformat()}",
      changes={
        "status": {
          "old": "SUBMITTED",
          "new": claim.status.value,
        }
      },
    )
    
    if claim.submitted_by is not None:
      await self.notifications.notify_user(
        organization_id, claim.submitted_by,
        NotificationType.PROGRESS_CLAIM_REJECTED,
        "Your progress claim was rejected",
        body=f"Claim dated {claim.claim_date.isoformat()} was rejected." + (f" Note: {payload.note}" if payload.note else ""),
        link_path=f"/app/projects/{claim.project_id}",
      )

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

   boq_item = await self._get_boq_item(    
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

   prompt = (
    "You are reviewing a construction site photo submitted as evidence for "
    "a progress claim. Based on what is visible in the photo, identify "
    "tags describing the construction work, materials, or stage shown, "
    "and note whether the photo appears visually consistent with the "
    "claim below. Respond with strict JSON only, no other text: "
    '{"tags": [{"tag": "short-label", "confidence": 0.0}], '
    '"visually_consistent_with_claim": true or false, "notes": "..."}. '
    f"Claimed BOQ item: {boq_item.material_name}"
    + (f" ({boq_item.category})" if boq_item.category else "")
    + f", unit {boq_item.unit}. "
    f"Claimed quantity: {claim.claimed_quantity} {boq_item.unit} "
    f"({claim.claimed_percentage}% of total). "
    f"Claim date: {claim.claim_date.isoformat()}. "
    f"Photo note (if any): {payload.note or 'none'}."
  )

   image_bytes: bytes | None = None
   image_mime_type: str | None = None
   try:
    image_bytes = await asyncio.to_thread(download_bytes, photo.storage_key)
    image_mime_type = _guess_mime_type(photo.storage_key)
   except Exception as exc:
    print(">>> PHOTO DOWNLOAD FAILED:", repr(exc), flush=True)
    image_bytes = None
    image_mime_type = None
   
   print(">>> BEFORE AI TAGGING", flush=True)

   ai_result = await self._run_photo_tagging(
    organization_id=organization_id,
    site_photo_id=payload.site_photo_id,
    user_id=user_id,
    prompt=prompt,
    image_bytes=image_bytes,
    image_mime_type=image_mime_type,
   )
   print(">>> AFTER AI TAGGING", flush=True)
   print(">>> AI RESULT:", ai_result.success, "| error:", ai_result.error_message)

   if ai_result.success and ai_result.parsed_output:
    try:
      await self._apply_ai_tags(photo, ai_result.parsed_output)
    except Exception:
      pass

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

  async def _apply_ai_tags(
    self,
    photo: SitePhoto,
    parsed_output: dict,
  ) -> None:
    raw_tags = parsed_output.get("tags")
    if not isinstance(raw_tags, list):
     return

    existing_tag_values = {t.tag for t in photo.tags}
    new_tags: list[PhotoTag] = []

    for entry in raw_tags[:10]:
     if isinstance(entry, dict):
      tag_value = str(entry.get("tag", "")).strip().lower()
      confidence = entry.get("confidence")
     elif isinstance(entry, str):
      tag_value = entry.strip().lower()
      confidence = None
     else:
      continue

     if not tag_value or tag_value in existing_tag_values:
      continue

     try:
      confidence_value = float(confidence) if confidence is not None else None
     except (TypeError, ValueError):
      confidence_value = None

     new_tags.append(
      PhotoTag(
        id=uuid4(),
        site_photo_id=photo.id,
        tag=tag_value,
        confidence=confidence_value,
        source=PhotoTagSource.AI,       
      )
    )
     existing_tag_values.add(tag_value)

    if new_tags:
     await self.photo_tags.bulk_create(new_tags)
     photo.is_ai_tagged = True

  async def _get_site_photo(
    self,
    organization_id: UUID,
    project_id: UUID,
    site_photo_id: UUID,
  ):
    result = await self.session.execute(
     select(SitePhoto)
     .where(
      SitePhoto.id == site_photo_id,
      SitePhoto.organization_id == organization_id,
    )
     .options(selectinload(SitePhoto.tags))    
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

  async def _run_photo_tagging(
    self,
    *,
    organization_id: UUID,
    site_photo_id: UUID,
    user_id: UUID | None,
    prompt: str,
    image_bytes: bytes | None = None,
    image_mime_type: str | None = None,
) -> AIRunResult:
    return await self.ai.run(
      organization_id=organization_id,
      purpose=AIRequestPurpose.PHOTO_TAGGING,
      prompt=prompt,
      entity_type=AIEntityType.SITE_PHOTO,
      entity_id=site_photo_id,
      requested_by=user_id,
      image_bytes=image_bytes,
      image_mime_type=image_mime_type,
    )

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