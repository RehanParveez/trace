from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.retention.repository import RetentionRepository
from app.modules.projects.repository import ProjectRepository
from app.modules.audit.service import AuditLogService
from app.modules.retention.schemas import RetentionReleaseCreateRequest
from app.modules.retention.models import RetentionHolderType, RetentionRelease
from app.core.exceptions import TraceException
from uuid import UUID, uuid4
from app.modules.audit.models import AuditEntityType, AuditAction
from app.modules.identity.models import Organization
from decimal import Decimal
from app.modules.drawings_boq.models import BOQVersion
from app.modules.subcontractors.models import SubcontractAgreement, Subcontractor
from app.modules.punch_lists.service import PunchListService

class RetentionService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = RetentionRepository(session)
    self.projects = ProjectRepository(session)
    self.audit = AuditLogService(session)
    self.punch_lists = PunchListService(session)

  async def record_release(
    self, organization_id: UUID, payload: RetentionReleaseCreateRequest, actor_user_id: UUID,
  ) -> RetentionRelease:
    project = await self._require_project(organization_id, payload.project_id)

    if payload.holder_type == RetentionHolderType.CLIENT:
      outstanding = await self._get_client_outstanding(organization_id, payload.boq_version_id)
      label = "client-held retention"
      if payload.is_final_release:
        await self.punch_lists.assert_project_clear_for_final_release(organization_id, payload.project_id)
    else:
      outstanding = await self._get_subcontractor_outstanding(organization_id, payload.agreement_id)
      label = "subcontractor retention"
      if payload.is_final_release:
        agreement = await self.session.get(SubcontractAgreement, payload.agreement_id)
        
        if agreement is not None:
          await self.punch_lists.assert_subcontractor_clear_for_final_release(
            organization_id, payload.project_id, agreement.subcontractor_id,
          )

    if payload.amount > outstanding:
      raise TraceException(
        f"Cannot release {payload.amount} — only {outstanding} of {label} is currently outstanding.",
        status_code=409, code="RETENTION_RELEASE_EXCEEDS_BALANCE",
      )

    release = RetentionRelease(
      id=uuid4(), organization_id=organization_id, project_id=payload.project_id,
      holder_type=payload.holder_type, boq_version_id=payload.boq_version_id, agreement_id=payload.agreement_id,
      amount=payload.amount, release_date=payload.release_date,
      is_final_release=payload.is_final_release, created_by_user_id=actor_user_id,
    )
    await self.repo.create_release(release)
    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.RETENTION, release.id, AuditAction.CREATE,
      f"Released {payload.amount} of {label} for {project.name}"
      + (" (final release)" if payload.is_final_release else "") + ".",
    )
    return release

  async def list_releases(self, organization_id: UUID, project_id: UUID | None = None) -> list[RetentionRelease]:
    return await self.repo.list_releases(organization_id, project_id)

  async def get_project_summary(self, organization_id: UUID, project_id: UUID) -> dict:
    await self._require_project(organization_id, project_id)
    organization = await self.session.get(Organization, organization_id)
    currency = organization.currency if organization else "PKR"

    client_lines = []
    client_total = Decimal("0")
    for bill in await self.repo.get_latest_issued_running_bills(organization_id, project_id):
      released = await self.repo.get_client_releases_total(organization_id, boq_version_id=bill.boq_version_id)
      outstanding = bill.retention_cumulative - released
      client_total += outstanding
      boq_version = await self.session.get(BOQVersion, bill.boq_version_id)
      client_lines.append({
        "boq_version_id": bill.boq_version_id,
        "boq_version_label": boq_version.label if boq_version else "BOQ",
        "retention_held": bill.retention_cumulative, "retention_released": released, "retention_outstanding": outstanding,
      })

    subcontractor_lines = []
    subcontractor_total = Decimal("0")
    for bill in await self.repo.get_latest_issued_subcontractor_bills(organization_id, project_id):
      released = await self.repo.get_subcontractor_releases_total(organization_id, agreement_id=bill.agreement_id)
      outstanding = bill.retention_cumulative - released
      subcontractor_total += outstanding
      agreement = await self.session.get(SubcontractAgreement, bill.agreement_id)
      subcontractor = await self.session.get(Subcontractor, agreement.subcontractor_id) if agreement else None
      subcontractor_lines.append({
        "agreement_id": bill.agreement_id, "subcontractor_name": subcontractor.name if subcontractor else "—",
        "retention_held": bill.retention_cumulative, "retention_released": released, "retention_outstanding": outstanding,
      })

    return {
      "project_id": project_id, "client_lines": client_lines, "client_total_outstanding": client_total,
      "subcontractor_lines": subcontractor_lines, "subcontractor_total_outstanding": subcontractor_total,
      "currency": currency,
    }

  async def get_organization_summary(self, organization_id: UUID) -> dict:
    organization = await self.session.get(Organization, organization_id)
    currency = organization.currency if organization else "PKR"

    client_bills = await self.repo.get_latest_issued_running_bills(organization_id)
    client_held = sum((b.retention_cumulative for b in client_bills), Decimal("0"))
    client_released = await self.repo.get_client_releases_total(organization_id)

    subcontractor_bills = await self.repo.get_latest_issued_subcontractor_bills(organization_id)
    subcontractor_held = sum((b.retention_cumulative for b in subcontractor_bills), Decimal("0"))
    subcontractor_released = await self.repo.get_subcontractor_releases_total(organization_id)

    return {
      "client_retention_held": client_held - client_released,
      "subcontractor_retention_held": subcontractor_held - subcontractor_released,
      "currency": currency,
    }

  async def _get_client_outstanding(self, organization_id: UUID, boq_version_id: UUID) -> Decimal:
    bill = await self.repo.get_latest_issued_running_bill(organization_id, boq_version_id)
    held = bill.retention_cumulative if bill else Decimal("0")
    released = await self.repo.get_client_releases_total(organization_id, boq_version_id=boq_version_id)
    return held - released

  async def _get_subcontractor_outstanding(self, organization_id: UUID, agreement_id: UUID) -> Decimal:
    bill = await self.repo.get_latest_issued_subcontractor_bill(organization_id, agreement_id)
    held = bill.retention_cumulative if bill else Decimal("0")
    released = await self.repo.get_subcontractor_releases_total(organization_id, agreement_id=agreement_id)
    return held - released

  async def _require_project(self, organization_id: UUID, project_id: UUID):
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")
    return project