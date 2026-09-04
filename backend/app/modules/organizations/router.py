from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permission
from app.modules.identity.enums import PermissionKey
from app.modules.identity.models import User
from app.modules.organizations.schemas import (AISettingsResponse, AISettingsUpdateRequest, InvitationAcceptRequest, InvitationAcceptanceResponse, InvitationCreateRequest, InvitationResponse,
  MemberResponse, MemberRoleUpdateRequest, MemberStatusUpdateRequest, OrganizationResponse, OrganizationUpdateRequest, PermissionResponse, RoleCreateRequest, RoleResponse, RoleUpdateRequest,
)
from app.modules.organizations.service import OrganizationService

router = APIRouter(
  prefix="/organizations",
  tags=["Organizations"],
)

def _service(session: AsyncSession) -> OrganizationService:
  return OrganizationService(session)

@router.get("/me", response_model=OrganizationResponse)
async def get_current_organization(
  current_user: User = Depends(
    require_permission(PermissionKey.ORGANIZATION_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.get_organization(current_user.organization_id)

@router.patch("/me", response_model=OrganizationResponse)
async def update_current_organization(
  payload: OrganizationUpdateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.ORGANIZATION_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.update_organization(
    current_user.organization_id, payload, actor_user_id=current_user.id
  )

@router.get("/me/ai-settings", response_model=AISettingsResponse)
async def get_ai_settings(
  current_user: User = Depends(
    require_permission(PermissionKey.ORGANIZATION_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  enabled = await service.get_ai_settings(current_user.organization_id)
  return AISettingsResponse(ai_enabled=enabled)

@router.patch("/me/ai-settings", response_model=AISettingsResponse)
async def update_ai_settings(
  payload: AISettingsUpdateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.ORGANIZATION_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  enabled = await service.update_ai_settings(
    current_user.organization_id, payload, actor_user_id=current_user.id
  )
  return AISettingsResponse(ai_enabled=enabled)

@router.get("/me/members", response_model=list[MemberResponse])
async def list_members(
  skip: int = Query(default=0, ge=0),
  limit: int = Query(default=100, ge=1, le=100),
  current_user: User = Depends(require_permission(PermissionKey.ORGANIZATION_READ)),
  session: AsyncSession = Depends(get_db),
):
  organization_id = current_user.active_membership.organization_id
  members, _total = await _service(session).list_members(organization_id, skip=skip, limit=limit)
  return [MemberResponse.from_user_and_role(u, r, organization_id, active) for u, r, active in members]

@router.get("/me/members/{user_id}", response_model=MemberResponse)
async def get_member(
  user_id: UUID,
  current_user: User = Depends(require_permission(PermissionKey.ORGANIZATION_READ)),
  session: AsyncSession = Depends(get_db),
):
  organization_id = current_user.active_membership.organization_id
  user, role, is_active = await _service(session).get_member(organization_id, user_id)
  return MemberResponse.from_user_and_role(user, role, organization_id, is_active)

@router.patch("/me/members/{user_id}/role", response_model=MemberResponse)
async def update_member_role(
  user_id: UUID, payload: MemberRoleUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.ORGANIZATION_MEMBERS_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  organization_id = current_user.active_membership.organization_id
  user, role, is_active = await _service(session).update_member_role(organization_id, user_id, payload, current_user.id)
  return MemberResponse.from_user_and_role(user, role, organization_id, is_active)

@router.patch("/me/members/{user_id}/status", response_model=MemberResponse)
async def update_member_status(
  user_id: UUID, payload: MemberStatusUpdateRequest,
  current_user: User = Depends(require_permission(PermissionKey.ORGANIZATION_MEMBERS_MANAGE)),
  session: AsyncSession = Depends(get_db),
):
  organization_id = current_user.active_membership.organization_id
  user, role, is_active = await _service(session).update_member_status(organization_id, user_id, payload, current_user.id)
  return MemberResponse.from_user_and_role(user, role, organization_id, is_active)

@router.get("/me/roles", response_model=list[RoleResponse])
async def list_roles(
  current_user: User = Depends(
    require_permission(PermissionKey.ORGANIZATION_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_roles(current_user.organization_id)

@router.get("/me/roles/{role_id}", response_model=RoleResponse)
async def get_role(
  role_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.ORGANIZATION_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.get_role(current_user.organization_id, role_id)

@router.post(
  "/me/roles",
  response_model=RoleResponse,
  status_code=status.HTTP_201_CREATED,
)
async def create_role(
  payload: RoleCreateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.ORGANIZATION_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.create_role(current_user.organization_id, payload, actor_user_id=current_user.id)

@router.patch("/me/roles/{role_id}", response_model=RoleResponse)
async def update_role(
  role_id: UUID,
  payload: RoleUpdateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.ORGANIZATION_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.update_role(
    current_user.organization_id, role_id, payload, actor_user_id=current_user.id
  )

@router.delete(
  "/me/roles/{role_id}",
  status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_role(
  role_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.ORGANIZATION_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  await service.delete_role(current_user.organization_id, role_id, actor_user_id=current_user.id)


@router.get("/me/permissions", response_model=list[PermissionResponse])
async def list_permissions(
  current_user: User = Depends(
    require_permission(PermissionKey.ORGANIZATION_READ)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.list_permissions()

@router.post(
  "/me/invitations",
  response_model=InvitationResponse,
  status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
  payload: InvitationCreateRequest,
  current_user: User = Depends(
    require_permission(PermissionKey.ORGANIZATION_MEMBERS_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.create_invitation(
    current_user.organization_id, current_user.id, payload
  )

@router.get("/me/invitations", response_model=list[InvitationResponse])
async def list_invitations(
  skip: int = Query(default=0, ge=0),
  limit: int = Query(default=100, ge=1, le=100),
  current_user: User = Depends(
    require_permission(PermissionKey.ORGANIZATION_MEMBERS_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  invitations, _total = await service.list_invitations(
    current_user.organization_id, skip=skip, limit=limit
  )
  return invitations

@router.delete(
  "/me/invitations/{invitation_id}",
  status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_invitation(
  invitation_id: UUID,
  current_user: User = Depends(
    require_permission(PermissionKey.ORGANIZATION_MEMBERS_MANAGE)
  ),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  await service.revoke_invitation(current_user.organization_id, invitation_id, actor_user_id=current_user.id)

@router.post(
  "/invitations/accept",
  response_model=InvitationAcceptanceResponse,
)
async def accept_invitation(
  payload: InvitationAcceptRequest,
  current_user: User = Depends(get_current_user),
  session: AsyncSession = Depends(get_db),
):
  service = _service(session)
  return await service.accept_invitation(payload, current_user)