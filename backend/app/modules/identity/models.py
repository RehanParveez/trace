from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Table, Column, UniqueConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.shared.mixins import TimestampMixin

role_permissions = Table(
  "role_permissions",
  Base.metadata,
  Column(
    "role_id",
    PGUUID(as_uuid=True),
    ForeignKey("roles.id", ondelete="CASCADE"),
    primary_key=True,
  ),
  Column(
    "permission_id",
    PGUUID(as_uuid=True),
    ForeignKey("permissions.id", ondelete="CASCADE"),
    primary_key=True,
  ),
)

class Organization(TimestampMixin, Base):
  __tablename__ = "organizations"

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid4,
  )

  name: Mapped[str] = mapped_column(
    String(255),
    nullable=False,
  )

  slug: Mapped[str] = mapped_column(
    String(100),
    nullable=False,
    unique=True,
    index=True,
  )

  is_active: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=True,
    server_default="true",
  )
  
  ai_enabled: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
    server_default="false",
  )

  users: Mapped[list["User"]] = relationship(
    back_populates="organization",
    cascade="all, delete-orphan",
  )

  roles: Mapped[list["Role"]] = relationship(
    back_populates="organization",
    cascade="all, delete-orphan",
  )

  refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
    back_populates="organization",
    cascade="all, delete-orphan",
  )
  
  invitations: Mapped[list["OrganizationInvitation"]] = relationship(
    back_populates="organization", 
    cascade="all, delete-orphan",
  )
  
  memberships: Mapped[list["OrganizationMembership"]] = relationship(
    back_populates="organization",
    cascade="all, delete-orphan",
    )
  
class OrganizationInvitation(TimestampMixin, Base):
  __tablename__ = "organization_invitations"

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid4,
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

  role_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "roles.id",
      ondelete="RESTRICT",
    ),
    nullable=False,
    index=True,
  )

  invited_by_user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "users.id",
      ondelete="RESTRICT",
    ),
    nullable=False,
    index=True,
  )

  accepted_by_user_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey(
      "users.id",
      ondelete="SET NULL",
    ),
    nullable=True,
    index=True,
  )

  email: Mapped[str] = mapped_column(
    String(320),
    nullable=False,
    index=True,
  )

  token_hash: Mapped[str] = mapped_column(
    String(128),
    nullable=False,
    unique=True,
    index=True,
  )

  expires_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    index=True,
  )

  accepted_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  revoked_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  organization: Mapped["Organization"] = relationship(
    back_populates="invitations",
  )

  role: Mapped["Role"] = relationship(
    back_populates="invitations",
  )

  invited_by: Mapped["User"] = relationship(
    foreign_keys=[invited_by_user_id],
    back_populates="sent_invitations",
  )

  accepted_by: Mapped["User | None"] = relationship(
    foreign_keys=[accepted_by_user_id],
    back_populates="accepted_invitations",
  )

  @property
  def is_accepted(self) -> bool:
    return self.accepted_at is not None

  @property
  def is_revoked(self) -> bool:
    return self.revoked_at is not None

  @property
  def is_expired(self) -> bool:
    return self.expires_at <= datetime.now(timezone.utc)

  @property
  def is_pending(self) -> bool:
    return (
      self.accepted_at is None
      and self.revoked_at is None
      and not self.is_expired
    )

  __table_args__ = (
    Index(
      "ix_organization_invitations_org_email",
      "organization_id",
      "email",
    ),
  )
  
class OrganizationMembership(TimestampMixin, Base):
  __tablename__ = "organization_memberships"

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid4,
  )

  user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  role_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("roles.id", ondelete="RESTRICT"),
    nullable=False,
    index=True,
  )

  is_active: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=True,
    server_default="true",
  )

  user: Mapped["User"] = relationship(
    back_populates="memberships",
  )

  organization: Mapped["Organization"] = relationship(
    back_populates="memberships",
  )

  role: Mapped["Role"] = relationship(
    back_populates="memberships",
  )

  __table_args__ = (
    UniqueConstraint(
      "user_id",
      "organization_id",
      name="uq_memberships_user_org",
    ),
    Index(
      "ix_memberships_org_user",
      "organization_id",
      "user_id",
    ),
  )

