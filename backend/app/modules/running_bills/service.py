from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.running_bills.models import RunningBill, RunningBillCollection, RunningBillLineItem, RunningBillStatus
from app.modules.running_bills.repository import RunningBillRepository
from app.modules.audit.service import AuditLogService
from app.modules.running_bills.schemas import RunningBillCreateRequest, RunningBillRecordCollectionRequest, RunningBillVoidCollectionRequest
from app.core.exceptions import TraceException
from decimal import Decimal
from app.modules.identity.models import Organization
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from app.modules.audit.models import AuditAction, AuditEntityType
from app.modules.projects.models import Client, Project
from app.modules.drawings_boq.models import BOQVersion
from app.modules.running_bills.export import build_running_bill_pdf, build_running_bill_xlsx
from app.modules.sales_tax.models import SalesTaxSourceType
from app.modules.sales_tax.service import SalesTaxService
from app.modules.sales_tax.models import SalesTaxAuthority
from app.modules.bank_guarantees.service import BankGuaranteeService
from app.shared.timeutils import to_local_date, today_local

class RunningBillService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = RunningBillRepository(session)
    self.audit = AuditLogService(session)
    self.sales_tax = SalesTaxService(session)
    self.bank_guarantees = BankGuaranteeService(session)

  async def list_bills(self, organization_id: UUID, project_id: UUID) -> list[RunningBill]:
    await self._require_project(organization_id, project_id)
    return await self.repo.list_by_project(organization_id, project_id)

  async def get_bill(self, organization_id: UUID, bill_id: UUID) -> RunningBill:
    bill = await self.repo.get_by_id(bill_id, organization_id)
    if bill is None:
      raise TraceException("Running bill not found.", status_code=404, code="RUNNING_BILL_NOT_FOUND")
    return bill

  async def generate_draft(
    self, organization_id: UUID, payload: RunningBillCreateRequest, actor_user_id: UUID,
  ) -> RunningBill:
    project = await self._require_project(organization_id, payload.project_id)
    await self._require_boq_version(organization_id, payload.project_id, payload.boq_version_id)

    previous_bill = await self.repo.get_last_issued_bill(
      organization_id, payload.project_id, payload.boq_version_id,
    )
    previous_line_by_item = (
      {line.boq_item_id: line for line in previous_bill.line_items} if previous_bill else {}
    )

    boq_items = await self.repo.get_billable_boq_items(organization_id, payload.boq_version_id)
    if not boq_items:
      raise TraceException(
        "This BOQ version has no approved line items to bill against.",
        status_code=409, code="NO_BILLABLE_BOQ_ITEMS",
      )

    billable_item_ids = {item.id for item in boq_items}
    for billed_item_id, billed_line in previous_line_by_item.items():
      if billed_item_id not in billable_item_ids and billed_line.cumulative_value != 0:
        raise TraceException(
          f"'{billed_line.material_name}' was billed in bill #{previous_bill.bill_number} but is no longer an "
          "approved BOQ item. Restore it before generating a new bill.",
          status_code=409, code="BILLED_ITEM_NO_LONGER_APPROVED",
        )

    current_claims = await self.repo.get_latest_approved_claims_as_of(
      organization_id, payload.project_id, payload.period_end,
    )

    line_items: list[RunningBillLineItem] = []
    revised_items: list[str] = []
    gross_this_period = Decimal("0")
    gross_cumulative = Decimal("0")
    contract_total_value = sum(
      ((item.quantity or Decimal("0")) * (item.unit_rate or Decimal("0")) for item in boq_items),
      Decimal("0"),
    )

    for boq_item in boq_items:
      claim = current_claims.get(boq_item.id)
      cumulative_percentage = claim.claimed_percentage if claim is not None else Decimal("0")

      previous_line = previous_line_by_item.get(boq_item.id)
      previous_percentage = previous_line.cumulative_percentage if previous_line is not None else Decimal("0")

      if cumulative_percentage <= 0 and previous_percentage <= 0:
        continue  

      if claim is not None and boq_item.unit_rate is None:
        raise TraceException(
          f"BOQ item '{boq_item.material_name}' has approved progress but no unit rate. "
          "Price the BOQ first.",
          status_code=409, code="NO_RATE_ON_CLAIMED_ITEM",
        )

      unit_rate = boq_item.unit_rate or Decimal("0")
      contract_quantity = boq_item.quantity or Decimal("0")
      if previous_line is not None and (
        previous_line.contract_quantity != contract_quantity or previous_line.unit_rate != unit_rate
      ):
        revised_items.append(boq_item.material_name)

      cumulative_quantity = contract_quantity * cumulative_percentage / Decimal("100")
      previous_quantity = previous_line.cumulative_quantity if previous_line is not None else Decimal("0")
      this_period_quantity = cumulative_quantity - previous_quantity

      cumulative_value = (cumulative_quantity * unit_rate).quantize(Decimal("0.01"))
      previous_value = previous_line.cumulative_value if previous_line is not None else Decimal("0")
      this_period_value = cumulative_value - previous_value

      gross_this_period += this_period_value
      gross_cumulative += cumulative_value

      line_items.append(
        RunningBillLineItem(
          id=uuid4(),
          organization_id=organization_id,
          boq_item_id=boq_item.id,
          sort_order=len(line_items),
          material_name=boq_item.material_name,
          unit=boq_item.unit,
          contract_quantity=contract_quantity,
          unit_rate=unit_rate,
          previous_percentage=previous_percentage,
          cumulative_percentage=cumulative_percentage,
          previous_quantity=previous_quantity,
          cumulative_quantity=cumulative_quantity,
          this_period_quantity=this_period_quantity,
          previous_value=previous_value,
          cumulative_value=cumulative_value,
          this_period_value=this_period_value,
        )
      )

    if not line_items:
      raise TraceException(
        "No progress has been claimed and approved against this BOQ version yet.",
        status_code=409, code="NO_MEASURED_PROGRESS",
      )

    retention_this_period, retention_cumulative = self._calculate_retention(
      gross_this_period=gross_this_period,
      retention_percentage=payload.retention_percentage,
      retention_cap_percentage=payload.retention_cap_percentage,
      previous_retention_cumulative=previous_bill.retention_cumulative if previous_bill else Decimal("0"),
      contract_total_value=contract_total_value,
    )

    if payload.retention_secured_by_guarantee:
      await self.bank_guarantees.require_adequate_guarantee_for_boq_version(
        organization_id, payload.boq_version_id, retention_cumulative,
      )
      net_payable = gross_this_period - payload.advance_recovery_amount - payload.other_deductions_amount
    else:
      net_payable = (
        gross_this_period - retention_this_period
        - payload.advance_recovery_amount - payload.other_deductions_amount
      )

    sales_tax_rate_estimate: Decimal | None = None
    sales_tax_amount_estimate = Decimal("0")
    if payload.sales_tax_authority is not None:
      sales_tax_rate_estimate, sales_tax_amount_estimate = await self.sales_tax.calculate_preview(
        organization_id, payload.sales_tax_authority, gross_this_period,
      )

    organization = await self.session.get(Organization, organization_id)

    conflict: Exception | None = None
    bill: RunningBill | None = None
    for _attempt in range(3):
      bill_number = await self.repo.get_max_bill_number(organization_id, payload.project_id) + 1
      candidate = RunningBill(
        id=uuid4(),
        organization_id=organization_id,
        project_id=payload.project_id,
        boq_version_id=payload.boq_version_id,
        previous_bill_id=previous_bill.id if previous_bill else None,
        bill_number=bill_number,
        status=RunningBillStatus.DRAFT,
        period_start=payload.period_start,
        period_end=payload.period_end,
        gross_value_this_period=gross_this_period,
        gross_value_cumulative=gross_cumulative,
        retention_percentage=payload.retention_percentage,
        retention_cap_percentage=payload.retention_cap_percentage,
        retention_this_period=retention_this_period,
        retention_cumulative=retention_cumulative,
        advance_recovery_amount=payload.advance_recovery_amount,
        other_deductions_amount=payload.other_deductions_amount,
        other_deductions_note=payload.other_deductions_note,
        net_payable=net_payable,
        retention_secured_by_guarantee=payload.retention_secured_by_guarantee,
        sales_tax_authority=payload.sales_tax_authority.value if payload.sales_tax_authority else None,
        sales_tax_rate_percentage=sales_tax_rate_estimate,
        sales_tax_amount=sales_tax_amount_estimate,
        currency=organization.currency if organization else "PKR",
        notes=self._notes_with_revisions(payload.notes, revised_items),
        created_by_user_id=actor_user_id,
      )
      try:
        await self.repo.create(candidate)
        for line in line_items:
          line.bill_id = candidate.id
        await self.repo.create_line_items(line_items)
        await self.session.commit()
        bill = candidate
        conflict = None
        break
      except IntegrityError as exc:
        await self.session.rollback()
        conflict = exc
        continue

    if conflict is not None or bill is None:
      raise TraceException(
        "Unable to generate this bill right now due to a numbering conflict. Please try again.",
        status_code=409, code="RUNNING_BILL_NUMBER_CONFLICT",
      )

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.RUNNING_BILL, bill.id, AuditAction.CREATE,
      f"Generated running bill #{bill.bill_number} for {project.name} "
      f"({payload.period_start} to {payload.period_end}), net payable {net_payable} {bill.currency}.",
    )

    return await self.get_bill(organization_id, bill.id)

  async def issue_bill(self, organization_id: UUID, bill_id: UUID, expected_version: int, actor_user_id: UUID) -> RunningBill:
    bill = await self.repo.get_by_id_for_update(bill_id, organization_id)
    if bill is None:
      raise TraceException("Running bill not found.", status_code=404, code="RUNNING_BILL_NOT_FOUND")
    if bill.version != expected_version:
      raise TraceException(
        "This bill was changed by someone else. Reload and try again.",
        status_code=409, code="RUNNING_BILL_VERSION_CONFLICT",
      )
      raise TraceException("Only draft bills can be issued.", status_code=409, code="RUNNING_BILL_NOT_DRAFT")
    await self.session.execute(select(Project.id).where(Project.id == bill.project_id).with_for_update())
    await self._assert_bill_not_stale(organization_id, bill)

    if bill.retention_secured_by_guarantee:
      await self.bank_guarantees.require_adequate_guarantee_for_boq_version(
        organization_id, bill.boq_version_id, bill.retention_cumulative,
      )

    if bill.sales_tax_authority is not None:
      rate_percentage, tax_amount = await self.sales_tax.calculate_and_record(
        organization_id=organization_id, project_id=bill.project_id,
        authority=SalesTaxAuthority(bill.sales_tax_authority), taxable_amount=bill.gross_value_this_period,
        source_type=SalesTaxSourceType.RUNNING_BILL, source_id=bill.id,
        charge_date=today_local(), actor_user_id=actor_user_id,
      )
      bill.sales_tax_rate_percentage = rate_percentage
      bill.sales_tax_amount = tax_amount

    bill.status = RunningBillStatus.ISSUED
    bill.issued_at = datetime.now(timezone.utc)
    bill.version += 1
    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.RUNNING_BILL, bill.id, AuditAction.UPDATE,
      f"Issued running bill #{bill.bill_number}, net payable {bill.net_payable} {bill.currency}"
      + (f", plus {bill.sales_tax_amount} sales tax" if bill.sales_tax_amount > 0 else "") + ".",
    )
    return bill

  async def cancel_bill(
    self, organization_id: UUID, bill_id: UUID, expected_version: int, actor_user_id: UUID,
    reason: str | None = None,
  ) -> RunningBill:
    bill = await self.repo.get_by_id_for_update(bill_id, organization_id)
    if bill is None:
      raise TraceException("Running bill not found.", status_code=404, code="RUNNING_BILL_NOT_FOUND")
    if bill.version != expected_version:
      raise TraceException(
        "This bill was changed by someone else. Reload and try again.",
        status_code=409, code="RUNNING_BILL_VERSION_CONFLICT",
      )
      
    if bill.status == RunningBillStatus.CANCELLED:
      raise TraceException("This bill is already cancelled.", status_code=409, code="RUNNING_BILL_ALREADY_CANCELLED")

    clean_reason = reason.strip() if reason and reason.strip() else None
    reversed_tax = Decimal("0")

    if bill.status == RunningBillStatus.ISSUED:
      if clean_reason is None or len(clean_reason) < 3:
        raise TraceException(
          "Give a reason for cancelling an issued bill.", status_code=422, code="CANCEL_REASON_REQUIRED",
        )
      await self.session.execute(select(Project.id).where(Project.id == bill.project_id).with_for_update())
      if await self.repo.count_active_collections(organization_id, bill.id) > 0:
        raise TraceException(
          "This bill has collections recorded against it. Void them first, then cancel the bill.",
          status_code=409, code="RUNNING_BILL_HAS_COLLECTIONS",
        )
      if await self.repo.has_later_issued_bill(
        organization_id, bill.project_id, bill.boq_version_id, bill.bill_number,
      ):
        
        raise TraceException(
          "A later bill was issued on top of this one. Cancel the later bill first.",
          status_code=409, code="RUNNING_BILL_HAS_LATER_BILLS",
        )
      if bill.sales_tax_authority is not None:
        reversed_tax = await self.sales_tax.reverse_charges_for_source(
          organization_id=organization_id, source_type=SalesTaxSourceType.RUNNING_BILL, source_id=bill.id,
          reversal_date=today_local(), actor_user_id=actor_user_id,
        )

    was_issued = bill.status == RunningBillStatus.ISSUED
    bill.status = RunningBillStatus.CANCELLED
    bill.cancelled_at = datetime.now(timezone.utc)
    bill.cancel_reason = clean_reason
    bill.version += 1
    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.RUNNING_BILL, bill.id, AuditAction.UPDATE,
      f"Cancelled {'issued ' if was_issued else ''}running bill #{bill.bill_number}"
      + (f" ({clean_reason})" if clean_reason else "")
      + (f"; reversed {reversed_tax} sales tax" if reversed_tax else "") + ".",
    )
    return bill

  async def export_pdf(self, organization_id: UUID, bill_id: UUID) -> tuple[bytes, str]:
    bill = await self.get_bill(organization_id, bill_id)
    project, client, organization = await self._load_display_context(organization_id, bill.project_id)
    pdf_bytes = build_running_bill_pdf(
      bill, organization.name, project.name, project.code, client.name if client else None,
    )
    return pdf_bytes, f"running-bill-{bill.bill_number}-{project.code or project.name}.pdf"

  async def export_xlsx(self, organization_id: UUID, bill_id: UUID) -> tuple[bytes, str]:
    bill = await self.get_bill(organization_id, bill_id)
    project, client, _organization = await self._load_display_context(organization_id, bill.project_id)
    xlsx_bytes = build_running_bill_xlsx(bill, _organization.name, project.name, client.name if client else None)
    return xlsx_bytes, f"running-bill-{bill.bill_number}-{project.code or project.name}.xlsx"

  @staticmethod
  def _notes_with_revisions(notes: str | None, revised_items: list[str]) -> str | None:
    if not revised_items:
      return notes
    line = (
      "Revised since the previous bill (change order): " + ", ".join(revised_items)
      + ". Previous values are carried forward as billed; check the progress % against the revised quantity."
    )
    return f"{notes}\n{line}" if notes else line

  async def _assert_bill_not_stale(self, organization_id: UUID, bill: RunningBill) -> None:
    last_issued = await self.repo.get_last_issued_bill(organization_id, bill.project_id, bill.boq_version_id)
    if (last_issued.id if last_issued else None) != bill.previous_bill_id:
      raise TraceException(
        "Another bill was issued or cancelled after this draft was generated, so its previous values are out of "
        "date. Cancel this draft and generate it again.",
        status_code=409, code="RUNNING_BILL_STALE_PREVIOUS",
      )

    claims = await self.repo.get_latest_approved_claims_as_of(organization_id, bill.project_id, bill.period_end)
    billable = await self.repo.get_billable_boq_items(organization_id, bill.boq_version_id)
    billed_pct = {line.boq_item_id: line.cumulative_percentage for line in bill.line_items}
    
    for item in billable:
      claim = claims.get(item.id)
      current_pct = claim.claimed_percentage if claim is not None else Decimal("0")
      if current_pct != billed_pct.get(item.id, Decimal("0")):
        raise TraceException(
          f"Approved progress changed for '{item.material_name}' after this draft was generated. "
          "Cancel this draft and generate it again.",
          status_code=409, code="RUNNING_BILL_PROGRESS_CHANGED",
        )

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
    result = await self.session.execute(
      select(Project).where(Project.id == project_id, Project.organization_id == organization_id)
    )
    project = result.scalar_one_or_none()
    if project is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")
    return project

  async def _require_boq_version(self, organization_id: UUID, project_id: UUID, boq_version_id: UUID) -> BOQVersion:
    result = await self.session.execute(
      select(BOQVersion).where(
        BOQVersion.id == boq_version_id, BOQVersion.organization_id == organization_id,
        BOQVersion.project_id == project_id,
      )
    )
    version = result.scalar_one_or_none()
    if version is None:
      raise TraceException("BOQ version not found for this project.", status_code=404, code="BOQ_VERSION_NOT_FOUND")
    return version

  async def _load_display_context(self, organization_id: UUID, project_id: UUID):
    project = await self._require_project(organization_id, project_id)
    client = None
    if project.client_id:
      client = (await self.session.execute(select(Client).where(Client.id == project.client_id))).scalar_one_or_none()
    organization = await self.session.get(Organization, organization_id)
    return project, client, organization
  
  async def record_collection(
    self, organization_id: UUID, bill_id: UUID, payload: RunningBillRecordCollectionRequest, actor_user_id: UUID,
  ) -> RunningBill:
    bill = await self.repo.get_by_id_for_update(bill_id, organization_id)
    if bill is None:
      raise TraceException("Running bill not found.", status_code=404, code="RUNNING_BILL_NOT_FOUND")

    # Same key again = the same click arriving twice (double tap, retry on a bad connection): do nothing new.
    if payload.idempotency_key:
      if await self.repo.get_collection_by_key(organization_id, bill.id, payload.idempotency_key) is not None:
        return bill

    if bill.status != RunningBillStatus.ISSUED:
      raise TraceException(
        "Only an issued bill can have collections recorded against it.", status_code=409, code="RUNNING_BILL_NOT_ISSUED",
      )
    if payload.collection_date > today_local():
      raise TraceException("The collection date cannot be in the future.", status_code=422, code="COLLECTION_DATE_IN_FUTURE")
    if bill.issued_at is not None and payload.collection_date < to_local_date(bill.issued_at):
      raise TraceException(
        "The collection date cannot be before the bill was issued.", status_code=422, code="COLLECTION_BEFORE_ISSUE",
      )

    credited = payload.amount + payload.client_wht_amount
    total_due = bill.net_payable + bill.sales_tax_amount
    outstanding = total_due - bill.collected_amount
    if credited > outstanding:
      raise TraceException(
        f"Cannot record {credited} — only {outstanding} is still outstanding on this bill.",
        status_code=409, code="COLLECTION_EXCEEDS_OUTSTANDING",
      )

    try:
      await self.repo.create_collection(RunningBillCollection(
        id=uuid4(), organization_id=organization_id, bill_id=bill.id, project_id=bill.project_id,
        amount_received=payload.amount, client_wht_amount=payload.client_wht_amount, credited_amount=credited,
        collection_date=payload.collection_date, reference=payload.reference,
        idempotency_key=payload.idempotency_key, recorded_by_user_id=actor_user_id,
      ))
    except IntegrityError:
      await self.session.rollback()
      return await self.get_bill(organization_id, bill_id)

    bill.collected_amount = bill.collected_amount + credited
    if bill.collected_amount >= total_due:
      bill.fully_collected_at = datetime.now(timezone.utc)
    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.RUNNING_BILL, bill.id, AuditAction.UPDATE,
      f"Recorded {payload.amount} received"
      + (f" plus {payload.client_wht_amount} tax withheld by client" if payload.client_wht_amount else "")
      + f" on {payload.collection_date} against running bill #{bill.bill_number}"
      + (" (fully collected)." if bill.collected_amount >= total_due else "."),
    )
    return bill

  async def list_collections(self, organization_id: UUID, bill_id: UUID) -> list[RunningBillCollection]:
    await self.get_bill(organization_id, bill_id)
    return await self.repo.list_collections(organization_id, bill_id)

  async def void_collection(
    self, organization_id: UUID, bill_id: UUID, collection_id: UUID,
    payload: RunningBillVoidCollectionRequest, actor_user_id: UUID,
  ) -> RunningBill:
    bill = await self.repo.get_by_id_for_update(bill_id, organization_id)
    if bill is None:
      raise TraceException("Running bill not found.", status_code=404, code="RUNNING_BILL_NOT_FOUND")
    collection = await self.repo.get_collection(collection_id, bill.id, organization_id)
    if collection is None:
      raise TraceException("Collection not found.", status_code=404, code="COLLECTION_NOT_FOUND")
    if collection.voided_at is not None:
      raise TraceException("This collection is already voided.", status_code=409, code="COLLECTION_ALREADY_VOIDED")

    collection.voided_at = datetime.now(timezone.utc)
    collection.voided_by_user_id = actor_user_id
    collection.void_reason = payload.reason.strip()
    bill.collected_amount = bill.collected_amount - collection.credited_amount
    if bill.collected_amount < bill.net_payable + bill.sales_tax_amount:
      bill.fully_collected_at = None
    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.RUNNING_BILL, bill.id, AuditAction.UPDATE,
      f"Voided a {collection.credited_amount} collection dated {collection.collection_date} on running bill "
      f"#{bill.bill_number} ({collection.void_reason}).",
    )
    return bill