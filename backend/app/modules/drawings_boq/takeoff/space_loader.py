from __future__ import annotations
from decimal import Decimal
from types import SimpleNamespace
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.engine.measure import takeoff as tk
from app.modules.drawings_boq.models import BuildingLevel, Drawing, DrawingFormat, TakeoffCandidate
from app.modules.drawings_boq.takeoff import placement as P
from app.modules.drawings_boq.takeoff import z_range as Z
from app.modules.drawings_boq.takeoff.levels import view_level_id

SPACE_CATEGORIES = ("COLUMN", "FOOTING", "BEAM", "SLAB", "LINTEL", "WALL")
SPACE_MODES = ("COUNT_X_VOLUME", "LENGTH_X_HEIGHT_X_THICKNESS")

def _f(value) -> float | None:
  try:
    v = float(value)
  except (TypeError, ValueError):
    return None
  return v if v == v else None

def _mm_per_pt(cand) -> float | None:
  v = _f(getattr(cand, "mm_per_pt", None))
  return v if v and v > 0 else None

def _run_points(points, scale: float) -> tuple:
  """The runs of a polyline as (x1, y1, x2, y2) in millimetres; a run of no length is left out."""
  out = []
  pts = []
  for p in points or []:
    try:
      pts.append((float(p[0]) * scale, float(p[1]) * scale))
    except (TypeError, ValueError, IndexError):
      return ()
  for a, b in zip(pts, pts[1:]):
    if abs(a[0] - b[0]) + abs(a[1] - b[1]) > 1e-6:
      out.append((round(a[0], 2), round(a[1], 2), round(b[0], 2), round(b[1], 2)))
  return tuple(out)

def kind_of(cand) -> str | None:
  """The kind of member for height and role: the register's own kinds, with an RCC wall told apart from a brick one."""
  kind = Z.member_kind(cand.category, cand.facts)
  if kind == "WALL" and (cand.facts or {}).get("construction") == "RCC":
    return "RCC_WALL"
  return kind

def build_space(cand, m, sheet, *, view: str, floors: dict, floor_key: str | None, footing: Z.FootingLevel | None, walls_by_key: dict | None = None):
  """One SpaceInput for a confirmed measurement of a member, or None when the measurement is not a concrete or masonry volume the engine can place. Pure: the
  candidate, the measurement, its sheet and the datums of its floor are given."""
  kind = kind_of(cand)
  if kind is None or kind in ("STAIR",):
    return None
  if m.quantity_mode not in SPACE_MODES:
    return None
  p = m.params or {}
  
  proxy = SimpleNamespace(category=cand.category, facts=cand.facts, params={**(cand.params or {}), **p})
  zr = P.z_of(proxy, floors, floor_key, footing)
  z0 = zr.base_mm if zr is not None and zr.known else None
  z1 = zr.top_mm if zr is not None and zr.known else None
  scale = _mm_per_pt(cand)
  
  shape, parts, length, width = "NONE", (), Decimal(0), Decimal(0)
  if kind in ("COLUMN", "NECK", "FOOTING") and scale is not None:
    points = (m.geometry or {}).get("points") or []
    size = (_f(p.get("length_mm")), _f(p.get("width_mm")))
    
    if points and size[0] and size[1] and size[0] > 0 and size[1] > 0:
      try:
        parts = tuple((round(float(q[0]) * scale, 1), round(float(q[1]) * scale, 1)) for q in points)
        shape, length, width = "BOX", Decimal(str(size[0])), Decimal(str(size[1]))
      except (TypeError, ValueError, IndexError):
        parts = ()
  elif kind in ("WALL", "RCC_WALL") and scale is not None:
    thickness = _f(p.get("thickness_mm"))
    runs = _run_points((m.geometry or {}).get("points"), scale) or _run_points((cand.geometry or {}).get("points"), scale)
    if runs and thickness and thickness > 0:
      shape, parts, width = "STRIP", runs, Decimal(str(thickness))
  elif kind in ("BEAM", "PLINTH_BEAM", "BAND") and (cand.facts or {}).get("derived_from") == "WALLS":
    width_mm = _f(p.get("width_mm"))
    runs: list = []
    
    for key in (cand.facts or {}).get("wall_keys") or []:
      wall = (walls_by_key or {}).get(key)
      ws = _mm_per_pt(wall) if wall is not None else None
      if wall is not None and ws is not None:
        runs.extend(_run_points((wall.geometry or {}).get("points"), ws))
    if runs and width_mm and width_mm > 0:
      shape, parts, width = "STRIP", tuple(runs), Decimal(str(width_mm))
  return tk.SpaceInput(
    measurement_id=m.id, candidate_id=cand.id, sheet_id=sheet.id, group=str(sheet.drawing_id), page_no=sheet.page_no, category=kind, tag=cand.tag, level_id=m.level_id,
    frame=view, shape=shape, parts=parts, length_mm=length, width_mm=width, z0_mm=z0, z1_mm=z1, z_grade=zr.grade if zr is not None else "ASSUMED", floor=floor_key,
    covered_by_band=kind == "LINTEL" and bool((cand.facts or {}).get("tie_band")))

