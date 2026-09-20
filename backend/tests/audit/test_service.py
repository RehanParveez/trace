from __future__ import annotations
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.modules.audit.models import AuditLog, AuditAction, AuditEntityType
from app.modules.audit.service import AuditLogService

@pytest.mark.asyncio
async def test_log_creates_entry_and_commits(
  audit_service: AuditLogService,
  audit_admin_context,
  db_session,
):
  org = audit_admin_context.organization
  actor = audit_admin_context.user
  entity_id = uuid4()

  entry = await audit_service.log(
    organization_id=org.id,
    actor_user_id=actor.id,
    entity_type=AuditEntityType.PROJECT,
    entity_id=entity_id,
    action=AuditAction.CREATE,
    summary="Project created",
    changes={"name": {"old": None, "new": "Tower A"}},
    ip_address="10.0.0.1",
    commit=True,
  )
  assert entry is not None
  assert entry.id is not None
  assert entry.organization_id == org.id
  assert entry.actor_user_id == actor.id
  assert entry.entity_type == AuditEntityType.PROJECT
  assert entry.entity_id == entity_id
  assert entry.action == AuditAction.CREATE
  assert entry.summary == "Project created"
  assert entry.changes == {"name": {"old": None, "new": "Tower A"}}
  assert entry.ip_address == "10.0.0.1"
  result = await db_session.execute(select(AuditLog).where(AuditLog.id == entry.id))
  assert result.scalar_one_or_none() is not None

@pytest.mark.asyncio
async def test_log_without_commit_does_not_persist(
  audit_service: AuditLogService,
  audit_admin_context,
  db_session,
):
  org = audit_admin_context.organization

  entry = await audit_service.log(
    organization_id=org.id,
    actor_user_id=None,
    entity_type=AuditEntityType.DRAWING,
    entity_id=uuid4(),
    action=AuditAction.UPDATE,
    summary="Drawing updated",
    commit=False,
  )
  assert entry is not None
  await db_session.rollback()

  result = await db_session.execute(select(AuditLog).where(AuditLog.id == entry.id))
  assert result.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_log_returns_none_on_failure_and_rolls_back(
  audit_service: AuditLogService,
  audit_admin_context,
  db_session,
  monkeypatch,
):
  org = audit_admin_context.organization

  async def boom(*args, **kwargs):
    raise RuntimeError("forced DB failure")

  monkeypatch.setattr(audit_service.repository, "create", boom)
  entry = await audit_service.log(
    organization_id=org.id,
    actor_user_id=None,
    entity_type=AuditEntityType.BOQ_ITEM,
    entity_id=uuid4(),
    action=AuditAction.DELETE,
    summary="Should never be written",
    commit=True,
  )
  assert entry is None
  result = await db_session.execute(
    select(AuditLog).where(AuditLog.summary == "Should never be written")
  )
  assert result.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_list_logs_filters_and_ordering(
  audit_service: AuditLogService,
  audit_admin_context,
  make_audit_log,
  other_organization,
):
  org = audit_admin_context.organization
  actor = audit_admin_context.user
  now = datetime.now(timezone.utc)
  e1 = await make_audit_log(
    organization=org,
    actor_user_id=actor.id,
    entity_type=AuditEntityType.PROJECT,
    action=AuditAction.CREATE,
    summary="first",
    created_at=now - timedelta(minutes=10),
  )
  e2 = await make_audit_log(
    organization=org,
    actor_user_id=actor.id,
    entity_type=AuditEntityType.PROJECT,
    action=AuditAction.UPDATE,
    summary="second",
    created_at=now - timedelta(minutes=5),
  )
  e3 = await make_audit_log(
    organization=org,
    actor_user_id=None,
    entity_type=AuditEntityType.DRAWING,
    action=AuditAction.CREATE,
    summary="drawing",
    created_at=now,
  )
  await make_audit_log(
    organization=other_organization,
    entity_type=AuditEntityType.PROJECT,
    action=AuditAction.CREATE,
    summary="other-org",
  )

  rows = await audit_service.list_logs(org.id)
  assert len(rows) == 3
  assert [r.summary for r in rows] == ["drawing", "second", "first"]

  rows = await audit_service.list_logs(org.id, entity_type=AuditEntityType.PROJECT)
  assert len(rows) == 2
  assert all(r.entity_type == AuditEntityType.PROJECT for r in rows)

  rows = await audit_service.list_logs(org.id, action=AuditAction.UPDATE)
  assert len(rows) == 1
  assert rows[0].id == e2.id

  rows = await audit_service.list_logs(org.id, actor_user_id=actor.id)
  assert len(rows) == 2

  rows = await audit_service.list_logs(org.id, skip=1, limit=1)
  assert len(rows) == 1
  assert rows[0].summary == "second"

@pytest.mark.asyncio
async def test_list_for_entity_returns_only_matching_rows(
  audit_service: AuditLogService,
  audit_admin_context,
  make_audit_log,
):
  org = audit_admin_context.organization
  entity_id = uuid4()

  await make_audit_log(
    organization=org,
    entity_type=AuditEntityType.PROGRESS_CLAIM,
    entity_id=entity_id,
    action=AuditAction.CREATE,
    summary="claim created",
  )
  await make_audit_log(
    organization=org,
    entity_type=AuditEntityType.PROGRESS_CLAIM,
    entity_id=entity_id,
    action=AuditAction.APPROVE,
    summary="claim approved",
  )
  await make_audit_log(
    organization=org,
    entity_type=AuditEntityType.PROGRESS_CLAIM,
    entity_id=uuid4(),
    action=AuditAction.CREATE,
    summary="other claim",
  )
  rows = await audit_service.list_for_entity(
    org.id, AuditEntityType.PROGRESS_CLAIM, entity_id
  )
  assert len(rows) == 2
  assert all(r.entity_id == entity_id for r in rows)
  assert rows[0].action == AuditAction.APPROVE

@pytest.mark.asyncio
async def test_list_latest_by_entity_type_returns_one_row_per_entity(
  audit_service: AuditLogService,
  audit_admin_context,
  make_audit_log,
):
  org = audit_admin_context.organization
  now = datetime.now(timezone.utc)

  entity_a = uuid4()
  entity_b = uuid4()

  await make_audit_log(
    organization=org,
    entity_type=AuditEntityType.PROJECT,
    entity_id=entity_a,
    action=AuditAction.CREATE,
    summary="A created",
    created_at=now - timedelta(hours=2),
  )
  await make_audit_log(
    organization=org,
    entity_type=AuditEntityType.PROJECT,
    entity_id=entity_a,
    action=AuditAction.STATUS_CHANGE,
    summary="A status changed",
    created_at=now - timedelta(hours=1),
  )
  await make_audit_log(
    organization=org,
    entity_type=AuditEntityType.PROJECT,
    entity_id=entity_b,
    action=AuditAction.UPDATE,
    summary="B updated",
    created_at=now,
  )
  rows = await audit_service.list_latest_by_entity_type(
    org.id, AuditEntityType.PROJECT
  )
  assert len(rows) == 2
  by_id = {r.entity_id: r for r in rows}
  assert by_id[entity_a].action == AuditAction.STATUS_CHANGE
  assert by_id[entity_a].summary == "A status changed"
  assert by_id[entity_b].action == AuditAction.UPDATE