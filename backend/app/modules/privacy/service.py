from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone
from app.modules.privacy.models import SupportAccessGrant, DataExportJob, DeletionStatus, ExportStatus, OrganizationDeletionRequest, OrganizationKey, SUPPORT_GRANT_MAX_HOURS
from app.modules.privacy.schemas import SupportGrantResponse, DeletionRequestResponse, EncryptionStatus, ExportJobResponse, PrivacyOverviewResponse
from uuid import UUID, uuid4
from app.modules.audit.service import AuditLogService
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.identity.models import Organization
from app.core.exceptions import TraceException
from app.modules.privacy.storage_ops import ObjectStore, assert_key_in_org, default_store
from app.core.config import settings
from app.core.crypto import keyring
from app.modules.audit.models import AuditAction, AuditEntityType

logger = logging.getLogger("trace.privacy")

ENCRYPTED_FIELDS = ["AI prompts", "AI responses", "AI structured output"]

def _now() -> datetime:
  return datetime.now(timezone.utc)

def grant_status(grant: SupportAccessGrant, now: datetime | None = None) -> str:
  now = now or _now()
  if grant.revoked_at is not None:
    return "REVOKED"
  return "EXPIRED" if grant.expires_at <= now else "ACTIVE"

def grant_response(grant: SupportAccessGrant) -> SupportGrantResponse:
  out = SupportGrantResponse.model_validate(grant)
  out.status = grant_status(grant)
  return out

def _default_enqueue(job_id: UUID) -> None:
  from app.modules.privacy.tasks import run_data_export_task
  run_data_export_task.delay(str(job_id))

