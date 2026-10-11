from __future__ import annotations
from app.modules.procurement.models import ProcurementDelivery, ProcurementStatus, ProcurementRequest
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.procurement.schemas import ProcurementCreateRequest, ProcurementDeliveryCreateRequest, ProcurementDeliveryVoidRequest, ProcurementStatusUpdateRequest
from app.modules.procurement.repository import ProcurementRepository
from app.modules.projects.repository import ProjectRepository
from app.modules.material_stock.repository import MaterialStockRepository
from app.shared.timeutils import today_local
from datetime import date, datetime, timezone
from decimal import Decimal
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
    self.stock = MaterialStockRepository(session)

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
    requests = await self.repo.list_requests(
      organization_id, project_id, status, skip, limit,
    )
    await self._attach_delivered_quantity(organization_id, requests)
    return requests

  async def _attach_delivered_quantity(
    self, organization_id: UUID, requests: list[ProcurementRequest],
  ) -> None:
    delivered = await self.repo.get_delivered_quantities(organization_id, [r.id for r in requests])
    for req in requests:
      req.delivered_quantity = delivered.get(req.id, Decimal("0"))
  
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
    req.delivered_quantity = Decimal("0")
    return req

  async def update_status(
    self,
    organization_id: UUID,
    request_id: UUID,
    payload: ProcurementStatusUpdateRequest,
    actor_user_id: UUID | None = None,
  ) -> ProcurementRequest:
    req = await self.repo.get_by_id_for_update(request_id, organization_id)
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
    if payload.supplier_name and payload.supplier_name.strip():
      req.supplier_name = payload.supplier_name.strip()
    if payload.status == ProcurementStatus.RECEIVED and not await self.repo.has_deliveries(req.id, organization_id):
      # "Mark received" with no delivery history means the whole order arrived: record it as one delivery so the
      # stock register and the cost summary work from the same records.
      await self.repo.create_delivery(ProcurementDelivery(
        id=uuid4(), organization_id=organization_id, project_id=req.project_id, request_id=req.id,
        received_date=today_local(), quantity=req.quantity, supplier_name=req.supplier_name,
        recorded_by_user_id=actor_user_id,
      ))
    req.status = payload.status
    await self.session.flush()
    await self.session.commit()
    await self._attach_delivered_quantity(organization_id, [req])
    return req

  async def record_delivery(
    self,
    organization_id: UUID,
    request_id: UUID,
    payload: ProcurementDeliveryCreateRequest,
    actor_user_id: UUID,
  ) -> dict:
    req = await self.repo.get_by_id_for_update(request_id, organization_id)
    if req is None:
      raise TraceException(
        "Procurement request not found.", status_code=404, code="PROCUREMENT_REQUEST_NOT_FOUND",
      )
    if req.status not in (ProcurementStatus.APPROVED, ProcurementStatus.ORDERED):
      raise TraceException(
        "Deliveries can only be recorded against an approved or ordered request.",
        status_code=409, code="DELIVERY_NOT_ALLOWED",
      )
    if payload.received_date > today_local():
      raise TraceException(
        "The delivery date cannot be in the future.", status_code=422, code="DELIVERY_DATE_IN_FUTURE",
      )
    already = await self.repo.get_delivered_quantity(req.id, organization_id)
    total = already + payload.quantity
    if total > req.quantity and not payload.allow_over_delivery:
      raise TraceException(
        f"This would make {total} {req.unit} delivered against {req.quantity} {req.unit} ordered. "
        "Confirm the over-delivery to record it.",
        status_code=409, code="DELIVERY_EXCEEDS_ORDER",
      )

    supplier = payload.supplier_name.strip() if payload.supplier_name and payload.supplier_name.strip() else req.supplier_name
    delivery = await self.repo.create_delivery(ProcurementDelivery(
      id=uuid4(), organization_id=organization_id, project_id=req.project_id, request_id=req.id,
      received_date=payload.received_date, quantity=payload.quantity, supplier_name=supplier,
      invoice_number=payload.invoice_number.strip() if payload.invoice_number else None,
      amount=payload.amount, notes=payload.notes.strip() if payload.notes else None,
      recorded_by_user_id=actor_user_id,
    ))
    if supplier and not req.supplier_name:
      req.supplier_name = supplier
    if total >= req.quantity:
      req.status = ProcurementStatus.RECEIVED
    elif req.status == ProcurementStatus.APPROVED:
      req.status = ProcurementStatus.ORDERED
    await self.session.flush()
    await self.session.commit()
    return self._delivery_dict(delivery, req)

  async def void_delivery(
    self,
    organization_id: UUID,
    delivery_id: UUID,
    payload: ProcurementDeliveryVoidRequest,
    actor_user_id: UUID,
  ) -> dict:
    delivery = await self.repo.get_delivery_for_update(delivery_id, organization_id)
    if delivery is None:
      raise TraceException("Delivery not found.", status_code=404, code="DELIVERY_NOT_FOUND")
    req = await self.repo.get_by_id_for_update(delivery.request_id, organization_id)
    if req is None:
      raise TraceException(
        "Procurement request not found.", status_code=404, code="PROCUREMENT_REQUEST_NOT_FOUND",
      )
    if delivery.voided_at is not None:
      raise TraceException("This delivery is already voided.", status_code=409, code="DELIVERY_ALREADY_VOIDED")

    delivery.voided_at = datetime.now(timezone.utc)
    delivery.voided_by_user_id = actor_user_id
    delivery.void_reason = payload.reason.strip()
    await self.session.flush()

    balance = await self.stock.get_material_balance(organization_id, req.project_id, req.material_name)
    if balance < 0:
      raise TraceException(
        f"Voiding this delivery would leave {balance} {req.unit} of {req.material_name} in stock — "
        "more has already been issued than would remain received.",
        status_code=409, code="DELIVERY_VOID_BREAKS_STOCK",
      )

    remaining = await self.repo.get_delivered_quantity(req.id, organization_id)
    if req.status == ProcurementStatus.RECEIVED and remaining < req.quantity:
      req.status = ProcurementStatus.ORDERED
    await self.session.flush()
    await self.session.commit()
    return self._delivery_dict(delivery, req)

  async def list_deliveries(
    self,
    organization_id: UUID,
    *,
    request_id: UUID | None = None,
    project_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
  ) -> list[dict]:
    if project_id is not None:
      await self._ensure_project(organization_id, project_id)
    rows = await self.repo.list_deliveries(
      organization_id, request_id=request_id, project_id=project_id,
      date_from=date_from, date_to=date_to,
    )
    return [self._delivery_dict(delivery, req) for delivery, req in rows]

  @staticmethod
  def _delivery_dict(delivery: ProcurementDelivery, req: ProcurementRequest) -> dict:
    return {
      "id": delivery.id, "request_id": delivery.request_id, "project_id": delivery.project_id,
      "material_name": req.material_name, "unit": req.unit, "received_date": delivery.received_date,
      "quantity": delivery.quantity, "supplier_name": delivery.supplier_name,
      "invoice_number": delivery.invoice_number, "amount": delivery.amount, "notes": delivery.notes,
      "voided_at": delivery.voided_at, "void_reason": delivery.void_reason, "created_at": delivery.created_at,
    }

  async def _ensure_project(self, organization_id: UUID, project_id: UUID) -> None:
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException(
        "Project not found.", status_code=404, code="PROJECT_NOT_FOUND",
      )
  
  async def get_status_counts(
    self,
    organization_id: UUID,
    project_id: UUID | None = None,
  ) -> dict[ProcurementStatus, int]:
    if project_id is not None:
      await self._ensure_project(organization_id, project_id)
    return await self.repo.get_status_counts(organization_id, project_id)