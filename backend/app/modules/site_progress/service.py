from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.site_progress.repository import SiteProgressRepository
from app.modules.projects.repository import ProjectRepository
from uuid import UUID, uuid4
from app.modules.site_progress.schemas import SiteLogCreateRequest, SiteLogUpdateRequest
from app.modules.site_progress.models import SiteLogEntry
from app.core.exceptions import TraceException
from app.modules.procurement.repository import ProcurementRepository
from app.shared.storage import generate_presigned_url
from datetime import date
from decimal import Decimal

class SiteProgressService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = SiteProgressRepository(session)
    self.projects = ProjectRepository(session)
    self.procurement = ProcurementRepository(session)

  async def list_logs(
    self,
    organization_id: UUID,
    project_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
  ) -> list[SiteLogEntry]:
    if project_id is not None:
      await self._ensure_project(organization_id, project_id)
    return await self.repo.list_logs(
      organization_id, project_id, skip=skip, limit=limit,
    )

  async def create_log(
    self,
    organization_id: UUID,
    user_id: UUID,
    payload: SiteLogCreateRequest,
  ) -> SiteLogEntry:
    await self._ensure_project(organization_id, payload.project_id)
    entry = SiteLogEntry(
      id=uuid4(),
      organization_id=organization_id,
      project_id=payload.project_id,
      log_date=payload.log_date,
      workforce_count=payload.workforce_count,
      weather=payload.weather.strip() if payload.weather else None,
      work_done=payload.work_done.strip() if payload.work_done else None,
      blockers=payload.blockers.strip() if payload.blockers else None,
      client_instructions=payload.client_instructions.strip() if payload.client_instructions else None,
      notes=payload.notes.strip() if payload.notes else None,
      created_by=user_id,
    )
    await self.repo.create(entry)
    await self.session.commit()
    return entry

  async def update_log(
    self,
    organization_id: UUID,
    log_id: UUID,
    payload: SiteLogUpdateRequest,
  ) -> SiteLogEntry:
    entry = await self.repo.get_by_id(log_id, organization_id)
    if entry is None:
      raise TraceException(
        "Site log not found.", status_code=404, code="SITE_LOG_NOT_FOUND",
      )
    if payload.log_date is not None:
      entry.log_date = payload.log_date
    if payload.workforce_count is not None:
      entry.workforce_count = payload.workforce_count
    if payload.weather is not None:
      entry.weather = payload.weather.strip() or None
    if payload.work_done is not None:
      entry.work_done = payload.work_done.strip() or None
    if payload.client_instructions is not None:
      entry.client_instructions = payload.client_instructions.strip() or None
    if payload.blockers is not None:
      entry.blockers = payload.blockers.strip() or None
    if payload.notes is not None:
      entry.notes = payload.notes.strip() or None
    await self.session.flush()
    await self.session.commit()
    return entry

  async def get_daily_report(
    self, organization_id: UUID, project_id: UUID, report_date: date,
  ) -> dict:
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")

    logs = await self.repo.list_logs_for_date(organization_id, project_id, report_date)
    manpower = await self.repo.get_manpower_for_date(organization_id, project_id, report_date)
    manpower_total = sum((units for _trade, units in manpower), Decimal("0"))
    reported = [log.workforce_count for log in logs if log.workforce_count is not None]
    reported_workforce = max(reported) if reported else None
    mismatch = (
      reported_workforce is not None and manpower_total > 0
      and abs(Decimal(reported_workforce) - manpower_total) > Decimal("0.5")
    )

    deliveries = await self.procurement.list_deliveries(
      organization_id, project_id=project_id, date_from=report_date, date_to=report_date, include_voided=False,
    )
    issues = await self.repo.list_issues_for_date(organization_id, project_id, report_date)
    photos, photo_count = await self.repo.list_photos_for_date(organization_id, project_id, report_date)

    def texts(attribute: str) -> list[str]:
      return [getattr(log, attribute) for log in logs if getattr(log, attribute)]

    weather = next((log.weather for log in logs if log.weather), None)
    return {
      "project_id": project_id, "project_name": project.name, "report_date": report_date,
      "logs": logs, "weather": weather,
      "work_done": texts("work_done"), "blockers": texts("blockers"),
      "client_instructions": texts("client_instructions"), "notes": texts("notes"),
      "manpower_total": manpower_total,
      "manpower": [{"trade": trade, "units": units} for trade, units in manpower],
      "reported_workforce": reported_workforce, "manpower_mismatch": bool(mismatch),
      "deliveries": [
        {"material_name": req.material_name, "unit": req.unit, "quantity": d.quantity,
         "supplier_name": d.supplier_name, "invoice_number": d.invoice_number}
        for d, req in deliveries
      ],
      "issues": [
        {"material_name": i.material_name, "unit": i.unit, "quantity": i.quantity,
         "issue_type": i.issue_type.value, "issued_to": i.issued_to}
        for i in issues
      ],
      "photos": [
        {"photo_id": p.id, "photo_url": generate_presigned_url(p.storage_key),
         "location_text": p.location_text, "caption": p.caption_raw}
        for p in photos
      ],
      "photo_count": photo_count,
    }

  async def delete_log(self, organization_id: UUID, log_id: UUID) -> None:
    entry = await self.repo.get_by_id(log_id, organization_id)
    if entry is None:
      raise TraceException(
        "Site log not found.", status_code=404, code="SITE_LOG_NOT_FOUND",
      )
    await self.repo.delete(entry)
    await self.session.commit()

  async def _ensure_project(self, organization_id: UUID, project_id: UUID) -> None:
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException(
        "Project not found.", status_code=404, code="PROJECT_NOT_FOUND",
      )