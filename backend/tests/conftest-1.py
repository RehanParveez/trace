from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.orm.attributes import set_committed_value
from app.dependencies.auth import get_current_user
from app.main import app
from app.modules.drawings_boq.models import (
  CalculationRun, Drawing, DrawingElement, DrawingFormat, MeasurementRuleSet, QuantityLedger,
  QuantitySolid, RateBook, RateBookEscalation, RateItem, WorkItem,
)
from app.modules.drawings_boq.permissions import DRAWINGS_BOQ_PERMISSIONS
from app.modules.identity.models import Permission
from app.modules.projects.models import Project, ProjectStatus

ALL_KEYS = [str(k) for k in DRAWINGS_BOQ_PERMISSIONS]

@dataclass
class Actor:
  user_id: object
  org_id: object
  stub: object

  def headers(self) -> dict:
    return {"Authorization": "Bearer test"}

async def _grant(db_session, role, keys):
  perms = []
  for key in keys:
    perm = (await db_session.execute(select(Permission).where(Permission.key == key))).scalar_one_or_none()
    if perm is None:
      perm = Permission(id=uuid4(), key=key, description=key)
      db_session.add(perm)
      await db_session.flush()
    perms.append(perm)
  set_committed_value(role, "permissions", perms)
  await db_session.flush()
  return perms

@pytest_asyncio.fixture
async def make_actor(db_session, make_role, make_user, make_membership):
  async def _factory(org, keys=None) -> Actor:
    keys = ALL_KEYS if keys is None else [str(k) for k in keys]
    role = await make_role(organization=org, name=f"Estimator-{uuid4().hex[:5]}", is_system=False)
    await _grant(db_session, role, keys)
    user = await make_user(organization=org, role=role, email=f"est-{uuid4().hex[:8]}@example.com")
    await make_membership(user=user, organization=org, role=role, is_active=True)
    stub = SimpleNamespace(
      id=user.id,
      active_membership=SimpleNamespace(organization_id=org.id,
        role=SimpleNamespace(permissions=[SimpleNamespace(key=k) for k in keys])))
    return Actor(user.id, org.id, stub)
  return _factory

@pytest.fixture
def act_as():
  def _set(actor: Actor) -> None:
    app.dependency_overrides[get_current_user] = lambda: actor.stub
  return _set

@pytest_asyncio.fixture
async def actor_a(organization, make_actor):
  return await make_actor(organization)

@pytest_asyncio.fixture
async def actor_b(other_organization, make_actor):
  return await make_actor(other_organization)

@pytest_asyncio.fixture
async def project_a(project_factory):
  return await project_factory()

@pytest_asyncio.fixture
async def project_b(db_session, other_organization):
  p = Project(id=uuid4(), organization_id=other_organization.id, name="Other", code=f"O-{uuid4().hex[:5]}",
    status=ProjectStatus.PLANNING, start_date=date.today())
  db_session.add(p)
  await db_session.flush()
  return p

@pytest_asyncio.fixture
async def make_book(db_session):
  """Insert a rate book (and its rates) directly. org=None makes a system book."""
  async def _factory(org=None, code="CSR", rates=(), status="ACTIVE", version=1, edition="2024", escalations=(),
    effective_from=None, effective_to=None):
    org_id = org.id if org is not None else None
    book = RateBook(id=uuid4(), organization_id=org_id, code=code, name=f"{code} book", edition=edition,
      currency="PKR", status=status, immutable_version=version, is_system=org_id is None, is_active=True,
      effective_from=effective_from, effective_to=effective_to, extra={},
      published_at=None if status == "DRAFT" else datetime.now(timezone.utc))
    db_session.add(book)
    await db_session.flush()
    for r in rates:
      wi, unit, rate = r[0], r[1], Decimal(str(r[2]))
      trade = r[3] if len(r) > 3 else None
      db_session.add(RateItem(id=uuid4(), rate_book_id=book.id, organization_id=org_id, work_item_code=wi,
        unit=unit, rate=rate, trade=trade, is_active=True, extra={}))
    for e in escalations:
      scope, eff, factor = e
      db_session.add(RateBookEscalation(id=uuid4(), rate_book_id=book.id, organization_id=org_id,
        trade_scope=scope, effective_from=eff, factor=Decimal(str(factor))))
    await db_session.flush()
    return book
  return _factory

@pytest_asyncio.fixture
async def rule_set(db_session):
  rs = MeasurementRuleSet(id=uuid4(), organization_id=None, code=f"P8-{uuid4().hex[:5]}", name="P8 rules", is_system=True,
    is_active=True, status="ACTIVE", immutable_version=1, published_at=datetime.now(timezone.utc))
  db_session.add(rs)
  await db_session.flush()
  return rs

@pytest_asyncio.fixture
async def make_run(db_session, rule_set):
  """A COMPLETED calculation run with one ledger row per line: (work_item_code, canonical qty, unit, ifc guid)."""
  async def _factory(org, project, lines, description_of=None):
    drawing = Drawing(id=uuid4(), organization_id=org.id, project_id=project.id, original_filename="m.ifc",
      storage_key=f"k/{uuid4().hex}", format=DrawingFormat.IFC, revision_group_id=uuid4())
    db_session.add(drawing)
    await db_session.flush()
    run = CalculationRun(id=uuid4(), organization_id=org.id, project_id=project.id, rule_set_id=rule_set.id,
      convention_code=None, drawing_revision_ids=[drawing.id], engine_version="t1", fingerprint=uuid4().hex + uuid4().hex,
      status="COMPLETED", settings={}, stats={})
    db_session.add(run)
    await db_session.flush()
    for code, qty, unit, guid in lines:
      if (await db_session.execute(select(WorkItem).where(WorkItem.code == code, WorkItem.organization_id.is_(None)))).first() is None:
        db_session.add(WorkItem(id=uuid4(), organization_id=None, code=code, description=(description_of or {}).get(code, code),
          unit=unit, trade=(description_of or {}).get(code + ":trade", "Concrete"), is_system=True, is_active=True))
        await db_session.flush()
      el = DrawingElement(id=uuid4(), drawing_id=drawing.id, organization_id=org.id, ifc_type="IfcColumn",
        ifc_global_id=guid, name=f"El {guid}")
      db_session.add(el)
      await db_session.flush()
      solid = QuantitySolid(id=uuid4(), organization_id=org.id, run_id=run.id, element_id=el.id,
        geometry_kind="EXTRUDED_PROFILE", engine_version="t1")
      db_session.add(solid)
      await db_session.flush()
      db_session.add(QuantityLedger(id=uuid4(), organization_id=org.id, run_id=run.id, solid_id=solid.id,
        element_id=el.id, work_item_code=code, quantity_net=Decimal(str(qty)), unit=unit, formula_code="TEST",
        engine_version="t1"))
    await db_session.flush()
    return run
  return _factory