def floor_data(group: str, floors: dict) -> tuple:
  return tuple(tk.FloorDatum(group, f.key, float(f.level_mm), f.soffit_mm, f.top_mm, f.grade) for f in floors.values())

async def load_space(session: AsyncSession, org: UUID, measurements: list, sheets: dict) -> tuple:

  from app.modules.drawings_boq.takeoff.register_service import RegisterService
  from app.modules.drawings_boq.takeoff.repository import view_key
  ids = [m.id for m in measurements if m.quantity_mode in SPACE_MODES]
  if not ids:
    return (), ()
  cands = (await session.execute(select(TakeoffCandidate).where(TakeoffCandidate.organization_id == org, TakeoffCandidate.measurement_id.in_(ids),
    TakeoffCandidate.category.in_(SPACE_CATEGORIES), TakeoffCandidate.decision == "ACCEPTED"))).scalars().all()
  by_measurement = {c.measurement_id: c for c in cands}
  
  if not by_measurement:
    return (), ()
  drawing_ids = sorted({sheets[m.sheet_id].drawing_id for m in measurements if m.id in by_measurement}, key=str)
  drawings = {d.id: d for d in (await session.execute(select(Drawing).where(Drawing.organization_id == org, Drawing.id.in_(drawing_ids)))).scalars().all()}
  level_ids = {sheets[m.sheet_id].level_id for m in measurements if m.id in by_measurement and sheets[m.sheet_id].level_id}
  level_ids |= {lv for lv in (view_level_id(by_measurement[m.id]) for m in measurements if m.id in by_measurement) if lv}
  
  floor_of: dict = {}
  if level_ids:
    for lv in (await session.execute(select(BuildingLevel).where(BuildingLevel.organization_id == org, BuildingLevel.id.in_(list(level_ids))))).scalars().all():
      floor_of[lv.id] = (lv.ifc_storey_id or "").removeprefix("PDF:")
  need_walls = {sheets[m.sheet_id].id for m in measurements if m.id in by_measurement and (by_measurement[m.id].facts or {}).get("derived_from") == "WALLS"}
  walls: dict = {}
  if need_walls:
    for w in (await session.execute(select(TakeoffCandidate).where(TakeoffCandidate.organization_id == org, TakeoffCandidate.sheet_id.in_(list(need_walls)),
        TakeoffCandidate.category == "WALL"))).scalars().all():
      walls[(w.sheet_id, w.ckey)] = w

  service = RegisterService(session)
  datums: dict = {}
  for did in drawing_ids:
    d = drawings.get(did)
    if d is None or d.format != DrawingFormat.PDF:
      continue
    datums[did] = await service._datums(org, d)
  out: list = []
  floors_out: list = []
  
  for did, (floors, _) in sorted(datums.items(), key=lambda kv: str(kv[0])):
    floors_out.extend(floor_data(str(did), floors))
  for m in sorted(measurements, key=lambda x: str(x.id)):
    cand = by_measurement.get(m.id)
    if cand is None:
      continue
  
    sheet = sheets[m.sheet_id]
    floors, footing = datums.get(sheet.drawing_id, ({}, None))
    lvl = view_level_id(cand) or sheet.level_id
    walls_by_key = {k[1]: w for k, w in walls.items() if k[0] == sheet.id}
    item = build_space(cand, m, sheet, view=view_key(cand, sheet), floors=floors, floor_key=floor_of.get(lvl) if lvl else None, footing=footing,
      walls_by_key=walls_by_key)
    if item is not None:
      out.append(item)
  return tuple(out), tuple(floors_out)
