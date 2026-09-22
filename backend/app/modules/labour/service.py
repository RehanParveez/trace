from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.labour.repository import LabourRepository
from app.modules.audit.service import AuditLogService
from app.modules.labour.schemas import (LabourSourceCreateRequest, AttendanceBulkCreateRequest, LabourAdvanceCreateRequest, LabourDeploymentCreateRequest, LabourDeploymentUpdateRequest, LabourPaymentCreateRequest,
  LabourSourceUpdateRequest, LabourWorkerCreateRequest, LabourWorkerUpdateRequest,
)
from app.modules.labour.models import LabourSource, LabourAdvance, LabourAttendance, LabourDeployment, LabourDeploymentStatus, LabourPayment, LabourWorker
from uuid import UUID, uuid4
from decimal import Decimal
from datetime import date
from app.core.exceptions import TraceException
from app.modules.audit.models import AuditAction, AuditEntityType
from app.modules.identity.models import Organization
from sqlalchemy import select
from app.modules.projects.repository import ProjectRepository
from app.modules.withholding_tax.models import WHTSourceType
from app.modules.withholding_tax.service import WithholdingTaxService

class LabourService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = LabourRepository(session)
    self.projects = ProjectRepository(session)
    self.audit = AuditLogService(session)
    self.withholding_tax = WithholdingTaxService(session)

  async def create_source(self, organization_id: UUID, payload: LabourSourceCreateRequest) -> LabourSource:
    source = LabourSource(
      id=uuid4(), organization_id=organization_id, name=payload.name.strip(),
      source_type=payload.source_type, contact_name=payload.contact_name, contact_phone=payload.contact_phone,
      is_active_taxpayer=payload.is_active_taxpayer, notes=payload.notes,
    )
    await self.repo.create_source(source)
    await self.session.commit()
    return source

  async def update_source(
    self, organization_id: UUID, source_id: UUID, payload: LabourSourceUpdateRequest,
  ) -> LabourSource:
    source = await self.repo.get_source(source_id, organization_id)
    if source is None:
      raise TraceException("Labour source not found.", status_code=404, code="LABOUR_SOURCE_NOT_FOUND")
    if payload.name is not None:
      source.name = payload.name.strip()
    if payload.contact_name is not None:
      source.contact_name = payload.contact_name
    if payload.contact_phone is not None:
      source.contact_phone = payload.contact_phone
    if payload.is_active_taxpayer is not None:
      source.is_active_taxpayer = payload.is_active_taxpayer
    if payload.is_active is not None:
      source.is_active = payload.is_active
    if payload.notes is not None:
      source.notes = payload.notes
    await self.session.commit()
    return source

  async def list_sources(self, organization_id: UUID) -> list[LabourSource]:
    return await self.repo.list_sources(organization_id)

  async def create_worker(self, organization_id: UUID, payload: LabourWorkerCreateRequest) -> LabourWorker:
    source = await self.repo.get_source(payload.source_id, organization_id)
    if source is None:
      raise TraceException("Labour source not found.", status_code=404, code="LABOUR_SOURCE_NOT_FOUND")

    worker = LabourWorker(
      id=uuid4(), organization_id=organization_id, source_id=payload.source_id,
      name=payload.name.strip(), trade=payload.trade.strip(), cnic=payload.cnic, phone=payload.phone,
      default_daily_rate=payload.default_daily_rate,
    )
    await self.repo.create_worker(worker)
    await self.session.commit()
    return worker

  async def update_worker(
    self, organization_id: UUID, worker_id: UUID, payload: LabourWorkerUpdateRequest,
  ) -> LabourWorker:
    worker = await self.repo.get_worker(worker_id, organization_id)
    if worker is None:
      raise TraceException("Labour worker not found.", status_code=404, code="LABOUR_WORKER_NOT_FOUND")
    if payload.name is not None:
      worker.name = payload.name.strip()
    if payload.trade is not None:
      worker.trade = payload.trade.strip()
    if payload.cnic is not None:
      worker.cnic = payload.cnic
    if payload.phone is not None:
      worker.phone = payload.phone
    if payload.default_daily_rate is not None:
      worker.default_daily_rate = payload.default_daily_rate
    if payload.is_active is not None:
      worker.is_active = payload.is_active
    await self.session.commit()
    return worker

  async def list_workers(self, organization_id: UUID, source_id: UUID | None) -> list[LabourWorker]:
    return await self.repo.list_workers(organization_id, source_id)

  async def create_deployment(
    self, organization_id: UUID, project_id: UUID, payload: LabourDeploymentCreateRequest,
  ) -> LabourDeployment:
    await self._require_project(organization_id, project_id)
    source = await self.repo.get_source(payload.source_id, organization_id)
    if source is None:
      raise TraceException("Labour source not found.", status_code=404, code="LABOUR_SOURCE_NOT_FOUND")

    if payload.worker_id is not None:
      worker = await self.repo.get_worker(payload.worker_id, organization_id)
      if worker is None:
        raise TraceException("Labour worker not found.", status_code=404, code="LABOUR_WORKER_NOT_FOUND")
      if worker.source_id != payload.source_id:
        raise TraceException(
          "This worker does not belong to the selected source.", status_code=422, code="WORKER_SOURCE_MISMATCH",
        )

    deployment = LabourDeployment(
      id=uuid4(), organization_id=organization_id, project_id=project_id, source_id=payload.source_id,
      worker_id=payload.worker_id, trade=payload.trade.strip(), daily_rate=payload.daily_rate,
      start_date=payload.start_date, status=LabourDeploymentStatus.ACTIVE,
    )
    await self.repo.create_deployment(deployment)
    await self.session.commit()
    return deployment

  async def update_deployment(
    self, organization_id: UUID, deployment_id: UUID, payload: LabourDeploymentUpdateRequest,
  ) -> LabourDeployment:
    deployment = await self.repo.get_deployment(deployment_id, organization_id)
    if deployment is None:
      raise TraceException("Deployment not found.", status_code=404, code="DEPLOYMENT_NOT_FOUND")

    if payload.end_date is not None:
      deployment.end_date = payload.end_date
    if payload.status is not None:
      deployment.status = payload.status
    await self.session.commit()
    return deployment

  async def list_deployments(self, organization_id: UUID, project_id: UUID) -> list[LabourDeployment]:
    await self._require_project(organization_id, project_id)
    return await self.repo.list_deployments(organization_id, project_id)

  async def bulk_record_attendance(
    self, organization_id: UUID, project_id: UUID, payload: AttendanceBulkCreateRequest, actor_user_id: UUID,
  ) -> tuple[int, int, list[LabourAttendance]]:
    await self._require_project(organization_id, project_id)

    created = 0
    updated = 0
    results: list[LabourAttendance] = []

    for entry in payload.entries:
      deployment = await self.repo.get_deployment(entry.deployment_id, organization_id)
      if deployment is None or deployment.project_id != project_id:
        raise TraceException(
          "One of these deployments does not belong to this project.",
          status_code=404, code="DEPLOYMENT_NOT_FOUND",
        )

      if deployment.worker_id is not None and entry.units_present not in (Decimal("0"), Decimal("0.5"), Decimal("1")):
        raise TraceException(
          "A named worker's attendance must be 0 (absent), 0.5 (half day) or 1 (present).",
          status_code=422, code="INVALID_ATTENDANCE_VALUE",
        )

      existing = await self.repo.get_attendance_for_deployment_date(entry.deployment_id, entry.attendance_date)
      if existing is not None:
        existing.units_present = entry.units_present
        existing.notes = entry.notes
        existing.recorded_by_user_id = actor_user_id
        results.append(existing)
        updated += 1
      else:
        record = LabourAttendance(
          id=uuid4(), organization_id=organization_id, project_id=project_id,
          deployment_id=entry.deployment_id, attendance_date=entry.attendance_date,
          units_present=entry.units_present, notes=entry.notes, recorded_by_user_id=actor_user_id,
        )
        self.session.add(record)
        results.append(record)
        created += 1

    await self.session.commit()
    return created, updated, results

  async def list_attendance(
    self, organization_id: UUID, project_id: UUID, period_start: date | None, period_end: date | None,
  ) -> list[LabourAttendance]:
    await self._require_project(organization_id, project_id)
    return await self.repo.list_attendance(organization_id, project_id, period_start, period_end)

  async def get_day_attendance_total(self, organization_id: UUID, project_id: UUID, attendance_date: date):
    rows = await self.repo.get_accrued_cost(organization_id, project_id, attendance_date, attendance_date)

    attendance_rows = await self.repo.list_attendance(organization_id, project_id, attendance_date, attendance_date)
    totals: dict[str, Decimal] = {}
    for record in attendance_rows:
      deployment = await self.repo.get_deployment(record.deployment_id, organization_id)
      if deployment is None:
        continue
      totals[deployment.trade] = totals.get(deployment.trade, Decimal("0")) + record.units_present
    total_present = sum(totals.values(), Decimal("0"))
    return total_present, [(trade, float(count)) for trade, count in totals.items()]

  async def record_advance(
    self, organization_id: UUID, project_id: UUID, payload: LabourAdvanceCreateRequest, actor_user_id: UUID,
  ) -> LabourAdvance:
    await self._require_project(organization_id, project_id)
    source = await self.repo.get_source(payload.source_id, organization_id)
    if source is None:
      raise TraceException("Labour source not found.", status_code=404, code="LABOUR_SOURCE_NOT_FOUND")

    advance = LabourAdvance(
      id=uuid4(), organization_id=organization_id, project_id=project_id, source_id=payload.source_id,
      worker_id=payload.worker_id, amount=payload.amount, advance_date=payload.advance_date,
      notes=payload.notes, created_by_user_id=actor_user_id,
    )
    self.session.add(advance)
    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.LABOUR, advance.id, AuditAction.CREATE,
      f"Recorded a labour advance of {payload.amount} against {source.name}.",
    )
    return advance

  async def list_advances(self, organization_id: UUID, project_id: UUID) -> list[LabourAdvance]:
    await self._require_project(organization_id, project_id)
    return await self.repo.list_advances(organization_id, project_id)

  async def record_payment(
    self, organization_id: UUID, project_id: UUID, payload: LabourPaymentCreateRequest, actor_user_id: UUID,
  ) -> LabourPayment:
    await self._require_project(organization_id, project_id)
    source = await self.repo.get_source(payload.source_id, organization_id)
    if source is None:
      raise TraceException("Labour source not found.", status_code=404, code="LABOUR_SOURCE_NOT_FOUND")

    if payload.wht_category is not None and source.source_type != LabourSourceType.CONTRACTOR:
      raise TraceException(
        "Withholding tax here applies to contractor-sourced labour payments only, not direct employees.",
        status_code=422, code="WHT_NOT_APPLICABLE_TO_DIRECT_LABOUR",
      )

    if payload.advance_recovered_amount > 0:
      total_advances, total_recovered = await self.repo.get_advance_balance(
        organization_id, project_id, payload.source_id, payload.worker_id,
      )
      outstanding = Decimal(str(total_advances)) - Decimal(str(total_recovered))
      if payload.advance_recovered_amount > outstanding:
        raise TraceException(
          f"Cannot recover {payload.advance_recovered_amount} — only {outstanding} in advances is outstanding.",
          status_code=409, code="ADVANCE_RECOVERY_EXCEEDS_BALANCE",
        )

    payment_id = uuid4()
    wht_rate_percentage: Decimal | None = None
    wht_deducted_amount = Decimal("0")

    if payload.wht_category is not None:
      wht_rate_percentage, wht_deducted_amount = await self.withholding_tax.calculate_and_record(
        organization_id=organization_id, project_id=project_id, category=payload.wht_category,
        gross_amount=payload.gross_wage_amount, is_filer=source.is_active_taxpayer,
        payee_name=source.name, payee_ntn_or_cnic=None,
        source_type=WHTSourceType.LABOUR_PAYMENT, source_id=payment_id, actor_user_id=actor_user_id,
      )

    net_paid = payload.gross_wage_amount - payload.advance_recovered_amount - wht_deducted_amount

    payment = LabourPayment(
      id=payment_id, organization_id=organization_id, project_id=project_id, source_id=payload.source_id,
      worker_id=payload.worker_id, period_start=payload.period_start, period_end=payload.period_end,
      gross_wage_amount=payload.gross_wage_amount, advance_recovered_amount=payload.advance_recovered_amount,
      wht_category=payload.wht_category.value if payload.wht_category else None,
      wht_rate_percentage=wht_rate_percentage, wht_deducted_amount=wht_deducted_amount,
      net_paid_amount=net_paid, payment_date=payload.payment_date, notes=payload.notes,
      created_by_user_id=actor_user_id,
    )
    self.session.add(payment)
    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.LABOUR, payment.id, AuditAction.CREATE,
      f"Paid {net_paid} net wages to {source.name} for {payload.period_start} to {payload.period_end}"
      + (f" (WHT: {wht_deducted_amount})" if wht_deducted_amount > 0 else "") + ".",
    )
    return payment

  async def list_payments(self, organization_id: UUID, project_id: UUID) -> list[LabourPayment]:
    await self._require_project(organization_id, project_id)
    return await self.repo.list_payments(organization_id, project_id)

  async def get_cost(
    self, organization_id: UUID, project_id: UUID, period_start: date, period_end: date,
    source_id: UUID | None, worker_id: UUID | None,
  ) -> Decimal:
    await self._require_project(organization_id, project_id)
    rows = await self.repo.get_accrued_cost(
      organization_id, project_id, period_start, period_end, source_id, worker_id,
    )
    return sum((Decimal(str(cost)) for _trade, cost in rows), Decimal("0"))

  async def get_balance(
    self, organization_id: UUID, project_id: UUID, source_id: UUID, worker_id: UUID | None,
  ) -> Decimal:
    await self._require_project(organization_id, project_id)
    total_advances, total_recovered = await self.repo.get_advance_balance(
      organization_id, project_id, source_id, worker_id,
    )
    return Decimal(str(total_advances)) - Decimal(str(total_recovered))

  async def get_project_summary(self, organization_id: UUID, project_id: UUID, period_start: date, period_end: date):
    await self._require_project(organization_id, project_id)
    cost_rows = await self.repo.get_accrued_cost(organization_id, project_id, period_start, period_end)
    total_advances, total_recovered = await self.repo.get_project_labour_totals(organization_id, project_id)
    total_cost = sum((Decimal(str(cost)) for _trade, cost in cost_rows), Decimal("0"))

    organization = await self.session.get(Organization, organization_id)

    return {
      "total_accrued_cost": total_cost,
      "cost_by_trade": [{"trade": trade, "cost": Decimal(str(cost))} for trade, cost in cost_rows],
      "total_advances_given": Decimal(str(total_advances)),
      "total_payments_made": Decimal(str(total_recovered)),
      "outstanding_advance_balance": Decimal(str(total_advances)) - Decimal(str(total_recovered)),
      "currency": organization.currency if organization else "PKR",
    }

  async def _require_project(self, organization_id: UUID, project_id: UUID):
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException(
        "Project not found.",
        status_code=404,
        code="PROJECT_NOT_FOUND",
      )
    return project