from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.projects.models import Client, Milestone, Project, ProjectMember

class ClientRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(
    self,
    client: Client,
  ) -> Client:
    self.session.add(client)
    await self.session.flush()
    return client

  async def get_by_id_and_org(
    self,
    client_id: UUID,
    organization_id: UUID,
  ) -> Client | None:
    result = await self.session.execute(
      select(Client).where(
        Client.id == client_id,
        Client.organization_id == organization_id,
      )
    )

    return result.scalar_one_or_none()

  async def get_by_name_and_org(
    self,
    name: str,
    organization_id: UUID,
  ) -> Client | None:
    result = await self.session.execute(
      select(Client).where(
        Client.organization_id == organization_id,
        Client.name == name,
      )
    )

    return result.scalar_one_or_none()

  async def list_by_org(
    self,
    organization_id: UUID,
  ) -> list[Client]:
    result = await self.session.execute(
      select(Client)
      .where(
        Client.organization_id == organization_id,
      )
      .order_by(Client.name.asc())
    )

    return list(result.scalars().all())

  async def delete(
    self,
    client: Client,
  ) -> None:
    await self.session.delete(client)
    await self.session.flush()

class ProjectRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(
    self,
    project: Project,
  ) -> Project:
    self.session.add(project)
    await self.session.flush()
    return project

  async def get_by_id_and_org(
    self,
    project_id: UUID,
    organization_id: UUID,
  ) -> Project | None:
    result = await self.session.execute(
      select(Project).where(
        Project.id == project_id,
        Project.organization_id == organization_id,
      )
    )

    return result.scalar_one_or_none()

  async def get_by_code_and_org(
    self,
    code: str,
    organization_id: UUID,
  ) -> Project | None:
    result = await self.session.execute(
      select(Project).where(
        Project.organization_id == organization_id,
        Project.code == code,
      )
    )

    return result.scalar_one_or_none()

  async def list_by_org(
    self,
    organization_id: UUID,
  ) -> list[Project]:
    result = await self.session.execute(
      select(Project)
      .where(
        Project.organization_id == organization_id,
      )
      .order_by(Project.created_at.desc())
    )

    return list(result.scalars().all())

  async def update(
    self,
    project: Project,
  ) -> Project:
    self.session.add(project)
    await self.session.flush()
    return project

  async def delete(
    self,
    project: Project,
  ) -> None:
    await self.session.delete(project)
    await self.session.flush()

class ProjectMemberRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(
    self,
    member: ProjectMember,
  ) -> ProjectMember:
    self.session.add(member)
    await self.session.flush()
    return member

  async def get_by_id(
    self,
    member_id: UUID,
  ) -> ProjectMember | None:
    result = await self.session.execute(
      select(ProjectMember).where(
        ProjectMember.id == member_id,
      )
    )

    return result.scalar_one_or_none()

  async def get_by_project_and_user(
    self,
    project_id: UUID,
    user_id: UUID,
  ) -> ProjectMember | None:
    result = await self.session.execute(
      select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
      )
    )

    return result.scalar_one_or_none()

  async def list_by_project(
    self,
    project_id: UUID,
  ) -> list[ProjectMember]:
    result = await self.session.execute(
      select(ProjectMember)
      .where(
        ProjectMember.project_id == project_id,
      )
      .order_by(ProjectMember.created_at.asc())
    )

    return list(result.scalars().all())

  async def delete(
    self,
    member: ProjectMember,
  ) -> None:
    await self.session.delete(member)
    await self.session.flush()

class MilestoneRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(
    self,
    milestone: Milestone,
  ) -> Milestone:
    self.session.add(milestone)
    await self.session.flush()
    return milestone

  async def get_by_id_and_project(
    self,
    milestone_id: UUID,
    project_id: UUID,
  ) -> Milestone | None:
    result = await self.session.execute(
      select(Milestone).where(
        Milestone.id == milestone_id,
        Milestone.project_id == project_id,
      )
    )

    return result.scalar_one_or_none()

  async def list_by_project(
    self,
    project_id: UUID,
  ) -> list[Milestone]:
    result = await self.session.execute(
      select(Milestone)
      .where(
        Milestone.project_id == project_id,
      )
      .order_by(
        Milestone.due_date.asc().nullslast(),
        Milestone.created_at.asc(),
      )
    )

    return list(result.scalars().all())

  async def update(
    self,
    milestone: Milestone,
  ) -> Milestone:
    self.session.add(milestone)
    await self.session.flush()
    return milestone

  async def delete(
    self,
    milestone: Milestone,
  ) -> None:
    await self.session.delete(milestone)
    await self.session.flush()