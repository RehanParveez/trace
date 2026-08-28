from __future__ import annotations
import enum
import uuid
from datetime import date
from uuid import UUID
from sqlalchemy import Date, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.shared.mixins import TimestampMixin

class ProjectStatus(str, enum.Enum):
  PLANNING = "PLANNING"
  ACTIVE = "ACTIVE"
  ON_HOLD = "ON_HOLD"
  COMPLETED = "COMPLETED"
  CANCELLED = "CANCELLED"

class ProjectMemberRole(str, enum.Enum):
  MANAGER = "MANAGER"
  ENGINEER = "ENGINEER"
  SUPERVISOR = "SUPERVISOR"
  SITE_MANAGER = "SITE_MANAGER"
  MEMBER = "MEMBER"

class Client(Base, TimestampMixin):
  __tablename__ = "clients"

  __table_args__ = (
    UniqueConstraint(
      "organization_id",
      "name",
      name="uq_clients_organization_name",
    ),
    Index(
      "ix_clients_org_name",
      "organization_id",
      "name",
    ),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "organizations.id",
      ondelete="CASCADE",
    ),
    nullable=False,
    index=True,
  )

  name: Mapped[str] = mapped_column(
    String(200),
    nullable=False,
  )

  contact_name: Mapped[str | None] = mapped_column(
    String(200),
    nullable=True,
  )

  email: Mapped[str | None] = mapped_column(
    String(255),
    nullable=True,
  )

  phone: Mapped[str | None] = mapped_column(
    String(50),
    nullable=True,
  )

  address: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  notes: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  organization = relationship(
    "Organization",
    lazy="joined",
  )

  projects: Mapped[list["Project"]] = relationship(
    "Project",
    back_populates="client",
  )

class Project(Base, TimestampMixin):
  __tablename__ = "projects"

  __table_args__ = (
    Index(
      "ix_projects_org_status",
      "organization_id",
      "status",
    ),
    Index(
      "ix_projects_org_client",
      "organization_id",
      "client_id",
    ),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "organizations.id",
      ondelete="CASCADE",
    ),
    nullable=False,
    index=True,
  )

  client_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "clients.id",
      ondelete="SET NULL",
    ),
    nullable=True,
    index=True,
  )

  name: Mapped[str] = mapped_column(
    String(200),
    nullable=False,
  )

  code: Mapped[str | None] = mapped_column(
    String(100),
    nullable=True,
  )

  description: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  location: Mapped[str | None] = mapped_column(
    String(500),
    nullable=True,
  )

  status: Mapped[ProjectStatus] = mapped_column(
    Enum(
      ProjectStatus,
      name="project_status",
    ),
    nullable=False,
    default=ProjectStatus.PLANNING,
    index=True,
  )

  start_date: Mapped[date | None] = mapped_column(
    Date,
    nullable=True,
  )

  expected_end_date: Mapped[date | None] = mapped_column(
    Date,
    nullable=True,
  )

  actual_end_date: Mapped[date | None] = mapped_column(
    Date,
    nullable=True,
  )

  organization = relationship(
    "Organization",
    lazy="joined",
  )

  client: Mapped["Client | None"] = relationship(
    "Client",
    back_populates="projects",
  )

  members: Mapped[list["ProjectMember"]] = relationship(
    "ProjectMember",
    back_populates="project",
    cascade="all, delete-orphan",
  )

  milestones: Mapped[list["Milestone"]] = relationship(
    "Milestone",
    back_populates="project",
    cascade="all, delete-orphan",
  )

class ProjectMember(Base, TimestampMixin):
  __tablename__ = "project_members"

  __table_args__ = (
    UniqueConstraint(
      "project_id",
      "user_id",
      name="uq_project_members_project_user",
    ),
    Index(
      "ix_project_members_project",
      "project_id",
    ),
    Index(
      "ix_project_members_user",
      "user_id",
    ),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "projects.id",
      ondelete="CASCADE",
    ),
    nullable=False,
  )

  user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "users.id",
      ondelete="CASCADE",
    ),
    nullable=False,
  )

  role: Mapped[ProjectMemberRole] = mapped_column(
    Enum(
      ProjectMemberRole,
      name="project_member_role",
    ),
    nullable=False,
    default=ProjectMemberRole.MEMBER,
  )

  project: Mapped["Project"] = relationship(
    "Project",
    back_populates="members",
  )

  user = relationship(
    "User",
    lazy="joined",
  )

class Milestone(Base, TimestampMixin):
  __tablename__ = "milestones"

  __table_args__ = (
    Index(
      "ix_milestones_project",
      "project_id",
    ),
    Index(
      "ix_milestones_project_due_date",
      "project_id",
      "due_date",
    ),
  )

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
  )

  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "projects.id",
      ondelete="CASCADE",
    ),
    nullable=False,
    index=True,
  )

  name: Mapped[str] = mapped_column(
    String(200),
    nullable=False,
  )

  description: Mapped[str | None] = mapped_column(
    Text,
    nullable=True,
  )

  due_date: Mapped[date | None] = mapped_column(
    Date,
    nullable=True,
  )

  completed_at: Mapped[date | None] = mapped_column(
    Date,
    nullable=True,
  )

  project: Mapped["Project"] = relationship(
    "Project",
    back_populates="milestones",
  )