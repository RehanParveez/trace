from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.running_bills.models import RunningBill, RunningBillLineItem, RunningBillStatus
from app.modules.running_bills.repository import RunningBillRepository
from app.modules.audit.service import AuditLogService
from app.modules.running_bills.schemas import RunningBillCreateRequest
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

class RunningBillService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = RunningBillRepository(session)
    self.audit = AuditLogService(session)
    self.sales_tax = SalesTaxService(session)

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

    current_claims = await self.repo.get_latest_approved_claims_as_of(
      organization_id, payload.project_id, payload.period_end,
    )

    line_items: list[RunningBillLineItem] = []
    gross_this_period = Decimal("0")
    gross_cumulative = Decimal("0")
    contract_total_value = Decimal("0")

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
      contract_total_value += contract_quantity * unit_rate

      cumulative_quantity = contract_quantity * cumulative_percentage / Decimal("100")
      previous_quantity = contract_quantity * previous_percentage / Decimal("100")
      this_period_quantity = cumulative_quantity - previous_quantity

      cumulative_value = cumulative_quantity * unit_rate
      previous_value = previous_quantity * unit_rate
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
        sales_tax_authority=payload.sales_tax_authority.value if payload.sales_tax_authority else None,
        sales_tax_rate_percentage=sales_tax_rate_estimate,
        sales_tax_amount=sales_tax_amount_estimate,
        currency=organization.currency if organization else "PKR",
        notes=payload.notes,
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
    if bill.status != RunningBillStatus.DRAFT:
      raise TraceException("Only draft bills can be issued.", status_code=409, code="RUNNING_BILL_NOT_DRAFT")

    if bill.sales_tax_authority is not None:
      rate_percentage, tax_amount = await self.sales_tax.calculate_and_record(
        organization_id=organization_id, project_id=bill.project_id,
        authority=SalesTaxAuthority(bill.sales_tax_authority), taxable_amount=bill.gross_value_this_period,
        source_type=SalesTaxSourceType.RUNNING_BILL, source_id=bill.id,
        charge_date=datetime.now(timezone.utc).date(), actor_user_id=actor_user_id,
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

    bill.status = RunningBillStatus.CANCELLED
    bill.cancelled_at = datetime.now(timezone.utc)
    bill.version += 1
    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.RUNNING_BILL, bill.id, AuditAction.UPDATE,
      f"Cancelled running bill #{bill.bill_number}.",
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