class PrivacyService:
  def __init__(self, session: AsyncSession, store: ObjectStore | None = None, enqueue_export=None):
    self.session = session
    self.store = store or default_store
    self.enqueue_export = enqueue_export or _default_enqueue
    self.audit = AuditLogService(session)

  async def _organization(self, organization_id: UUID) -> Organization:
    org = (await self.session.execute(select(Organization).where(Organization.id == organization_id))).scalar_one_or_none()
    if org is None:
      raise TraceException("Organization not found.", status_code=404, code="ORGANIZATION_NOT_FOUND")
    return org

  async def active_grant(self, organization_id: UUID) -> SupportAccessGrant | None:
    now = _now()
    return (await self.session.execute(
      select(SupportAccessGrant).where(
        SupportAccessGrant.organization_id == organization_id, SupportAccessGrant.revoked_at.is_(None),
        SupportAccessGrant.starts_at <= now, SupportAccessGrant.expires_at > now)
      .order_by(SupportAccessGrant.expires_at.desc()).limit(1))).scalar_one_or_none()

  async def list_grants(self, organization_id: UUID, limit: int = 20) -> list[SupportAccessGrant]:
    return list((await self.session.execute(
      select(SupportAccessGrant).where(SupportAccessGrant.organization_id == organization_id)
      .order_by(SupportAccessGrant.created_at.desc()).limit(limit))).scalars().all())

  async def create_grant(self, organization_id: UUID, user_id: UUID, reason: str, hours: int, ip_address: str | None = None) -> SupportAccessGrant:
    reason = (reason or "").strip()
    
    if len(reason) < 10:
      raise TraceException("Say why support needs access (at least 10 characters).", status_code=422, code="SUPPORT_REASON_REQUIRED")
    if hours < 1 or hours > SUPPORT_GRANT_MAX_HOURS:
      raise TraceException(f"Access can be granted for 1 to {SUPPORT_GRANT_MAX_HOURS} hours.", status_code=422, code="SUPPORT_HOURS_INVALID")
    if await self.active_grant(organization_id) is not None:
      raise TraceException("Support already has access. Revoke it before granting again.", status_code=409, code="SUPPORT_GRANT_ACTIVE")
    now = _now()
    
    grant = SupportAccessGrant(id=uuid4(), organization_id=organization_id, granted_by_user_id=user_id, reason=reason, starts_at=now,
      expires_at=now + timedelta(hours=hours))
    self.session.add(grant)
    await self.session.flush()
    await self.audit.log(organization_id, user_id, AuditEntityType.SUPPORT_ACCESS, grant.id, AuditAction.CREATE,
      f"Granted support access for {hours} hours", {"reason": reason, "expires_at": grant.expires_at.isoformat()}, ip_address, commit=False)
    await self.session.commit()
    return grant

  async def revoke_grant(self, organization_id: UUID, user_id: UUID, grant_id: UUID, ip_address: str | None = None) -> SupportAccessGrant:
    grant = (await self.session.execute(
      select(SupportAccessGrant).where(SupportAccessGrant.id == grant_id, SupportAccessGrant.organization_id == organization_id))).scalar_one_or_none()
    if grant is None:
      raise TraceException("Support access grant not found.", status_code=404, code="SUPPORT_GRANT_NOT_FOUND")
    if grant.revoked_at is None and grant.expires_at > _now():
      grant.revoked_at = _now()
      
      grant.revoked_by_user_id = user_id
      await self.audit.log(organization_id, user_id, AuditEntityType.SUPPORT_ACCESS, grant.id, AuditAction.STATUS_CHANGE,
        "Revoked support access", {}, ip_address, commit=False)
      await self.session.commit()
    return grant

  async def list_exports(self, organization_id: UUID, limit: int = 10) -> list[DataExportJob]:
    return list((await self.session.execute(
      select(DataExportJob).where(DataExportJob.organization_id == organization_id)
      .order_by(DataExportJob.created_at.desc()).limit(limit))).scalars().all())

  async def request_export(self, organization_id: UUID, user_id: UUID, ip_address: str | None = None) -> DataExportJob:
    busy = (await self.session.execute(
      select(DataExportJob.id).where(DataExportJob.organization_id == organization_id,
        DataExportJob.status.in_([ExportStatus.QUEUED.value, ExportStatus.RUNNING.value])).limit(1))).scalar_one_or_none()
    
    if busy is not None:
      raise TraceException("An export is already being prepared.", status_code=409, code="EXPORT_IN_PROGRESS")
    job = DataExportJob(id=uuid4(), organization_id=organization_id, requested_by_user_id=user_id, status=ExportStatus.QUEUED.value)
    self.session.add(job)
    await self.session.flush()
    await self.audit.log(organization_id, user_id, AuditEntityType.DATA_EXPORT, job.id, AuditAction.CREATE, "Requested an export of all company data",
      {}, ip_address, commit=False)
    await self.session.commit()
    try:
      self.enqueue_export(job.id)
    except Exception: 
      logger.warning("could not queue export %s; the privacy sweep queues it again", job.id, exc_info=True)
    return job

  async def download_link(self, organization_id: UUID, user_id: UUID, job_id: UUID, ip_address: str | None = None) -> tuple[str, int]:
    job = (await self.session.execute(
      select(DataExportJob).where(DataExportJob.id == job_id, DataExportJob.organization_id == organization_id))).scalar_one_or_none()
    
    if job is None:
      raise TraceException("Export not found.", status_code=404, code="EXPORT_NOT_FOUND")
    if job.status != ExportStatus.COMPLETED.value or not job.storage_key:
      raise TraceException("The export is not ready or has expired.", status_code=409, code="EXPORT_NOT_READY")
    if job.expires_at is not None and job.expires_at <= _now():
      raise TraceException("The export has expired. Request a new one.", status_code=409, code="EXPORT_EXPIRED")
  
    assert_key_in_org(organization_id, job.storage_key)
    ttl = int(settings.data_export_url_ttl_seconds)
    url = self.store.presign(job.storage_key, ttl)
    await self.audit.log(organization_id, user_id, AuditEntityType.DATA_EXPORT, job.id, AuditAction.UPDATE, "Downloaded the company data export",
      {}, ip_address, commit=True)
    return url, ttl

  async def pending_deletion(self, organization_id: UUID) -> OrganizationDeletionRequest | None:
    return (await self.session.execute(
      select(OrganizationDeletionRequest).where(OrganizationDeletionRequest.organization_id == organization_id,
        OrganizationDeletionRequest.status.in_([DeletionStatus.PENDING.value, DeletionStatus.EXECUTING.value]))
      .order_by(OrganizationDeletionRequest.requested_at.desc()).limit(1))).scalar_one_or_none()

  async def request_deletion(self, organization_id: UUID, user_id: UUID, confirm_name: str, reason: str | None = None,
    ip_address: str | None = None) -> OrganizationDeletionRequest:
    org = await self._organization(organization_id)
    if (confirm_name or "").strip().casefold() != org.name.strip().casefold():
      raise TraceException("Type the exact organization name to confirm.", status_code=422, code="DELETION_CONFIRMATION_MISMATCH")
    if await self.pending_deletion(organization_id) is not None:
      raise TraceException("Deletion is already requested.", status_code=409, code="DELETION_ALREADY_REQUESTED")
  
    when = _now() + timedelta(days=int(settings.org_deletion_grace_days))
    req = OrganizationDeletionRequest(id=uuid4(), organization_id=organization_id, requested_by_user_id=user_id, status=DeletionStatus.PENDING.value,
      reason=(reason or None), scheduled_for=when)
    self.session.add(req)
    
    try:
      await self.session.flush()
    except IntegrityError as exc:
      await self.session.rollback()
      raise TraceException("Deletion is already requested.", status_code=409, code="DELETION_ALREADY_REQUESTED") from exc
    await self.audit.log(organization_id, user_id, AuditEntityType.DATA_DELETION, req.id, AuditAction.CREATE,
      f"Requested deletion of all company data, scheduled for {when.date().isoformat()}", {"scheduled_for": when.isoformat()}, ip_address, commit=False)
    await self.session.commit()
    return req

  async def cancel_deletion(self, organization_id: UUID, user_id: UUID, ip_address: str | None = None) -> OrganizationDeletionRequest:
    req = await self.pending_deletion(organization_id)
    if req is None or req.status != DeletionStatus.PENDING.value:
      raise TraceException("There is no pending deletion to cancel.", status_code=404, code="DELETION_NOT_PENDING")
    req.status = DeletionStatus.CANCELLED.value
    req.cancelled_at = _now()
    req.cancelled_by_user_id = user_id
    await self.audit.log(organization_id, user_id, AuditEntityType.DATA_DELETION, req.id, AuditAction.STATUS_CHANGE, "Cancelled the deletion of company data",
      {}, ip_address, commit=False)
    await self.session.commit()
    return req

  async def overview(self, organization_id: UUID) -> PrivacyOverviewResponse:
    org = await self._organization(organization_id)
    grant = await self.active_grant(organization_id)
    exports = await self.list_exports(organization_id, limit=1)
    pending = await self.pending_deletion(organization_id)
    key_ready = keyring.has_key(organization_id)
    
    if keyring.enabled and not key_ready:
      key_ready = (await self.session.execute(
        select(OrganizationKey.id).where(OrganizationKey.organization_id == organization_id).limit(1))).scalar_one_or_none() is not None
      
    return PrivacyOverviewResponse(
      organization_name=org.name,
      encryption=EncryptionStatus(enabled=keyring.enabled, provider=keyring.provider_name, key_ready=key_ready, fields=ENCRYPTED_FIELDS if keyring.enabled else []),
      active_support_grant=grant_response(grant) if grant else None,
      latest_export=ExportJobResponse.model_validate(exports[0]) if exports else None,
      pending_deletion=DeletionRequestResponse.model_validate(pending) if pending else None,
      grace_days=int(settings.org_deletion_grace_days),
      support_grant_max_hours=SUPPORT_GRANT_MAX_HOURS,
    )
