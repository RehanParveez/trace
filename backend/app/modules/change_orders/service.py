from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.change_orders.repository import ChangeOrderRepository
from app.modules.projects.repository import ProjectRepository
from app.modules.audit.service import AuditLogService
from uuid import UUID, uuid4
from app.modules.change_orders.schemas import ChangeOrderCreateRequest
from app.modules.change_orders.models import ChangeOrderLineItem, ChangeOrder, ChangeOrderStatus
from app.modules.drawings_boq.models import BOQItem, BOQItemRateSource, BOQItemStatus, BOQItemType, BOQVersion
from app.modules.identity.models import Organization
from app.modules.audit.models import  AuditEntityType, AuditAction
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from app.core.exceptions import TraceException
from sqlalchemy import select

class ChangeOrderService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = ChangeOrderRepository(session)
    self.projects = ProjectRepository(session)
    self.audit = AuditLogService(session)

  async def create_change_order(
    self, organization_id: UUID, payload: ChangeOrderCreateRequest, actor_user_id: UUID,
  ) -> ChangeOrder:
    project = await self._require_project(organization_id, payload.project_id)
    await self._require_boq_version(organization_id, payload.project_id, payload.boq_version_id)

    estimated_total = Decimal("0")
    line_items: list[ChangeOrderLineItem] = []

    for index, line in enumerate(payload.line_items):
      if line.boq_item_id is None:
        line_estimate = line.quantity * line.unit_rate
      else:
        existing_item = await self.repo.get_boq_item(line.boq_item_id, organization_id, payload.boq_version_id)
        if existing_item is None:
          raise TraceException(
            f"Line {index + 1}: the referenced BOQ item doesn't belong to this BOQ version.",
            status_code=404, code="BOQ_ITEM_NOT_FOUND",
          )
        applicable_rate = line.unit_rate if line.unit_rate is not None else existing_item.unit_rate
        line_estimate = line.quantity * (applicable_rate or Decimal("0"))

      estimated_total += line_estimate
      line_items.append(
        ChangeOrderLineItem(
          id=uuid4(), organization_id=organization_id, sort_order=index,
          description=line.description.strip(), unit=line.unit.strip(),
          boq_item_id=line.boq_item_id, quantity=line.quantity, unit_rate=line.unit_rate,
        )
      )

    organization = await self.session.get(Organization, organization_id)

    change_order: ChangeOrder | None = None
    for _attempt in range(3):
      number = await self.repo.get_max_number(organization_id, payload.project_id) + 1
      candidate = ChangeOrder(
        id=uuid4(), organization_id=organization_id, project_id=payload.project_id,
        boq_version_id=payload.boq_version_id, change_order_number=number, change_type=payload.change_type,
        status=ChangeOrderStatus.DRAFT, title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        client_reference=payload.client_reference, value_impact=estimated_total,
        currency=organization.currency if organization else "PKR", requested_by_user_id=actor_user_id,
      )
      try:
        await self.repo.create(candidate)
        for line in line_items:
          line.change_order_id = candidate.id
        await self.repo.create_line_items(line_items)
        await self.session.commit()
        change_order = candidate
        break
      except IntegrityError:
        await self.session.rollback()
        continue

    if change_order is None:
      raise TraceException(
        "Unable to create this change order right now due to a numbering conflict. Please try again.",
        status_code=409, code="CHANGE_ORDER_NUMBER_CONFLICT",
      )

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.CHANGE_ORDER, change_order.id, AuditAction.CREATE,
      f"Drafted change order #{change_order.change_order_number} for {project.name}, "
      f"estimated impact {estimated_total} {change_order.currency}.",
    )
    return await self.get_change_order(organization_id, change_order.id)

  async def approve_change_order(
    self, organization_id: UUID, change_order_id: UUID, expected_version: int, actor_user_id: UUID,
  ) -> ChangeOrder:
    change_order = await self.repo.get_by_id_for_update(change_order_id, organization_id)
    if change_order is None:
      raise TraceException("Change order not found.", status_code=404, code="CHANGE_ORDER_NOT_FOUND")
    if change_order.version != expected_version:
      raise TraceException(
        "This change order was changed by someone else. Reload and try again.",
        status_code=409, code="CHANGE_ORDER_VERSION_CONFLICT",
      )
    if change_order.status != ChangeOrderStatus.DRAFT:
      raise TraceException(
        "Only draft change orders can be approved.", status_code=409, code="CHANGE_ORDER_NOT_DRAFT",
      )

    realized_total = Decimal("0")

    for line in change_order.line_items:
      if line.boq_item_id is None:
        new_item = BOQItem(
          id=uuid4(), organization_id=organization_id, boq_version_id=change_order.boq_version_id,
          drawing_element_id=None, material_name=line.description, category=None, unit=line.unit,
          quantity=line.quantity, unit_rate=line.unit_rate, rate_source=BOQItemRateSource.LIBRARY if line.unit_rate else None,
          item_type=BOQItemType.CUSTOM, status=BOQItemStatus.APPROVED, created_by_user_id=actor_user_id,
        )
        await self.repo.create_boq_item(new_item)
        line.created_boq_item_id = new_item.id
        line_value = line.quantity * line.unit_rate
      else:
        existing_item = await self.repo.get_boq_item(line.boq_item_id, organization_id, change_order.boq_version_id)
        if existing_item is None:
          raise TraceException(
            f"The BOQ item referenced by line '{line.description}' no longer exists.",
            status_code=404, code="BOQ_ITEM_NOT_FOUND",
          )
        original_rate = existing_item.unit_rate
        new_quantity = existing_item.quantity + line.quantity
        if new_quantity < 0:
          raise TraceException(
            f"Approving this change order would reduce '{existing_item.material_name}' below zero quantity.",
            status_code=409, code="CHANGE_ORDER_QUANTITY_UNDERFLOW",
          )
        existing_item.quantity = new_quantity
        if line.unit_rate is not None:
          existing_item.unit_rate = line.unit_rate
        applicable_rate = line.unit_rate if line.unit_rate is not None else original_rate
        line_value = line.quantity * (applicable_rate or Decimal("0"))

      line.realized_value_impact = line_value
      realized_total += line_value

    change_order.status = ChangeOrderStatus.APPROVED
    change_order.approved_by_user_id = actor_user_id
    change_order.approved_at = datetime.now(timezone.utc)
    change_order.value_impact = realized_total
    change_order.version += 1

    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.CHANGE_ORDER, change_order.id, AuditAction.UPDATE,
      f"Approved change order #{change_order.change_order_number}, applied impact {realized_total} {change_order.currency}.",
    )
    return change_order

  async def reject_change_order(
    self, organization_id: UUID, change_order_id: UUID, expected_version: int, reason: str, actor_user_id: UUID,
  ) -> ChangeOrder:
    change_order = await self.repo.get_by_id_for_update(change_order_id, organization_id)
    if change_order is None:
      raise TraceException("Change order not found.", status_code=404, code="CHANGE_ORDER_NOT_FOUND")
    if change_order.version != expected_version:
      raise TraceException(
        "This change order was changed by someone else. Reload and try again.",
        status_code=409, code="CHANGE_ORDER_VERSION_CONFLICT",
      )
    if change_order.status != ChangeOrderStatus.DRAFT:
      raise TraceException(
        "Only draft change orders can be rejected.", status_code=409, code="CHANGE_ORDER_NOT_DRAFT",
      )

    change_order.status = ChangeOrderStatus.REJECTED
    change_order.rejected_at = datetime.now(timezone.utc)
    change_order.rejection_reason = reason.strip()
    change_order.version += 1
    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.CHANGE_ORDER, change_order.id, AuditAction.UPDATE,
      f"Rejected change order #{change_order.change_order_number}: {reason}",
    )
    return change_order

  async def cancel_change_order(
    self, organization_id: UUID, change_order_id: UUID, expected_version: int, actor_user_id: UUID,
  ) -> ChangeOrder:
    change_order = await self.repo.get_by_id_for_update(change_order_id, organization_id)
    if change_order is None:
      raise TraceException("Change order not found.", status_code=404, code="CHANGE_ORDER_NOT_FOUND")
    if change_order.version != expected_version:
      raise TraceException(
        "This change order was changed by someone else. Reload and try again.",
        status_code=409, code="CHANGE_ORDER_VERSION_CONFLICT",
      )
    if change_order.status != ChangeOrderStatus.DRAFT:
      raise TraceException(
        "Only draft change orders can be cancelled.", status_code=409, code="CHANGE_ORDER_NOT_DRAFT",
      )

    change_order.status = ChangeOrderStatus.CANCELLED
    change_order.version += 1
    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.CHANGE_ORDER, change_order.id, AuditAction.UPDATE,
      f"Cancelled change order #{change_order.change_order_number}.",
    )
    return change_order

  async def get_change_order(self, organization_id: UUID, change_order_id: UUID) -> ChangeOrder:
    change_order = await self.repo.get_by_id(change_order_id, organization_id)
    if change_order is None:
      raise TraceException("Change order not found.", status_code=404, code="CHANGE_ORDER_NOT_FOUND")
    return change_order

  async def list_change_orders(self, organization_id: UUID, project_id: UUID) -> list[ChangeOrder]:
    await self._require_project(organization_id, project_id)
    return await self.repo.list_by_project(organization_id, project_id)

  async def get_project_summary(self, organization_id: UUID, project_id: UUID) -> dict:
    await self._require_project(organization_id, project_id)
    approved_count, approved_total, draft_count = await self.repo.get_approval_summary(organization_id, project_id)
    organization = await self.session.get(Organization, organization_id)
    return {
      "project_id": project_id, "approved_count": approved_count,
      "approved_net_value_impact": Decimal(str(approved_total)), "draft_count": draft_count,
      "currency": organization.currency if organization else "PKR",
    }

  async def _require_project(self, organization_id: UUID, project_id: UUID):
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
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