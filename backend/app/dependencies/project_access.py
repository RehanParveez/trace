from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.identity.models import User
from uuid import UUID
from app.modules.identity.enums import PermissionKey
from app.modules.projects.models import Project, ProjectMember
from sqlalchemy import select
from app.core.exceptions import TraceException

async def accessible_project_ids(session: AsyncSession, user: User) -> set[UUID] | None:
  membership = user.active_membership
  if PermissionKey.PROJECT_VIEW_ALL in {p.key for p in membership.role.permissions}:
    return None
  rows = await session.execute(
    select(ProjectMember.project_id).join(Project, Project.id == ProjectMember.project_id).where(
      Project.organization_id == membership.organization_id, ProjectMember.user_id == user.id,
    )
  )
  return {row[0] for row in rows.all()}

async def ensure_project_access(session: AsyncSession, user: User, project_id: UUID) -> None:
  allowed = await accessible_project_ids(session, user)
  if allowed is not None and project_id not in allowed:
    raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")