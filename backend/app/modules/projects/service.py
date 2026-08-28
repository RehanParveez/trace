from __future__ import annotations
from uuid import UUID, uuid4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import TraceException
from app.modules.projects.models import Client, Milestone, Project, ProjectMember
from app.modules.projects.repository import ClientRepository, MilestoneRepository, ProjectMemberRepository, ProjectRepository
from app.modules.projects.schemas import ClientCreate, ClientUpdate, MilestoneCreate, MilestoneUpdate, ProjectCreate, ProjectMemberCreate, ProjectMemberUpdate, ProjectUpdate

class ProjectService:
  def __init__(
    self,
    session: AsyncSession,
  ):
    self.session = session
    self.clients = ClientRepository(session)
    self.projects = ProjectRepository(session)
    self.members = ProjectMemberRepository(session)
    self.milestones = MilestoneRepository(session)

  async def create_client(
    self,
    organization_id: UUID,
    payload: ClientCreate,
  ) -> Client:
    existing = await self.clients.get_by_name_and_org(
      payload.name,
      organization_id,
    )

    if existing is not None:
      raise TraceException(
        "A client with this name already exists.",
        status_code=409,
        code="CLIENT_ALREADY_EXISTS",
      )

    client = Client(
      id=uuid4(),
      organization_id=organization_id,
      name=payload.name,
      contact_name=payload.contact_name,
      email=payload.email,
      phone=payload.phone,
      address=payload.address,
      notes=payload.notes,
    )

    try:
      await self.clients.create(client)
      await self.session.commit()
    except IntegrityError as exc:
      await self.session.rollback()

      raise TraceException(
        "Unable to create client.",
        status_code=409,
        code="CLIENT_CREATE_CONFLICT",
      ) from exc

    return client

  async def list_clients(
    self,
    organization_id: UUID,
  ) -> list[Client]:
    return await self.clients.list_by_org(
      organization_id
    )

  async def get_client(
    self,
    organization_id: UUID,
    client_id: UUID,
  ) -> Client:
    client = await self.clients.get_by_id_and_org(
      client_id,
      organization_id,
    )

    if client is None:
      raise TraceException(
        "Client not found.",
        status_code=404,
        code="CLIENT_NOT_FOUND",
      )
    return client

  async def update_client(
    self,
    organization_id: UUID,
    client_id: UUID,
    payload: ClientUpdate,
  ) -> Client:
    client = await self.get_client(
      organization_id,
      client_id,
    )

    if payload.name is not None:
      existing = await self.clients.get_by_name_and_org(
        payload.name,
        organization_id,
      )

      if (
        existing is not None
        and existing.id != client.id
      ):
        raise TraceException(
          "A client with this name already exists.",
          status_code=409,
          code="CLIENT_ALREADY_EXISTS",
        )

      client.name = payload.name

    if payload.contact_name is not None:
      client.contact_name = payload.contact_name

    if payload.email is not None:
      client.email = payload.email

    if payload.phone is not None:
      client.phone = payload.phone

    if payload.address is not None:
      client.address = payload.address

    if payload.notes is not None:
      client.notes = payload.notes

    await self.session.flush()
    await self.session.commit()
    return client

  async def delete_client(
    self,
    organization_id: UUID,
    client_id: UUID,
  ) -> None:
    client = await self.get_client(
      organization_id,
      client_id,
    )

    await self.clients.delete(client)
    await self.session.commit()

  async def create_project(
    self,
    organization_id: UUID,
    payload: ProjectCreate,
  ) -> Project:
    if payload.client_id is not None:
      client = await self.clients.get_by_id_and_org(
        payload.client_id,
        organization_id,
      )

      if client is None:
        raise TraceException(
          "Client not found.",
          status_code=404,
          code="CLIENT_NOT_FOUND",
        )

    if payload.code is not None:
      existing = await self.projects.get_by_code_and_org(
        payload.code,
        organization_id,
      )

      if existing is not None:
        raise TraceException(
          "A project with this code already exists.",
          status_code=409,
          code="PROJECT_CODE_ALREADY_EXISTS",
        )

    if (
      payload.start_date is not None
      and payload.expected_end_date is not None
      and payload.expected_end_date < payload.start_date
    ):
      raise TraceException(
        "Expected end date cannot be before start date.",
        status_code=422,
        code="INVALID_PROJECT_DATES",
      )

    project = Project(
      id=uuid4(),
      organization_id=organization_id,
      client_id=payload.client_id,
      name=payload.name,
      code=payload.code,
      description=payload.description,
      location=payload.location,
      start_date=payload.start_date,
      expected_end_date=payload.expected_end_date,
    )

    try:
      await self.projects.create(project)
      await self.session.commit()
    except IntegrityError as exc:
      await self.session.rollback()

      raise TraceException(
        "Unable to create project.",
        status_code=409,
        code="PROJECT_CREATE_CONFLICT",
      ) from exc
    return project

  async def list_projects(
    self,
    organization_id: UUID,
  ) -> list[Project]:
    return await self.projects.list_by_org(
      organization_id
    )

  async def get_project(
    self,
    organization_id: UUID,
    project_id: UUID,
  ) -> Project:
    project = await self.projects.get_by_id_and_org(
      project_id,
      organization_id,
    )

    if project is None:
      raise TraceException(
        "Project not found.",
        status_code=404,
        code="PROJECT_NOT_FOUND",
      )

    return project

  async def update_project(
    self,
    organization_id: UUID,
    project_id: UUID,
    payload: ProjectUpdate,
  ) -> Project:
    project = await self.get_project(
      organization_id,
      project_id,
    )

    if payload.client_id is not None:
      client = await self.clients.get_by_id_and_org(
        payload.client_id,
        organization_id,
      )

      if client is None:
        raise TraceException(
          "Client not found.",
          status_code=404,
          code="CLIENT_NOT_FOUND",
        )

      project.client_id = payload.client_id

    if payload.name is not None:
      project.name = payload.name

    if payload.code is not None:
      existing = await self.projects.get_by_code_and_org(
        payload.code,
        organization_id,
      )

      if (
        existing is not None
        and existing.id != project.id
      ):
        raise TraceException(
          "A project with this code already exists.",
          status_code=409,
          code="PROJECT_CODE_ALREADY_EXISTS",
        )

      project.code = payload.code

    if payload.description is not None:
      project.description = payload.description

    if payload.location is not None:
      project.location = payload.location

    if payload.status is not None:
      project.status = payload.status

    if payload.start_date is not None:
      project.start_date = payload.start_date

    if payload.expected_end_date is not None:
      project.expected_end_date = payload.expected_end_date

    if payload.actual_end_date is not None:
      project.actual_end_date = payload.actual_end_date

    if (
      project.start_date is not None
      and project.expected_end_date is not None
      and project.expected_end_date < project.start_date
    ):
      raise TraceException(
        "Expected end date cannot be before start date.",
        status_code=422,
        code="INVALID_PROJECT_DATES",
      )

    await self.projects.update(project)
    await self.session.commit()
    return project

  async def delete_project(
    self,
    organization_id: UUID,
    project_id: UUID,
  ) -> None:
    project = await self.get_project(
      organization_id,
      project_id,
    )

    await self.projects.delete(project)
    await self.session.commit()

  async def add_member(
    self,
    organization_id: UUID,
    project_id: UUID,
    payload: ProjectMemberCreate,
  ) -> ProjectMember:
    await self.get_project(
      organization_id,
      project_id,
    )

    existing = await self.members.get_by_project_and_user(
      project_id,
      payload.user_id,
    )

    if existing is not None:
      raise TraceException(
        "User is already a member of this project.",
        status_code=409,
        code="PROJECT_MEMBER_ALREADY_EXISTS",
      )

    member = ProjectMember(
      id=uuid4(),
      project_id=project_id,
      user_id=payload.user_id,
      role=payload.role,
    )

    try:
      await self.members.create(member)
      await self.session.commit()
    except IntegrityError as exc:
      await self.session.rollback()

      raise TraceException(
        "Unable to add project member.",
        status_code=409,
        code="PROJECT_MEMBER_CREATE_CONFLICT",
      ) from exc

    return member

  async def list_members(
    self,
    organization_id: UUID,
    project_id: UUID,
  ) -> list[ProjectMember]:
    await self.get_project(
      organization_id,
      project_id,
    )

    return await self.members.list_by_project(
      project_id
    )

  async def update_member(
    self,
    organization_id: UUID,
    project_id: UUID,
    user_id: UUID,
    payload: ProjectMemberUpdate,
  ) -> ProjectMember:
    await self.get_project(
      organization_id,
      project_id,
    )

    member = await self.members.get_by_project_and_user(
      project_id,
      user_id,
    )

    if member is None:
      raise TraceException(
        "Project member not found.",
        status_code=404,
        code="PROJECT_MEMBER_NOT_FOUND",
      )

    member.role = payload.role
    await self.session.flush()
    await self.session.commit()
    return member

  async def remove_member(
    self,
    organization_id: UUID,
    project_id: UUID,
    user_id: UUID,
  ) -> None:
    await self.get_project(
      organization_id,
      project_id,
    )

    member = await self.members.get_by_project_and_user(
      project_id,
      user_id,
    )

    if member is None:
      raise TraceException(
        "Project member not found.",
        status_code=404,
        code="PROJECT_MEMBER_NOT_FOUND",
      )
    await self.members.delete(member)
    await self.session.commit()

  async def create_milestone(
    self,
    organization_id: UUID,
    project_id: UUID,
    payload: MilestoneCreate,
  ) -> Milestone:
    await self.get_project(
      organization_id,
      project_id,
    )

    milestone = Milestone(
      id=uuid4(),
      project_id=project_id,
      name=payload.name,
      description=payload.description,
      due_date=payload.due_date,
    )

    await self.milestones.create(milestone)
    await self.session.commit()
    return milestone

  async def list_milestones(
    self,
    organization_id: UUID,
    project_id: UUID,
  ) -> list[Milestone]:
    await self.get_project(
      organization_id,
      project_id,
    )

    return await self.milestones.list_by_project(
      project_id
    )

  async def update_milestone(
    self,
    organization_id: UUID,
    project_id: UUID,
    milestone_id: UUID,
    payload: MilestoneUpdate,
  ) -> Milestone:
    await self.get_project(
      organization_id,
      project_id,
    )

    milestone = await self.milestones.get_by_id_and_project(
      milestone_id,
      project_id,
    )

    if milestone is None:
      raise TraceException(
        "Milestone not found.",
        status_code=404,
        code="MILESTONE_NOT_FOUND",
      )

    if payload.name is not None:
      milestone.name = payload.name

    if payload.description is not None:
      milestone.description = payload.description

    if payload.due_date is not None:
      milestone.due_date = payload.due_date

    if payload.completed_at is not None:
      milestone.completed_at = payload.completed_at

    await self.milestones.update(milestone)
    await self.session.commit()
    return milestone

  async def delete_milestone(
    self,
    organization_id: UUID,
    project_id: UUID,
    milestone_id: UUID,
  ) -> None:
    await self.get_project(
      organization_id,
      project_id,
    )

    milestone = await self.milestones.get_by_id_and_project(
      milestone_id,
      project_id,
    )

    if milestone is None:
      raise TraceException(
        "Milestone not found.",
        status_code=404,
        code="MILESTONE_NOT_FOUND",
      )

    await self.milestones.delete(milestone)
    await self.session.commit()