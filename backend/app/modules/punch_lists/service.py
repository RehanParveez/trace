from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.punch_lists.repository import PunchListRepository
from app.modules.projects.repository import ProjectRepository
from app.modules.audit.service import AuditLogService
from app.modules.audit.models import AuditAction, AuditEntityType
from app.modules.punch_lists.models import PunchList, PunchListItem, PunchListItemPhoto, PunchListItemStatus, PunchListStatus
from uuid import UUID, uuid4
from app.modules.punch_lists.schemas import PunchListCreateRequest, PunchListItemCreateRequest, PunchListItemPhotoCreateRequest, PunchListItemUpdateRequest
from app.core.exceptions import TraceException
from datetime import datetime, timezone

class PunchListService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = PunchListRepository(session)
    self.projects = ProjectRepository(session)
    self.audit = AuditLogService(session)

  async def create_punch_list(
    self, organization_id: UUID, payload: PunchListCreateRequest, actor_user_id: UUID,
  ) -> PunchList:
    project = await self._require_project(organization_id, payload.project_id)
    punch_list = PunchList(
      id=uuid4(), organization_id=organization_id, project_id=payload.project_id,
      title=payload.title.strip(), inspection_date=payload.inspection_date, notes=payload.notes,
      created_by_user_id=actor_user_id,
    )
    await self.repo.create(punch_list)
    await self.session.commit()
    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.PUNCH_LIST, punch_list.id, AuditAction.CREATE,
      f'Created punch list "{punch_list.title}" for {project.name}.',
    )
    return punch_list

  async def add_item(
    self, organization_id: UUID, punch_list_id: UUID, payload: PunchListItemCreateRequest, actor_user_id: UUID,
  ) -> PunchListItem:
    punch_list = await self.repo.get_by_id(punch_list_id, organization_id)
    if punch_list is None:
      raise TraceException("Punch list not found.", status_code=404, code="PUNCH_LIST_NOT_FOUND")
    if punch_list.status == PunchListStatus.CLOSED:
      raise TraceException(
        "This punch list is closed. Create a new inspection round to add items.",
        status_code=409, code="PUNCH_LIST_CLOSED",
      )

    item = PunchListItem(
      id=uuid4(),
      organization_id=organization_id,
      punch_list_id=punch_list_id,
      location=payload.location.strip(),
      description=payload.description.strip(),
      assigned_to_user_id=payload.assigned_to_user_id,
      assigned_to_subcontractor_id=payload.assigned_to_subcontractor_id,
      due_date=payload.due_date,
      created_by_user_id=actor_user_id,
    )
    await self.repo.create_item(item)
    await self.session.commit()

    return await self.repo.get_item(item.id, organization_id)

  async def update_item(
    self, organization_id: UUID, item_id: UUID, payload: PunchListItemUpdateRequest, actor_user_id: UUID,
  ) -> PunchListItem:
    item = await self.repo.get_item(item_id, organization_id)
    if item is None:
        raise TraceException("Punch list item not found.", status_code=404, code="PUNCH_LIST_ITEM_NOT_FOUND")

    was_open = item.status in (PunchListItemStatus.OPEN, PunchListItemStatus.IN_PROGRESS)

    for field_name in (
        "location", "description", "assigned_to_user_id", "assigned_to_subcontractor_id",
        "status", "due_date", "resolution_notes",
    ):
        value = getattr(payload, field_name)
        if value is not None:
            setattr(item, field_name, value.strip() if isinstance(value, str) else value)

    if item.status in (PunchListItemStatus.RESOLVED, PunchListItemStatus.WAIVED) and item.resolved_at is None:
        item.resolved_at = datetime.now(timezone.utc)
    elif item.status in (PunchListItemStatus.OPEN, PunchListItemStatus.IN_PROGRESS):
        item.resolved_at = None

    await self.session.commit()

    if was_open and item.status in (PunchListItemStatus.RESOLVED, PunchListItemStatus.WAIVED):
        await self.audit.log(
            organization_id, actor_user_id, AuditEntityType.PUNCH_LIST, item.id, AuditAction.UPDATE,
            f'Closed punch list item "{item.description[:80]}".',
        )

    return await self.repo.get_item(item.id, organization_id)

  async def close_punch_list(self, organization_id: UUID, punch_list_id: UUID, actor_user_id: UUID) -> PunchList:
    punch_list = await self.repo.get_by_id(punch_list_id, organization_id)
    if punch_list is None:
      raise TraceException("Punch list not found.", status_code=404, code="PUNCH_LIST_NOT_FOUND")

    open_items = [
      i for i in punch_list.items if i.status in (PunchListItemStatus.OPEN, PunchListItemStatus.IN_PROGRESS)
    ]
    if open_items:
      raise TraceException(
        f"Cannot close this punch list — {len(open_items)} item(s) are still open or in progress.",
        status_code=409, code="PUNCH_LIST_HAS_OPEN_ITEMS",
      )

    punch_list.status = PunchListStatus.CLOSED
    punch_list.closed_at = datetime.now(timezone.utc)
    await self.session.commit()

    await self.audit.log(
      organization_id, actor_user_id, AuditEntityType.PUNCH_LIST, punch_list.id, AuditAction.UPDATE,
      f'Closed punch list "{punch_list.title}" — every item resolved or waived.',
    )
    return punch_list

  async def add_photo(
    self, organization_id: UUID, item_id: UUID, payload: PunchListItemPhotoCreateRequest,
  ) -> PunchListItemPhoto:
    item = await self.repo.get_item(item_id, organization_id)
    if item is None:
      raise TraceException("Punch list item not found.", status_code=404, code="PUNCH_LIST_ITEM_NOT_FOUND")
    photo = PunchListItemPhoto(
      id=uuid4(), organization_id=organization_id, punch_list_item_id=item_id,
      site_photo_id=payload.site_photo_id, photo_purpose=payload.photo_purpose,
    )
    await self.repo.create_photo_link(photo)
    await self.session.commit()
    return photo

  async def remove_photo(self, organization_id: UUID, link_id: UUID) -> None:
    link = await self.repo.get_photo_link(link_id, organization_id)
    if link is None:
      raise TraceException("Photo link not found.", status_code=404, code="PUNCH_LIST_PHOTO_NOT_FOUND")
    await self.repo.delete_photo_link(link)
    await self.session.commit()

  async def get_punch_list(self, organization_id: UUID, punch_list_id: UUID) -> PunchList:
    punch_list = await self.repo.get_by_id(punch_list_id, organization_id)
    if punch_list is None:
      raise TraceException("Punch list not found.", status_code=404, code="PUNCH_LIST_NOT_FOUND")
    return punch_list

  async def list_punch_lists(self, organization_id: UUID, project_id: UUID) -> list[PunchList]:
    await self._require_project(organization_id, project_id)
    return await self.repo.list_by_project(organization_id, project_id)

  async def get_project_summary(self, organization_id: UUID, project_id: UUID) -> dict:
    await self._require_project(organization_id, project_id)
    open_lists, open_items = await self.repo.get_open_lists_and_items_count(organization_id, project_id)
    total_lists = await self.repo.get_total_lists_count(organization_id, project_id)
    return {
      "project_id": project_id, "open_lists_count": open_lists, "total_open_items": open_items,
      "is_project_clear": total_lists > 0 and open_lists == 0,
    }

  async def assert_project_clear_for_final_release(self, organization_id: UUID, project_id: UUID) -> None:
    total_lists = await self.repo.get_total_lists_count(organization_id, project_id)
    if total_lists == 0:
      raise TraceException(
        "A final retention release requires at least one closed punch list for this project. "
        "Create and close one first.",
        status_code=409, code="PUNCH_LIST_REQUIRED_FOR_FINAL_RELEASE",
      )
    open_lists, open_items = await self.repo.get_open_lists_and_items_count(organization_id, project_id)
    if open_lists > 0 or open_items > 0:
      raise TraceException(
        f"Cannot record a final retention release — this project has {open_lists} open punch list(s) "
        f"and {open_items} unresolved item(s).",
        status_code=409, code="PUNCH_LIST_NOT_CLEAR",
      )

  async def assert_subcontractor_clear_for_final_release(
    self, organization_id: UUID, project_id: UUID, subcontractor_id: UUID,
  ) -> None:
    open_count = await self.repo.get_subcontractor_open_items_count(organization_id, project_id, subcontractor_id)
    if open_count > 0:
      raise TraceException(
        f"Cannot record a final retention release to this subcontractor — {open_count} punch list "
        f"item(s) assigned to them are still open or in progress.",
        status_code=409, code="PUNCH_LIST_NOT_CLEAR",
      )

  async def _require_project(self, organization_id: UUID, project_id: UUID):
    project = await self.projects.get_by_id_and_org(project_id, organization_id)
    if project is None:
      raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")
    return project