class User(TimestampMixin, Base):
  __tablename__ = "users"

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid4,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  role_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("roles.id", ondelete="RESTRICT"),
    nullable=False,
    index=True,
  )

  email: Mapped[str] = mapped_column(
    String(320),
    nullable=False,
    unique=True,
    index=True,
  )

  password_hash: Mapped[str] = mapped_column(
    String(255),
    nullable=False,
  )

  first_name: Mapped[str] = mapped_column(
    String(100),
    nullable=False,
  )

  last_name: Mapped[str] = mapped_column(
    String(100),
    nullable=False,
  )

  is_active: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=True,
    server_default="true",
  )

  is_verified: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
    server_default="false",
  )

  last_login_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  failed_login_attempts: Mapped[int] = mapped_column(
    nullable=False,
    default=0,
    server_default="0",
  )

  locked_until: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  password_changed_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  organization: Mapped["Organization"] = relationship(
    back_populates="users",
  )

  role: Mapped["Role"] = relationship(
    back_populates="users",
  )
  
  sent_invitations: Mapped[list["OrganizationInvitation"]] = relationship(
    foreign_keys="OrganizationInvitation.invited_by_user_id",
    back_populates="invited_by",
  )

  accepted_invitations: Mapped[list["OrganizationInvitation"]] = relationship(
    foreign_keys="OrganizationInvitation.accepted_by_user_id",
    back_populates="accepted_by",
  )
  
  memberships: Mapped[list["OrganizationMembership"]] = relationship(
    back_populates="user",
    cascade="all, delete-orphan",
  )

class Role(TimestampMixin, Base):
  __tablename__ = "roles"

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid4,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  name: Mapped[str] = mapped_column(
    String(100),
    nullable=False,
  )

  description: Mapped[str | None] = mapped_column(
    String(500),
    nullable=True,
  )

  is_system: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
    server_default="false",
  )

  organization: Mapped["Organization"] = relationship(
    back_populates="roles",
  )

  permissions: Mapped[list["Permission"]] = relationship(
    secondary=role_permissions,
    back_populates="roles",
    lazy="selectin",
  )

  users: Mapped[list["User"]] = relationship(
    back_populates="role",
  )
  
  invitations: Mapped[list["OrganizationInvitation"]] = relationship(
    back_populates="role",
  )
  
  memberships: Mapped[list["OrganizationMembership"]] = relationship(
    back_populates="role",
    )

  __table_args__ = (
    UniqueConstraint(
      "organization_id",
      "name",
      name="uq_roles_organization_name",
    ),
  )

class Permission(Base):
  __tablename__ = "permissions"

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid4,
  )

  key: Mapped[str] = mapped_column(
    String(150),
    nullable=False,
    unique=True,
    index=True,
  )

  description: Mapped[str | None] = mapped_column(
    String(500),
    nullable=True,
  )

  roles: Mapped[list["Role"]] = relationship(
    secondary=role_permissions,
    back_populates="permissions",
  )

class RefreshToken(TimestampMixin, Base):
  __tablename__ = "refresh_tokens"

  id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    primary_key=True,
    default=uuid4,
  )

  user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  organization_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )

  token_hash: Mapped[str] = mapped_column(
    String(128),
    nullable=False,
    unique=True,
    index=True,
  )

  expires_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
  )

  revoked_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  replaced_by_token_id: Mapped[UUID | None] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
    nullable=True,
  )

  last_used_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
  )

  ip_address: Mapped[str | None] = mapped_column(
    String(64),
    nullable=True,
  )

  user_agent: Mapped[str | None] = mapped_column(
    String(1024),
    nullable=True,
  )

  user: Mapped["User"] = relationship()

  organization: Mapped["Organization"] = relationship(
    back_populates="refresh_tokens",
  )

  replaced_by: Mapped["RefreshToken | None"] = relationship(
    remote_side="RefreshToken.id",
  )

  @property
  def is_revoked(self) -> bool:
    return self.revoked_at is not None

  @property
  def is_expired(self) -> bool:
    return self.expires_at <= datetime.now().astimezone()

class PlatformAdmin(Base):
  __tablename__ = "platform_admins"

  user_id: Mapped[UUID] = mapped_column(
    PGUUID(as_uuid=True),
    ForeignKey("users.id", ondelete="CASCADE"),
    primary_key=True,
  )

  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    server_default=func.now(),
  )

  user: Mapped["User"] = relationship()

Index(
  "ix_refresh_tokens_user_active",
  RefreshToken.user_id,
  RefreshToken.revoked_at,
)
