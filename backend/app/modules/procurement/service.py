from __future__ import annotations
from app.modules.procurement.models import ProcurementStatus, ProcurementRequest
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.procurement.schemas import ProcurementCreateRequest, ProcurementStatusUpdateRequest
from app.modules.procurement.repository import ProcurementRepository
from app.modules.projects.repository import ProjectRepository
from uuid import UUID, uuid4
from app.core.exceptions import TraceException

ALLOWED_TRANSITIONS: dict[ProcurementStatus, set[ProcurementStatus]] = {
  ProcurementStatus.REQUESTED: {
    ProcurementStatus.APPROVED, ProcurementStatus.CANCELLED,
  },
  ProcurementStatus.APPROVED: {
    ProcurementStatus.ORDERED, ProcurementStatus.CANCELLED,
  },
  ProcurementStatus.ORDERED: {
    ProcurementStatus.RECEIVED, ProcurementStatus.CANCELLED,
  },
  ProcurementStatus.RECEIVED: set(),
  ProcurementStatus.CANCELLED: set(),
}

class ProcurementService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = ProcurementRepository(session)
    self.projects = ProjectRepository(session)

  async def list_requests(
    self,
    organization_id: UUID,
    project_id: UUID | None = None,
    status: ProcurementStatus | None = None,
    skip: int = 0,
    limit: int = 100,
  ) -> list[ProcurementRequest]:
    if project_id is not None:
      await self._ensure_project(organization_id, project_id)
    return await self.repo.list_requests(
      organization_id, project_id, status, skip, limit,
    )
  
  async def get_organization_summary(
    self, organization_id: UUID,
  ) -> dict:
    return await self.repo.get_organization_summary(organization_id)

  async def create_request(
    self,
    organization_id: UUID,
    user_id: UUID,
    payload: ProcurementCreateRequest,
  ) -> ProcurementRequest:
    await self._ensure_project(organization_id, payload.project_id)
    req = ProcurementRequest(
      id=uuid4(),
      organization_id=organization_id,
      project_id=payload.project_id,
      material_name=payload.material_name.strip(),
      quantity=payload.quantity,
      unit=payload.unit.strip(),
      estimated_amount=payload.estimated_amount,
      needed_by_date=payload.needed_by_date,
      notes=payload.notes.strip() if payload.notes else None,
      requested_by=user_id,
      status=ProcurementStatus.REQUESTED,
    )
    await self.repo.create(req)
    await self.session.commit()
    return req

  async def update_status(
    self,
    organization_id: UUID,
    request_id: UUID,
    payload: ProcurementStatusUpdateRequest,
  ) -> ProcurementRequest:
    req = await self.repo.get_by_id(request_id, organization_id)
    if req is None:
      raise TraceException(
        "Procurement request not found.",
        status_code=404, code="PROCUREMENT_REQUEST_NOT_FOUND",
      )
    allowed = ALLOWED_TRANSITIONS.get(req.status, set())
    if payload.status not in allowed:
      raise TraceException(
        f"Cannot transition from {req.status.value} to {payload.status.value}.",
        status_code=409, code="INVALID_STATUS_TRANSITION",
      )
    req.status = payload.status
    await self.session.flush()
    await self.session.commit()
    return req

  async def _ensure_project(self, organization_id: UUID, project_id: UUID) -> None:
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException(
        "Project not found.", status_code=404, code="PROJECT_NOT_FOUND",
      )