from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.bank_guarantees.repository import BankGuaranteeRepository
from app.modules.projects.repository import ProjectRepository
from app.modules.audit.service import AuditLogService
from app.modules.punch_lists.service import PunchListService
from app.modules.bank_guarantees.schemas import BankGuaranteeCreateRequest, BankGuaranteeRenewRequest
from app.modules.bank_guarantees.models import BankGuarantee, BankGuaranteeHolderType, BankGuaranteeStatus
from app.core.exceptions import TraceException
from app.modules.identity.models import Organization
from decimal import Decimal
from uuid import UUID, uuid4
from app.modules.audit.models import AuditEntityType, AuditAction
from app.modules.subcontractors.models import SubcontractAgreement
from datetime import datetime, timezone
from app.shared.timeutils import today_local

EXPIRING_SOON_WINDOW_DAYS = 30

class BankGuaranteeService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = BankGuaranteeRepository(session)
    self.projects = ProjectRepository(session)
    self.audit = AuditLogService(session)
    self.punch_lists = PunchListService(session)

  async def create_guarantee(
    self, organization_id: UUID, payload: BankGuaranteeCreateRequest, actor_user_id: UUID,
  ) -> BankGuarantee:
    project = await self._require_project(organization_id, payload.project_id)
    organization = await self.session.get(Organization, organization_id)

    guarantee = BankGuarantee(
      id=uuid4(), organization_id=organization_id, project_id=payload.project_id,
      holder_type=payload.holder_type, boq_version_id=payload.boq_version_id, agreement_id=payload.agreement_id,
      guarantee_number=payload.guarantee_number.strip(), issuing_bank=payload.issuing_bank.strip(),
      amount=payload.amount, currency=organization.currency if organization else "PKR",
      issue_date=payload.issue_date, expiry_date=payload.expiry_date, notes=payload.notes,
      created_by_user_id=actor_user_id,
    )
    await self.repo.create(guarantee)
    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.BANK_GUARANTEE, guarantee.id, AuditAction.CREATE,
      f"Recorded bank guarantee {guarantee.guarantee_number} ({guarantee.amount} {guarantee.currency}) for {project.name}.",
    )
    return guarantee

  async def renew_guarantee(
    self, organization_id: UUID, guarantee_id: UUID, payload: BankGuaranteeRenewRequest, actor_user_id: UUID,
  ) -> BankGuarantee:
    old_guarantee = await self.repo.get_by_id_for_update(guarantee_id, organization_id)
    if old_guarantee is None:
      raise TraceException("Bank guarantee not found.", status_code=404, code="BANK_GUARANTEE_NOT_FOUND")
    if old_guarantee.status != BankGuaranteeStatus.ACTIVE:
      raise TraceException("Only an active guarantee can be renewed.", status_code=409, code="BANK_GUARANTEE_NOT_ACTIVE")

    new_guarantee = BankGuarantee(
      id=uuid4(), organization_id=organization_id, project_id=old_guarantee.project_id,
      holder_type=old_guarantee.holder_type, boq_version_id=old_guarantee.boq_version_id,
      agreement_id=old_guarantee.agreement_id, purpose=old_guarantee.purpose,
      guarantee_number=payload.guarantee_number.strip(), issuing_bank=old_guarantee.issuing_bank,
      amount=payload.amount if payload.amount is not None else old_guarantee.amount,
      currency=old_guarantee.currency, issue_date=payload.issue_date, expiry_date=payload.expiry_date,
      renewed_from_guarantee_id=old_guarantee.id, notes=payload.notes, created_by_user_id=actor_user_id,
    )
    await self.repo.create(new_guarantee)

    old_guarantee.status = BankGuaranteeStatus.RENEWED
    old_guarantee.superseded_at = datetime.now(timezone.utc)
    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.BANK_GUARANTEE, new_guarantee.id, AuditAction.CREATE,
      f"Renewed bank guarantee {old_guarantee.guarantee_number} as {new_guarantee.guarantee_number}, new expiry {new_guarantee.expiry_date}.",
    )
    return new_guarantee

  async def release_guarantee(self, organization_id: UUID, guarantee_id: UUID, actor_user_id: UUID) -> BankGuarantee:
    guarantee = await self.repo.get_by_id_for_update(guarantee_id, organization_id)
    if guarantee is None:
      raise TraceException("Bank guarantee not found.", status_code=404, code="BANK_GUARANTEE_NOT_FOUND")
    if guarantee.status != BankGuaranteeStatus.ACTIVE:
      raise TraceException("Only an active guarantee can be released.", status_code=409, code="BANK_GUARANTEE_NOT_ACTIVE")

    if guarantee.holder_type == BankGuaranteeHolderType.CLIENT:
      await self.punch_lists.assert_project_clear_for_final_release(organization_id, guarantee.project_id)
    else:
      agreement = await self.session.get(SubcontractAgreement, guarantee.agreement_id)
      if agreement is not None:
        await self.punch_lists.assert_subcontractor_clear_for_final_release(
          organization_id, guarantee.project_id, agreement.subcontractor_id,
        )

    guarantee.status = BankGuaranteeStatus.RELEASED
    guarantee.released_at = datetime.now(timezone.utc)
    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.BANK_GUARANTEE, guarantee.id, AuditAction.UPDATE,
      f"Released bank guarantee {guarantee.guarantee_number} for return to {guarantee.issuing_bank}.",
    )
    return guarantee

  async def mark_called(self, organization_id: UUID, guarantee_id: UUID, actor_user_id: UUID) -> BankGuarantee:
    """Records that the beneficiary encashed the guarantee -- a real dispute outcome, not an approval request."""
    guarantee = await self.repo.get_by_id_for_update(guarantee_id, organization_id)
    if guarantee is None:
      raise TraceException("Bank guarantee not found.", status_code=404, code="BANK_GUARANTEE_NOT_FOUND")
    if guarantee.status != BankGuaranteeStatus.ACTIVE:
      raise TraceException(
        "Only an active guarantee can be marked as called.", status_code=409, code="BANK_GUARANTEE_NOT_ACTIVE",
      )
    guarantee.status = BankGuaranteeStatus.CALLED
    await self.session.commit()
    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.BANK_GUARANTEE, guarantee.id, AuditAction.UPDATE,
      f"Bank guarantee {guarantee.guarantee_number} was called by the beneficiary.",
    )
    return guarantee

  async def get_guarantee(self, organization_id: UUID, guarantee_id: UUID) -> BankGuarantee:
    guarantee = await self.repo.get_by_id(guarantee_id, organization_id)
    if guarantee is None:
      raise TraceException("Bank guarantee not found.", status_code=404, code="BANK_GUARANTEE_NOT_FOUND")
    return guarantee

  async def list_guarantees(self, organization_id: UUID, project_id: UUID) -> list[BankGuarantee]:
    await self._require_project(organization_id, project_id)
    return await self.repo.list_by_project(organization_id, project_id)

  async def get_project_summary(self, organization_id: UUID, project_id: UUID) -> dict:
    await self._require_project(organization_id, project_id)
    active_guarantees = await self.repo.get_active_for_project(organization_id, project_id)
    today_local()

    expiring_soon = 0
    expired = 0
    total_value = Decimal("0")
    for g in active_guarantees:
      days_left = (g.expiry_date - today).days
      if days_left < 0:
        expired += 1
      elif days_left <= EXPIRING_SOON_WINDOW_DAYS:
        expiring_soon += 1
      total_value += g.amount

    organization = await self.session.get(Organization, organization_id)
    return {
      "project_id": project_id, "active_count": len(active_guarantees),
      "expiring_soon_count": expiring_soon, "expired_count": expired,
      "total_active_value": total_value, "currency": organization.currency if organization else "PKR",
    }

  async def require_adequate_guarantee_for_boq_version(
    self, organization_id: UUID, boq_version_id: UUID, required_amount: Decimal,
  ) -> BankGuarantee:
    guarantee = await self.repo.get_active_for_boq_version(organization_id, boq_version_id)
    if guarantee is None:
      raise TraceException(
        "No active bank guarantee is on file to secure retention for this BOQ version. "
        "Record one first, or bill with cash retention instead.",
        status_code=409, code="BANK_GUARANTEE_REQUIRED",
      )
    if guarantee.expiry_date <= _date.today():
      raise TraceException(
        f"The bank guarantee on file ({guarantee.guarantee_number}) has expired. Renew it before billing.",
        status_code=409, code="BANK_GUARANTEE_EXPIRED",
      )
    if guarantee.amount < required_amount:
      raise TraceException(
        f"The bank guarantee on file ({guarantee.guarantee_number}, {guarantee.amount} {guarantee.currency}) "
        f"is smaller than the required retention value of {required_amount} {guarantee.currency}. "
        f"Increase the guarantee's value or renew it before billing.",
        status_code=409, code="BANK_GUARANTEE_INSUFFICIENT",
      )
    return guarantee

  async def require_adequate_guarantee_for_agreement(
    self, organization_id: UUID, agreement_id: UUID, required_amount: Decimal,
  ) -> BankGuarantee:
    guarantee = await self.repo.get_active_for_agreement(organization_id, agreement_id)
    if guarantee is None:
      raise TraceException(
        "No active bank guarantee is on file from this subcontractor to secure retention. "
        "Record one first, or bill with cash retention instead.",
        status_code=409, code="BANK_GUARANTEE_REQUIRED",
      )
    if guarantee.expiry_date <= _date.today():
      raise TraceException(
        f"The bank guarantee on file ({guarantee.guarantee_number}) has expired. Request a renewal before billing.",
        status_code=409, code="BANK_GUARANTEE_EXPIRED",
      )
    if guarantee.amount < required_amount:
      raise TraceException(
        f"The bank guarantee on file ({guarantee.guarantee_number}, {guarantee.amount} {guarantee.currency}) "
        f"is smaller than the required retention value of {required_amount} {guarantee.currency}.",
        status_code=409, code="BANK_GUARANTEE_INSUFFICIENT",
      )
    return guarantee

  async def _require_project(self, organization_id: UUID, project_id: UUID):
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")
    return project