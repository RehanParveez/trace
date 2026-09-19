from __future__ import annotations
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
from app.core.exceptions import TraceException
from app.modules.projects.models import ProjectMemberRole
from app.modules.projects.schemas import ProjectMemberCreate, ProjectMemberUpdate

@pytest.mark.asyncio
class TestProjectMemberService:
  async def test_add_member_success(
    self,
    project_service,
    organization,
    project_factory,
    user,
  ):
    project = await project_factory()
    payload = ProjectMemberCreate(user_id=user.id, role=ProjectMemberRole.ENGINEER)
    member = await project_service.add_member(organization.id, project.id, payload)

    assert member.project_id == project.id
    assert member.user_id == user.id
    assert member.role == ProjectMemberRole.ENGINEER
    assert member.user is not None

  async def test_add_member_user_must_belong_to_organization(
    self,
    project_service,
    organization,
    project_factory,
  ):
    project = await project_factory()
    foreign_user_id = uuid4()

    with patch("app.modules.projects.service.IdentityRepository") as MockRepo:
      MockRepo.return_value.get_membership = AsyncMock(return_value=None)

      with pytest.raises(TraceException) as exc:
        await project_service.add_member(
          organization.id,
          project.id,
          ProjectMemberCreate(user_id=foreign_user_id),
        )
      assert exc.value.code == "USER_NOT_IN_ORGANIZATION"

  async def test_add_member_duplicate_rejected(
    self,
    project_service,
    organization,
    project_factory,
    user,
    member_factory,
  ):
    project = await project_factory()
    await member_factory(project=project, target_user=user)

    with pytest.raises(TraceException) as exc:
      await project_service.add_member(
        organization.id,
        project.id,
        ProjectMemberCreate(user_id=user.id),
      )
    assert exc.value.code == "PROJECT_MEMBER_ALREADY_EXISTS"

  async def test_list_update_remove_member(
    self,
    project_service,
    organization,
    project_factory,
    user,
    member_factory,
  ):
    project = await project_factory()
    member = await member_factory(
      project=project,
      target_user=user,
      role=ProjectMemberRole.MEMBER,
    )

    members = await project_service.list_members(organization.id, project.id)
    assert len(members) >= 1
    assert any(m.user_id == user.id for m in members)

    updated = await project_service.update_member(
      organization.id,
      project.id,
      user.id,
      ProjectMemberUpdate(role=ProjectMemberRole.SITE_MANAGER),
    )
    assert updated.role == ProjectMemberRole.SITE_MANAGER

    await project_service.remove_member(organization.id, project.id, user.id)

    with pytest.raises(TraceException) as exc:
      await project_service.update_member(
        organization.id,
        project.id,
        user.id,
        ProjectMemberUpdate(role=ProjectMemberRole.MEMBER),
      )
    assert exc.value.code == "PROJECT_MEMBER_NOT_FOUND"