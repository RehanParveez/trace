from __future__ import annotations
from datetime import date, timedelta
import pytest
from app.core.exceptions import TraceException
from app.modules.projects.schemas import MilestoneCreate, MilestoneUpdate

@pytest.mark.asyncio
class TestMilestoneService:
  async def test_create_list_update_delete_milestone(
    self,
    project_service,
    organization,
    project_factory,
  ):
    project = await project_factory()

    payload = MilestoneCreate(
      name="Foundation Complete",
      description="All foundation work done",
      due_date=date.today() + timedelta(days=45),
    )
    ms = await project_service.create_milestone(organization.id, project.id, payload)
    assert ms.project_id == project.id
    assert ms.name == "Foundation Complete"
    assert ms.completed_at is None

    milestones = await project_service.list_milestones(organization.id, project.id)
    assert any(m.id == ms.id for m in milestones)

    updated = await project_service.update_milestone(
      organization.id,
      project.id,
      ms.id,
      MilestoneUpdate(
        name="Foundation Complete (Revised)",
        completed_at=date.today(),
      ),
    )
    assert updated.name == "Foundation Complete (Revised)"
    assert updated.completed_at == date.today()

    await project_service.delete_milestone(organization.id, project.id, ms.id)

    with pytest.raises(TraceException) as exc:
      await project_service.update_milestone(
        organization.id,
        project.id,
        ms.id,
        MilestoneUpdate(name="Ghost"),
      )
    assert exc.value.code == "MILESTONE_NOT_FOUND"

  async def test_milestone_summary_correct_counts(
    self,
    project_service,
    organization,
    project_factory,
    milestone_factory,
  ):
    p1 = await project_factory()
    p2 = await project_factory()

    await milestone_factory(project=p1, completed_at=date.today())
    await milestone_factory(project=p1, completed_at=date.today())
    await milestone_factory(project=p1)
    await milestone_factory(project=p2)

    summary = await project_service.get_milestone_summary(organization.id)
    by_project = {s["project_id"]: s for s in summary}

    assert by_project[p1.id]["milestone_total"] == 3
    assert by_project[p1.id]["milestone_completed"] == 2
    assert by_project[p2.id]["milestone_total"] == 1
    assert by_project[p2.id]["milestone_completed"] == 0