from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID, uuid4
from app.engine.measure.models import ModelElement
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.identity.models import Organization
from app.modules.subscriptions.models import Plan, Subscription, SubscriptionStatus, BillingInterval
from datetime import timedelta
from app.modules.projects.models import Project, ProjectStatus
from app.modules.drawings_boq.models import Drawing, DrawingElement, BuildingLevel, DrawingFormat, DrawingStatus
from datetime import date, datetime, timezone
from sqlalchemy import bindparam, insert, update
from sqlalchemy import select
from app.engine.measure.synthetic import frame, level_ids, shifted
from app.modules.drawings_boq.calc_service import CalculationService
import time
from app.modules.drawings_boq.models import CalculationRun

_INSERT_CHUNK = 2000

@dataclass
class SyntheticProject:
  project_id: UUID
  drawing_id: UUID
  namespace: UUID
  grid: tuple
  elements: int

def _row(el: ModelElement, drawing_id: UUID, organization_id: UUID) -> dict:
  lo, hi = el.bbox_min_mm, el.bbox_max_mm
  vol = float(el.volume_mm3) if el.volume_mm3 is not None else 0.0
  return {
    "id": el.id, "drawing_id": drawing_id, "organization_id": organization_id, "ifc_global_id": el.ifc_global_id,
    "ifc_type": el.ifc_type, "name": el.ifc_global_id, "unit": "m3", "quantity": round(vol / 1e9, 4),
    "properties": {}, "discipline": "STRUCTURAL", "structural_role": el.role, "classification_source": "SYNTHETIC",
    "classification_confidence": el.classification_confidence, "quantity_source": "GEOMETRY",
    "level_id": el.level_id, "volume_mm3": el.volume_mm3,
    "bbox_min_x_mm": lo[0], "bbox_min_y_mm": lo[1], "bbox_min_z_mm": lo[2],
    "bbox_max_x_mm": hi[0], "bbox_max_y_mm": hi[1], "bbox_max_z_mm": hi[2],
    "geometry_kind": el.geometry_kind, "profile": el.profile, "placement": el.placement,
    "normalization_status": el.normalization_status, "normalization_issues": [],
  }

async def _insert_elements(session: AsyncSession, rows: list[dict]) -> None:
  table = DrawingElement.__table__
  now = datetime.now(timezone.utc)
  for i in range(0, len(rows), _INSERT_CHUNK):
    await session.execute(insert(table), [{**r, "created_at": now, "updated_at": now} for r in rows[i:i + _INSERT_CHUNK]])

async def ensure_organization(session: AsyncSession, *, plan_slug: str = "professional", name: str | None = None):
  
  org = Organization(id=uuid4(), name=name or f"Loadtest {uuid4().hex[:6]}", slug=f"load-{uuid4().hex[:8]}", is_active=True)
  session.add(org)
  await session.flush()
  plan = (await session.execute(select(Plan).where(Plan.slug == plan_slug))).scalar_one()
  now = datetime.now(timezone.utc)
  session.add(Subscription(id=uuid4(), organization_id=org.id, plan_id=plan.id, status=SubscriptionStatus.ACTIVE,
    billing_interval=BillingInterval.MONTHLY, quantity=1, started_at=now, current_period_start=now,
    current_period_end=now + timedelta(days=30)))
  await session.commit()
  return org

async def seed_synthetic_project(session: AsyncSession, organization_id: UUID, *, grid: tuple, user_id: UUID | None = None,
  name: str | None = None, namespace: UUID | None = None) -> SyntheticProject:
  nx, ny, nz = grid
  namespace = namespace or uuid4()
  project = Project(id=uuid4(), organization_id=organization_id, client_id=None, name=name or f"Synthetic {nx}x{ny}x{nz}",
    code=f"SYN-{uuid4().hex[:6].upper()}", description="Synthetic load-test model", location="n/a",
    status=ProjectStatus.PLANNING, start_date=date.today())
  session.add(project)
  await session.flush()
  
  drawing = Drawing(id=uuid4(), organization_id=organization_id, project_id=project.id, uploaded_by_user_id=user_id,
    original_filename=f"synthetic_{nx}x{ny}x{nz}.ifc", storage_key=f"loadtest/{uuid4().hex}.ifc", format=DrawingFormat.IFC,
    status=DrawingStatus.PARSED, file_size_bytes=0, revision_group_id=uuid4(), is_current_revision=True,
    parsed_at=datetime.now(timezone.utc), ingestion_meta={"synthetic": True})
  session.add(drawing)
  await session.flush()
  
  for k, lid in enumerate(level_ids(namespace, nz)):
    session.add(BuildingLevel(id=lid, organization_id=organization_id, drawing_id=drawing.id, name=f"Level {k}",
      elevation_mm=k * 3000, ifc_storey_id=f"level-{k}", sequence=k))
  await session.flush()
  
  elements = frame(nx, ny, nz, namespace=namespace)
  await _insert_elements(session, [_row(e, drawing.id, organization_id) for e in elements])
  await session.commit()
  return SyntheticProject(project.id, drawing.id, namespace, grid, len(elements))

async def edit_columns(session: AsyncSession, synthetic: SyntheticProject, organization_id: UUID, count: int,
  dx: float = 120.0) -> list[str]:
  nx, ny, nz = synthetic.grid
  by_tag = {e.ifc_global_id: e for e in frame(nx, ny, nz, namespace=synthetic.namespace)}
  step = max((nx * ny * nz) // max(count, 1), 1)
  tags = [t for t in sorted(by_tag) if "|col|" in t][::step][:count]
  table = DrawingElement.__table__
  rows = []
  
  for tag in tags:
    moved = shifted(by_tag[tag], dx=dx)
    r = _row(moved, synthetic.drawing_id, organization_id)
    rows.append({"b_id": r["id"], "placement": r["placement"], "bbox_min_x_mm": r["bbox_min_x_mm"],
      "bbox_max_x_mm": r["bbox_max_x_mm"]})
  stmt = update(table).where(table.c.id == bindparam("b_id")).values(
    placement=bindparam("placement"), bbox_min_x_mm=bindparam("bbox_min_x_mm"), bbox_max_x_mm=bindparam("bbox_max_x_mm"))
  
  if rows:
    await session.execute(stmt, rows)
  await session.commit()
  return tags

async def run_to_completion(session: AsyncSession, organization_id: UUID, project_id: UUID, *, user_id: UUID | None = None,
  force_full: bool = False, verify: bool = False, rule_set_code: str | None = None) -> dict:
  
  svc = CalculationService(session)
  started = time.perf_counter()
  run, reused = await svc.request_run(organization_id, project_id, user_id, None, rule_set_code, None,
    force_full=force_full, verify=verify, enqueue=False)
  request_s = time.perf_counter() - started
  run_id = run.id
  
  if reused:
    return {"run_id": run_id, "reused": True, "request_s": request_s, "execute_s": 0.0}
  started = time.perf_counter()
  await svc.execute_run(run_id)
  execute_s = time.perf_counter() - started
  session.expire_all()
  row = await session.get(CalculationRun, run_id)
  return {"run_id": run_id, "reused": False, "request_s": request_s, "execute_s": execute_s, "status": row.status,
    "mode": row.mode, "metrics": row.metrics, "error": row.error_message}