from __future__ import annotations
import asyncio
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.modules.identity.models import Organization
from app.modules.projects.models import Client, Milestone, Project, ProjectStatus

async def seed_projects(
  session: AsyncSession,
) -> None:
  organization_result = await session.execute(
    select(Organization)
    .order_by(Organization.created_at.asc())
    .limit(1)
  )

  organization = organization_result.scalar_one_or_none()
  if organization is None:
    print(
      "Skipping project seed: "
      "no organization exists."
    )
    return

  existing_client = await session.execute(
    select(Client).where(
      Client.organization_id == organization.id,
      Client.name == "Trace Construction Client",
    )
  )
  client = existing_client.scalar_one_or_none()

  if client is None:
    client = Client(
      id=uuid4(),
      organization_id=organization.id,
      name="Trace Construction Client",
      contact_name="Project Client",
      email="client@gmail.com",
      phone="+92 300 6208750",
      address="Bahawalpur, Pakistan",
      notes="Seed client.",
    )

    session.add(client)
    await session.flush()

  existing_project = await session.execute(
    select(Project).where(
      Project.organization_id == organization.id,
      Project.code == "TRC-001",
    )
  )

  project = existing_project.scalar_one_or_none()
  if project is None:
    project = Project(
      id=uuid4(),
      organization_id=organization.id,
      client_id=client.id,
      name="Trace Construction Project",
      code="TRC-001",
      description=(
        "Initial Trace Project demonstration project."
      ),
      location="Bahawalpur, Pakistan",
      status=ProjectStatus.ACTIVE,
    )
    session.add(project)
    await session.flush()
    session.add_all(
      [
        Milestone(
          id=uuid4(),
          project_id=project.id,
          name="Site Preparation",
          description=(
            "Initial site preparation and mobilization."
          ),
        ),
        Milestone(
          id=uuid4(),
          project_id=project.id,
          name="Foundation",
          description=(
            "Foundation works."
          ),
        ),
        Milestone(
          id=uuid4(),
          project_id=project.id,
          name="Structural Work",
          description=(
            "Main structural construction."
          ),
        ),
      ]
    )
  await session.commit()

  print(
    "Projects module seeding completed successfully."
  )

async def main():
  async with AsyncSessionLocal() as session:
    await seed_projects(session)

if __name__ == "__main__":
  asyncio.run(main())