from __future__ import annotations
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
from app.core.exceptions import TraceException
from app.modules.projects.models import ProjectStatus
from app.modules.projects.schemas import ProjectCreate, ProjectUpdate

@pytest.mark.asyncio
class TestProjectService:
  async def test_create_project_success_with_client_and_dates(
    self,
    project_service,
    organization,
    client_factory,
  ):
    client = await client_factory()
    start = date.today()
    end = start + timedelta(days=120)

    payload = ProjectCreate(
      name="Highway Expansion",
      code="HWY-2026",
      description="Major road project",
      location="North Corridor",
      client_id=client.id,
      start_date=start,
      expected_end_date=end,
    )

    with patch("app.modules.projects.service.SubscriptionService") as MockSub:
      mock_sub = MockSub.return_value
      mock_sub.check_quota = AsyncMock()
      mock_sub.increment_usage = AsyncMock()

      project = await project_service.create_project(organization.id, payload)

    assert project.organization_id == organization.id
    assert project.client_id == client.id
    assert project.name == "Highway Expansion"
    assert project.code == "HWY-2026"
    assert project.status == ProjectStatus.PLANNING
    assert project.start_date == start
    assert project.expected_end_date == end
    mock_sub.check_quota.assert_awaited_once_with(organization.id, "projects", 1)
    mock_sub.increment_usage.assert_awaited_once_with(organization.id, "projects", 1)

  async def test_create_project_client_must_belong_to_same_org(
    self,
    project_service,
    organization,
    client_factory,
    other_organization,
  ):
    foreign_client = await client_factory(organization_id=other_organization.id)

    payload = ProjectCreate(name="Bad Client Project", client_id=foreign_client.id)
    with pytest.raises(TraceException) as exc:
      await project_service.create_project(organization.id, payload)
    assert exc.value.code == "CLIENT_NOT_FOUND"

  async def test_create_project_code_uniqueness_case_insensitive(
    self,
    project_service,
    organization,
    project_factory,
  ):
    await project_factory(code="TRC-001")

    payload = ProjectCreate(name="Duplicate Code", code="trc-001")
    with pytest.raises(TraceException) as exc:
      await project_service.create_project(organization.id, payload)
    assert exc.value.code == "PROJECT_CODE_ALREADY_EXISTS"

  async def test_create_project_invalid_dates(
    self,
    project_service,
    organization,
  ):
    payload = ProjectCreate(
      name="Bad Dates",
      start_date=date(2026, 6, 1),
      expected_end_date=date(2026, 5, 1),
    )
    with pytest.raises(TraceException) as exc:
      await project_service.create_project(organization.id, payload)
    assert exc.value.status_code == 422
    assert exc.value.code == "INVALID_PROJECT_DATES"

  async def test_list_and_get_project_org_scoped(
    self,
    project_service,
    organization,
    project_factory,
    other_organization,
  ):
    p1 = await project_factory(name="Org Project 1")
    p2 = await project_factory(name="Org Project 2")
    await project_factory(organization_id=other_organization.id, name="Foreign")

    projects = await project_service.list_projects(organization.id)
    assert {p.id for p in projects} >= {p1.id, p2.id}
    assert all(p.organization_id == organization.id for p in projects)

    found = await project_service.get_project(organization.id, p1.id)
    assert found.id == p1.id

    with pytest.raises(TraceException) as exc:
      await project_service.get_project(organization.id, uuid4())
    assert exc.value.code == "PROJECT_NOT_FOUND"

  async def test_update_project_full_rules(
    self,
    project_service,
    organization,
    project_factory,
    client_factory,
  ):
    project = await project_factory(
      start_date=date(2026, 1, 1),
      expected_end_date=date(2026, 6, 1),
    )
    new_client = await client_factory()

    updated = await project_service.update_project(
      organization.id,
      project.id,
      ProjectUpdate(
        name="Updated Name",
        code="NEW-CODE",
        status=ProjectStatus.ACTIVE,
        client_id=new_client.id,
        actual_end_date=date(2026, 5, 15),
      ),
    )
    assert updated.name == "Updated Name"
    assert updated.code == "NEW-CODE"
    assert updated.status == ProjectStatus.ACTIVE
    assert updated.client_id == new_client.id
    assert updated.actual_end_date == date(2026, 5, 15)

    other = await project_factory(code="CONFLICT")
    with pytest.raises(TraceException) as exc:
      await project_service.update_project(
        organization.id, project.id, ProjectUpdate(code="CONFLICT")
      )
    assert exc.value.code == "PROJECT_CODE_ALREADY_EXISTS"

    with pytest.raises(TraceException) as exc:
      await project_service.update_project(
        organization.id,
        project.id,
        ProjectUpdate(expected_end_date=date(2025, 12, 1)),
      )
    assert exc.value.code == "INVALID_PROJECT_DATES"

    with pytest.raises(TraceException) as exc:
      await project_service.update_project(
        organization.id,
        project.id,
        ProjectUpdate(actual_end_date=date(2025, 12, 1)),
      )
    assert exc.value.code == "INVALID_PROJECT_DATES"

  async def test_delete_project_decrements_usage(
    self,
    project_service,
    organization,
    project_factory,
  ):
    project = await project_factory()

    with patch("app.modules.projects.service.SubscriptionService") as MockSub:
      mock_sub = MockSub.return_value
      mock_sub.decrement_usage = AsyncMock()

      await project_service.delete_project(organization.id, project.id)

      mock_sub.decrement_usage.assert_awaited_once_with(
        organization_id=organization.id,
        metric="projects",
        amount=1,
      )

    with pytest.raises(TraceException) as exc:
      await project_service.get_project(organization.id, project.id)
    assert exc.value.code == "PROJECT_NOT_FOUND"