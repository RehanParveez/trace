from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.site_progress.repository import SiteProgressRepository
from app.modules.projects.repository import ProjectRepository
from uuid import UUID, uuid4
from app.modules.site_progress.schemas import SiteLogCreateRequest, SiteLogUpdateRequest
from app.modules.site_progress.models import SiteLogEntry
from app.core.exceptions import TraceException

class SiteProgressService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = SiteProgressRepository(session)
    self.projects = ProjectRepository(session)

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
      blockers=payload.blockers.strip() if payload.blockers else None,
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
    if payload.blockers is not None:
      entry.blockers = payload.blockers.strip() or None
    if payload.notes is not None:
      entry.notes = payload.notes.strip() or None
    await self.session.flush()
    await self.session.commit()
    return entry

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