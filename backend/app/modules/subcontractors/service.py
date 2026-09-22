from __future__ import annotations
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.exceptions import TraceException
from app.modules.audit.models import AuditAction, AuditEntityType
from app.modules.audit.service import AuditLogService
from app.modules.identity.models import Organization
from app.modules.projects.models import Client, Project
from app.modules.subcontractors.export import build_subcontractor_bill_pdf, build_subcontractor_bill_xlsx
from app.modules.subcontractors.models import (Subcontractor, SubcontractAgreement, SubcontractAgreementItem, SubcontractAgreementStatus, SubcontractorAdvance, SubcontractorBill, SubcontractorBillLineItem, 
  SubcontractorBillStatus, SubcontractorPayment,
)
from app.modules.subcontractors.repository import SubcontractorRepository
from app.modules.subcontractors.schemas import (SubcontractAgreementCreateRequest, SubcontractAgreementUpdateRequest, SubcontractorAdvanceCreateRequest, SubcontractorBillCreateRequest, SubcontractorCreateRequest,
  SubcontractorPaymentCreateRequest, SubcontractorUpdateRequest,
)
from app.modules.projects.repository import ProjectRepository

class SubcontractorService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = SubcontractorRepository(session)
    self.projects = ProjectRepository(session)
    self.audit = AuditLogService(session)

  async def create_subcontractor(self, organization_id: UUID, payload: SubcontractorCreateRequest) -> Subcontractor:
    subcontractor = Subcontractor(
      id=uuid4(), organization_id=organization_id, name=payload.name.strip(),
      trade_specialization=payload.trade_specialization.strip(), contact_name=payload.contact_name,
      contact_phone=payload.contact_phone, ntn_or_cnic=payload.ntn_or_cnic, notes=payload.notes,
    )
    await self.repo.create(subcontractor)
    await self.session.commit()
    return subcontractor

  async def update_subcontractor(
    self, organization_id: UUID, subcontractor_id: UUID, payload: SubcontractorUpdateRequest,
  ) -> Subcontractor:
    subcontractor = await self.repo.get(subcontractor_id, organization_id)
    if subcontractor is None:
      raise TraceException("Subcontractor not found.", status_code=404, code="SUBCONTRACTOR_NOT_FOUND")
    for field in ("name", "trade_specialization", "contact_name", "contact_phone", "ntn_or_cnic", "is_active", "notes"):
      value = getattr(payload, field)
      if value is not None:
        setattr(subcontractor, field, value.strip() if isinstance(value, str) else value)
    await self.session.commit()
    return subcontractor

  async def list_subcontractors(self, organization_id: UUID) -> list[Subcontractor]:
    return await self.repo.list_all(organization_id)

  async def create_agreement(
    self, organization_id: UUID, payload: SubcontractAgreementCreateRequest,
  ) -> SubcontractAgreement:
    project = await self._require_project(organization_id, payload.project_id)
    subcontractor = await self.repo.get(payload.subcontractor_id, organization_id)
    if subcontractor is None:
      raise TraceException("Subcontractor not found.", status_code=404, code="SUBCONTRACTOR_NOT_FOUND")

    if payload.items:
      contract_value = sum((item.quantity * item.rate for item in payload.items), Decimal("0"))
    else:
      contract_value = payload.contract_value 

    agreement = SubcontractAgreement(
      id=uuid4(), organization_id=organization_id, project_id=payload.project_id,
      subcontractor_id=payload.subcontractor_id, scope_description=payload.scope_description.strip(),
      contract_value=contract_value, default_retention_percentage=payload.default_retention_percentage,
      default_retention_cap_percentage=payload.default_retention_cap_percentage,
      start_date=payload.start_date, notes=payload.notes,
    )
    await self.repo.create_agreement(agreement)

    if payload.items:
      items = [
        SubcontractAgreementItem(
          id=uuid4(), organization_id=organization_id, agreement_id=agreement.id, sort_order=index,
          description=item.description.strip(), unit=item.unit.strip(), quantity=item.quantity, rate=item.rate,
        )
        for index, item in enumerate(payload.items)
      ]
    else:
      items = [
        SubcontractAgreementItem(
          id=uuid4(), organization_id=organization_id, agreement_id=agreement.id, sort_order=0,
          description=payload.scope_description.strip()[:300], unit="LS", quantity=Decimal("1"), rate=contract_value,
        )
      ]
    await self.repo.create_agreement_items(items)
    await self.session.commit()

    await self.audit.log(
      organization_id, None, AuditEntityType.SUBCONTRACTOR, agreement.id, AuditAction.CREATE,
      f"Created subcontract agreement with {subcontractor.name} for {project.name}, value {contract_value}.",
    )
    return await self.get_agreement(organization_id, agreement.id)

  async def update_agreement(
    self, organization_id: UUID, agreement_id: UUID, payload: SubcontractAgreementUpdateRequest,
  ) -> SubcontractAgreement:
    agreement = await self.repo.get_agreement_for_update(agreement_id, organization_id)
    if agreement is None:
      raise TraceException("Agreement not found.", status_code=404, code="AGREEMENT_NOT_FOUND")
    if agreement.version != payload.version:
      raise TraceException(
        "This agreement was changed by someone else. Reload and try again.",
        status_code=409, code="AGREEMENT_VERSION_CONFLICT",
      )
    if payload.end_date is not None:
      agreement.end_date = payload.end_date
    if payload.status is not None:
      agreement.status = payload.status
    if payload.default_retention_percentage is not None:
      agreement.default_retention_percentage = payload.default_retention_percentage
    agreement.version += 1
    await self.session.commit()
    return agreement

  async def get_agreement(self, organization_id: UUID, agreement_id: UUID) -> SubcontractAgreement:
    agreement = await self.repo.get_agreement(agreement_id, organization_id)
    if agreement is None:
      raise TraceException("Agreement not found.", status_code=404, code="AGREEMENT_NOT_FOUND")
    return agreement

  async def list_agreements(self, organization_id: UUID, project_id: UUID) -> list[SubcontractAgreement]:
    await self._require_project(organization_id, project_id)
    return await self.repo.list_agreements_by_project(organization_id, project_id)

  async def generate_draft_bill(
    self, organization_id: UUID, payload: SubcontractorBillCreateRequest, actor_user_id: UUID,
  ) -> SubcontractorBill:
    agreement = await self.get_agreement(organization_id, payload.agreement_id)
    if agreement.status != SubcontractAgreementStatus.ACTIVE:
      raise TraceException(
        "Only active agreements can be billed.", status_code=409, code="AGREEMENT_NOT_ACTIVE",
      )

    previous_bill = await self.repo.get_last_issued_bill(organization_id, agreement.id)
    previous_by_item = (
      {line.agreement_item_id: line for line in previous_bill.line_items} if previous_bill else {}
    )
    measurement_by_item = {m.agreement_item_id: m.cumulative_percentage for m in payload.measurements}

    for item in agreement.items:
      if item.id not in measurement_by_item:
        continue
      previous_percentage = (
        previous_by_item[item.id].cumulative_percentage if item.id in previous_by_item else Decimal("0")
      )
      if measurement_by_item[item.id] < previous_percentage:
        raise TraceException(
          f"'{item.description}' cannot go backward from {previous_percentage}% to {measurement_by_item[item.id]}%.",
          status_code=422, code="MEASUREMENT_REGRESSION",
        )

    line_items: list[SubcontractorBillLineItem] = []
    gross_this_period = Decimal("0")
    gross_cumulative = Decimal("0")

    for index, item in enumerate(agreement.items):
      previous_line = previous_by_item.get(item.id)
      previous_percentage = previous_line.cumulative_percentage if previous_line is not None else Decimal("0")
      cumulative_percentage = measurement_by_item.get(item.id, previous_percentage)  # carry forward if unmeasured

      cumulative_value = (item.quantity * item.rate * cumulative_percentage / Decimal("100")).quantize(Decimal("0.01"))
      previous_value = previous_line.cumulative_value if previous_line is not None else Decimal("0")
      this_period_value = cumulative_value - previous_value

      gross_this_period += this_period_value
      gross_cumulative += cumulative_value

      line_items.append(
        SubcontractorBillLineItem(
          id=uuid4(), organization_id=organization_id, agreement_item_id=item.id, sort_order=index,
          description=item.description, unit=item.unit, contract_quantity=item.quantity, rate=item.rate,
          previous_percentage=previous_percentage, cumulative_percentage=cumulative_percentage,
          this_period_value=this_period_value, cumulative_value=cumulative_value,
        )
      )

    if gross_this_period <= 0 and previous_bill is not None:
      raise TraceException(
        "No additional progress has been measured since the last bill.",
        status_code=409, code="NO_NEW_PROGRESS",
      )

    retention_percentage = payload.retention_percentage or agreement.default_retention_percentage
    retention_cap_percentage = payload.retention_cap_percentage or agreement.default_retention_cap_percentage
    retention_this_period, retention_cumulative = self._calculate_retention(
      gross_this_period=gross_this_period, retention_percentage=retention_percentage,
      retention_cap_percentage=retention_cap_percentage,
      previous_retention_cumulative=previous_bill.retention_cumulative if previous_bill else Decimal("0"),
      contract_total_value=agreement.contract_value,
    )

    net_payable = gross_this_period - retention_this_period - payload.other_deductions_amount

    organization = await self.session.get(Organization, organization_id)

    bill: SubcontractorBill | None = None
    for _attempt in range(3):
      bill_number = await self.repo.get_max_bill_number(organization_id, agreement.id) + 1
      candidate = SubcontractorBill(
        id=uuid4(), organization_id=organization_id, project_id=agreement.project_id, agreement_id=agreement.id,
        bill_number=bill_number, status=SubcontractorBillStatus.DRAFT,
        period_start=payload.period_start, period_end=payload.period_end,
        gross_value_this_period=gross_this_period, gross_value_cumulative=gross_cumulative,
        retention_percentage=retention_percentage, retention_cap_percentage=retention_cap_percentage,
        retention_this_period=retention_this_period, retention_cumulative=retention_cumulative,
        other_deductions_amount=payload.other_deductions_amount, other_deductions_note=payload.other_deductions_note,
        net_payable=net_payable, currency=organization.currency if organization else "PKR",
        notes=payload.notes, created_by_user_id=actor_user_id,
      )
      try:
        await self.repo.create_bill(candidate)
        for line in line_items:
          line.bill_id = candidate.id
        await self.repo.create_bill_line_items(line_items)
        await self.session.commit()
        bill = candidate
        break
      except IntegrityError:
        await self.session.rollback()
        continue

    if bill is None:
      raise TraceException(
        "Unable to generate this bill right now due to a numbering conflict. Please try again.",
        status_code=409, code="SUBCONTRACTOR_BILL_NUMBER_CONFLICT",
      )

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.SUBCONTRACTOR, bill.id, AuditAction.CREATE,
      f"Generated subcontractor bill #{bill.bill_number}, net payable {net_payable} {bill.currency}.",
    )
    return await self.get_bill(organization_id, bill.id)

  async def issue_bill(self, organization_id: UUID, bill_id: UUID, expected_version: int, actor_user_id: UUID) -> SubcontractorBill:
    from datetime import datetime, timezone
    bill = await self.repo.get_bill_for_update(bill_id, organization_id)
    if bill is None:
      raise TraceException("Bill not found.", status_code=404, code="SUBCONTRACTOR_BILL_NOT_FOUND")
    if bill.version != expected_version:
      raise TraceException("This bill was changed by someone else. Reload and try again.", status_code=409, code="SUBCONTRACTOR_BILL_VERSION_CONFLICT")
    if bill.status != SubcontractorBillStatus.DRAFT:
      raise TraceException("Only draft bills can be issued.", status_code=409, code="SUBCONTRACTOR_BILL_NOT_DRAFT")
    bill.status = SubcontractorBillStatus.ISSUED
    bill.issued_at = datetime.now(timezone.utc)
    bill.version += 1
    await self.session.commit()
    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.SUBCONTRACTOR, bill.id, AuditAction.UPDATE,
      f"Issued subcontractor bill #{bill.bill_number}.",
    )
    return bill

  async def cancel_bill(self, organization_id: UUID, bill_id: UUID, expected_version: int, actor_user_id: UUID) -> SubcontractorBill:
    from datetime import datetime, timezone
    bill = await self.repo.get_bill_for_update(bill_id, organization_id)
    if bill is None:
      raise TraceException("Bill not found.", status_code=404, code="SUBCONTRACTOR_BILL_NOT_FOUND")
    if bill.version != expected_version:
      raise TraceException("This bill was changed by someone else. Reload and try again.", status_code=409, code="SUBCONTRACTOR_BILL_VERSION_CONFLICT")
    if bill.status == SubcontractorBillStatus.CANCELLED:
      raise TraceException("This bill is already cancelled.", status_code=409, code="SUBCONTRACTOR_BILL_ALREADY_CANCELLED")
    bill.status = SubcontractorBillStatus.CANCELLED
    bill.cancelled_at = datetime.now(timezone.utc)
    bill.version += 1
    await self.session.commit()
    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.SUBCONTRACTOR, bill.id, AuditAction.UPDATE,
      f"Cancelled subcontractor bill #{bill.bill_number}.",
    )
    return bill

  async def get_bill(self, organization_id: UUID, bill_id: UUID) -> SubcontractorBill:
    bill = await self.repo.get_bill(bill_id, organization_id)
    if bill is None:
      raise TraceException("Bill not found.", status_code=404, code="SUBCONTRACTOR_BILL_NOT_FOUND")
    return bill

  async def list_bills(self, organization_id: UUID, agreement_id: UUID) -> list[SubcontractorBill]:
    await self.get_agreement(organization_id, agreement_id)
    return await self.repo.list_bills_by_agreement(organization_id, agreement_id)

  async def export_pdf(self, organization_id: UUID, bill_id: UUID) -> tuple[bytes, str]:
    bill = await self.get_bill(organization_id, bill_id)
    agreement, subcontractor, project, organization = await self._load_display_context(organization_id, bill.agreement_id)
    pdf_bytes = build_subcontractor_bill_pdf(bill, organization.name, project.name, subcontractor.name)
    return pdf_bytes, f"subcontractor-bill-{bill.bill_number}-{subcontractor.name}.pdf"

  async def export_xlsx(self, organization_id: UUID, bill_id: UUID) -> tuple[bytes, str]:
    bill = await self.get_bill(organization_id, bill_id)
    agreement, subcontractor, project, organization = await self._load_display_context(organization_id, bill.agreement_id)
    xlsx_bytes = build_subcontractor_bill_xlsx(bill, organization.name, project.name, subcontractor.name)
    return xlsx_bytes, f"subcontractor-bill-{bill.bill_number}-{subcontractor.name}.xlsx"

  async def record_advance(
    self, organization_id: UUID, payload_agreement_id: UUID, payload: SubcontractorAdvanceCreateRequest, actor_user_id: UUID,
  ) -> SubcontractorAdvance:
    agreement = await self.get_agreement(organization_id, payload_agreement_id)
    advance = SubcontractorAdvance(
      id=uuid4(), organization_id=organization_id, project_id=agreement.project_id, agreement_id=agreement.id,
      amount=payload.amount, advance_date=payload.advance_date, notes=payload.notes, created_by_user_id=actor_user_id,
    )
    await self.repo.create_advance(advance)
    await self.session.commit()
    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.SUBCONTRACTOR, advance.id, AuditAction.CREATE,
      f"Recorded a {payload.amount} advance for agreement {agreement.id}.",
    )
    return advance

  async def list_advances(self, organization_id: UUID, agreement_id: UUID) -> list[SubcontractorAdvance]:
    await self.get_agreement(organization_id, agreement_id)
    return await self.repo.list_advances(organization_id, agreement_id)

  async def record_payment(
    self, organization_id: UUID, agreement_id: UUID, payload: SubcontractorPaymentCreateRequest, actor_user_id: UUID,
  ) -> SubcontractorPayment:
    agreement = await self.get_agreement(organization_id, agreement_id)

    if payload.advance_recovered_amount > 0:
      _billed, _paid, total_advances, total_recovered = await self.repo.get_ledger_totals(organization_id, agreement.id)
      outstanding = Decimal(str(total_advances)) - Decimal(str(total_recovered))
      if payload.advance_recovered_amount > outstanding:
        raise TraceException(
          f"Cannot recover {payload.advance_recovered_amount} — only {outstanding} in advances is outstanding.",
          status_code=409, code="ADVANCE_RECOVERY_EXCEEDS_BALANCE",
        )

    net_paid = payload.gross_amount - payload.advance_recovered_amount

    payment = SubcontractorPayment(
      id=uuid4(), organization_id=organization_id, project_id=agreement.project_id, agreement_id=agreement.id,
      bill_id=payload.bill_id, gross_amount=payload.gross_amount,
      advance_recovered_amount=payload.advance_recovered_amount, net_paid_amount=net_paid,
      payment_date=payload.payment_date, notes=payload.notes, created_by_user_id=actor_user_id,
    )
    await self.repo.create_payment(payment)
    await self.session.commit()
    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.SUBCONTRACTOR, payment.id, AuditAction.CREATE,
      f"Paid {net_paid} net to subcontractor for agreement {agreement.id}.",
    )
    return payment

  async def list_payments(self, organization_id: UUID, agreement_id: UUID) -> list[SubcontractorPayment]:
    await self.get_agreement(organization_id, agreement_id)
    return await self.repo.list_payments(organization_id, agreement_id)

  async def get_ledger(self, organization_id: UUID, agreement_id: UUID) -> dict:
    agreement = await self.get_agreement(organization_id, agreement_id)
    total_billed, total_paid, total_advances, total_recovered = await self.repo.get_ledger_totals(
      organization_id, agreement.id,
    )
    organization = await self.session.get(Organization, organization_id)
    return {
      "agreement_id": agreement.id,
      "contract_value": agreement.contract_value,
      "total_billed": Decimal(str(total_billed)),
      "total_paid": Decimal(str(total_paid)),
      "outstanding_bill_balance": Decimal(str(total_billed)) - Decimal(str(total_paid)),
      "total_advances_given": Decimal(str(total_advances)),
      "outstanding_advance_balance": Decimal(str(total_advances)) - Decimal(str(total_recovered)),
      "currency": organization.currency if organization else "PKR",
    }

  async def get_project_cost_summary(self, organization_id: UUID, project_id: UUID) -> dict:
    await self._require_project(organization_id, project_id)
    total_billed = await self.repo.get_project_billed_total(organization_id, project_id)
    organization = await self.session.get(Organization, organization_id)
    return {
      "project_id": project_id,
      "total_billed": Decimal(str(total_billed)),
      "currency": organization.currency if organization else "PKR",
    }

  @staticmethod
  def _calculate_retention(
    *, gross_this_period: Decimal, retention_percentage: Decimal, retention_cap_percentage: Decimal | None,
    previous_retention_cumulative: Decimal, contract_total_value: Decimal,
  ) -> tuple[Decimal, Decimal]:
    candidate = (gross_this_period * retention_percentage / Decimal("100")).quantize(Decimal("0.01"))
    if retention_cap_percentage is None:
      retention_this_period = candidate
    else:
      cap_value = (contract_total_value * retention_cap_percentage / Decimal("100")).quantize(Decimal("0.01"))
      headroom = max(cap_value - previous_retention_cumulative, Decimal("0"))
      retention_this_period = min(candidate, headroom)
    return retention_this_period, previous_retention_cumulative + retention_this_period

  async def _require_project(self, organization_id: UUID, project_id: UUID) -> Project:
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")
    return project

  async def _load_display_context(self, organization_id: UUID, agreement_id: UUID):
    agreement = await self.get_agreement(organization_id, agreement_id)
    subcontractor = await self.repo.get(agreement.subcontractor_id, organization_id)
    project = await self._require_project(organization_id, agreement.project_id)
    organization = await self.session.get(Organization, organization_id)
    return agreement, subcontractor, project, organization