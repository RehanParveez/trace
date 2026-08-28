from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.permissions import require_permission
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.projects.schemas import (ClientCreate, ClientResponse, ClientUpdate, MilestoneCreate, MilestoneResponse, MilestoneUpdate, ProjectCreate, ProjectMemberCreate, ProjectMemberResponse,
  ProjectMemberUpdate, ProjectResponse, ProjectUpdate,
)
from app.modules.projects.service import ProjectService

router = APIRouter(
  prefix="/projects",
  tags=["Projects"],
)

def _service(
  session: AsyncSession,
) -> ProjectService:
  return ProjectService(session)

@router.post(
  "/clients",
  response_model=ClientResponse,
)
async def create_client(
  payload: ClientCreate,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_CREATE
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.create_client(
    current_user.organization_id,
    payload,
  )

@router.get(
  "/clients",
  response_model=list[ClientResponse],
)
async def list_clients(
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_READ
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.list_clients(
    current_user.organization_id,
  )

@router.get(
  "/clients/{client_id}",
  response_model=ClientResponse,
)
async def get_client(
  client_id: UUID,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_READ
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.get_client(
    current_user.organization_id,
    client_id,
  )

@router.patch(
  "/clients/{client_id}",
  response_model=ClientResponse,
)
async def update_client(
  client_id: UUID,
  payload: ClientUpdate,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_UPDATE
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.update_client(
    current_user.organization_id,
    client_id,
    payload,
  )

@router.delete(
  "/clients/{client_id}",
  status_code=204,
)
async def delete_client(
  client_id: UUID,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_DELETE
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  await service.delete_client(
    current_user.organization_id,
    client_id,
  )

@router.post(
  "",
  response_model=ProjectResponse,
)
async def create_project(
  payload: ProjectCreate,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_CREATE
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.create_project(
    current_user.organization_id,
    payload,
  )

@router.get(
  "",
  response_model=list[ProjectResponse],
)
async def list_projects(
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_READ
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.list_projects(
    current_user.organization_id,
  )

@router.get(
  "/{project_id}",
  response_model=ProjectResponse,
)
async def get_project(
  project_id: UUID,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_READ
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.get_project(
    current_user.organization_id,
    project_id,
  )

@router.patch(
  "/{project_id}",
  response_model=ProjectResponse,
)
async def update_project(
  project_id: UUID,
  payload: ProjectUpdate,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_UPDATE
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.update_project(
    current_user.organization_id,
    project_id,
    payload,
  )

@router.delete(
  "/{project_id}",
  status_code=204,
)
async def delete_project(
  project_id: UUID,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_DELETE
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  await service.delete_project(
    current_user.organization_id,
    project_id,
  )

@router.post(
  "/{project_id}/members",
  response_model=ProjectMemberResponse,
)
async def add_project_member(
  project_id: UUID,
  payload: ProjectMemberCreate,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_UPDATE
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.add_member(
    current_user.organization_id,
    project_id,
    payload,
  )

@router.get(
  "/{project_id}/members",
  response_model=list[ProjectMemberResponse],
)
async def list_project_members(
  project_id: UUID,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_READ
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.list_members(
    current_user.organization_id,
    project_id,
  )

@router.patch(
  "/{project_id}/members/{user_id}",
  response_model=ProjectMemberResponse,
)
async def update_project_member(
  project_id: UUID,
  user_id: UUID,
  payload: ProjectMemberUpdate,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_UPDATE
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.update_member(
    current_user.organization_id,
    project_id,
    user_id,
    payload,
  )

@router.delete(
  "/{project_id}/members/{user_id}",
  status_code=204,
)
async def remove_project_member(
  project_id: UUID,
  user_id: UUID,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_UPDATE
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  await service.remove_member(
    current_user.organization_id,
    project_id,
    user_id,
  )

@router.post(
  "/{project_id}/milestones",
  response_model=MilestoneResponse,
)
async def create_milestone(
  project_id: UUID,
  payload: MilestoneCreate,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_UPDATE
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.create_milestone(
    current_user.organization_id,
    project_id,
    payload,
  )

@router.get(
  "/{project_id}/milestones",
  response_model=list[MilestoneResponse],
)
async def list_milestones(
  project_id: UUID,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_READ
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.list_milestones(
    current_user.organization_id,
    project_id,
  )

@router.patch(
  "/{project_id}/milestones/{milestone_id}",
  response_model=MilestoneResponse,
)
async def update_milestone(
  project_id: UUID,
  milestone_id: UUID,
  payload: MilestoneUpdate,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_UPDATE
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  return await service.update_milestone(
    current_user.organization_id,
    project_id,
    milestone_id,
    payload,
  )

@router.delete(
  "/{project_id}/milestones/{milestone_id}",
  status_code=204,
)
async def delete_milestone(
  project_id: UUID,
  milestone_id: UUID,
  current_user: User = Depends(
    require_permission(
      PermissionKey.PROJECT_UPDATE
    )
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)

  await service.delete_milestone(
    current_user.organization_id,
    project_id,
    milestone_id,
  )