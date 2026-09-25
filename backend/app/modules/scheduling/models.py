from __future__ import annotations
from app.core.database import Base
from app.shared.mixins import TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy import Enum, Boolean, Date, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
import enum
import uuid
from decimal import Decimal
from datetime import date

class ScheduleTaskStatus(str, enum.Enum):
  NOT_STARTED = "NOT_STARTED"
  IN_PROGRESS = "IN_PROGRESS"
  COMPLETE = "COMPLETE"
  
class ProjectSchedule(Base, TimestampMixin):
  __tablename__ = "project_schedules"

  __table_args__ = (UniqueConstraint("organization_id", "project_id", name="uq_project_schedule_project"),)

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  target_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)

class ScheduleTask(Base, TimestampMixin):
  __tablename__ = "schedule_tasks"

  __table_args__ = (Index("ix_schedule_tasks_org_project", "organization_id", "project_id"),)

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  project_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("projects.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  name: Mapped[str] = mapped_column(String(300), nullable=False)
  description: Mapped[str | None] = mapped_column(Text, nullable=True)

  planned_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
 
  planned_duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
  is_milestone_marker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

  actual_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
  actual_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
  percent_complete: Mapped[Decimal] = mapped_column(
    Numeric(5, 2), 
    nullable=False,
    default=Decimal("0"),
  )
  
  status: Mapped[ScheduleTaskStatus] = mapped_column(
    Enum(ScheduleTaskStatus,
    name="schedule_task_status"),
    nullable=False,
    default=ScheduleTaskStatus.NOT_STARTED,
  )

  sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

  predecessor_links: Mapped[list["ScheduleDependency"]] = relationship(
    "ScheduleDependency",
    foreign_keys="ScheduleDependency.successor_task_id",
    back_populates="successor_task",
    cascade="all, delete-orphan",
  )
  
  successor_links: Mapped[list["ScheduleDependency"]] = relationship(
    "ScheduleDependency", 
    foreign_keys="ScheduleDependency.predecessor_task_id",
    back_populates="predecessor_task",
    cascade="all, delete-orphan",
  )

class ScheduleDependency(Base):
  __tablename__ = "schedule_dependencies"

  __table_args__ = (
    UniqueConstraint("predecessor_task_id", "successor_task_id", name="uq_schedule_dependency_pair"),
  )

  id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  
  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
  )

  predecessor_task_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("schedule_tasks.id", ondelete="CASCADE"),
    nullable=False,
  )
  
  successor_task_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("schedule_tasks.id", ondelete="CASCADE"),
    nullable=False,
  )

  predecessor_task: Mapped["ScheduleTask"] = relationship(
    "ScheduleTask",
    foreign_keys=[predecessor_task_id],
    back_populates="successor_links",
  )
  
  successor_task: Mapped["ScheduleTask"] = relationship(
    "ScheduleTask",
    foreign_keys=[successor_task_id],
    back_populates="predecessor_links",
  )
