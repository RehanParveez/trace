from __future__ import annotations
from app.modules.drawings_boq.models import Drawing, BuildingSpace, BuildingLevel, DrawingElement, DrawingFormat, DrawingStatus, ElementRelation, SpaceFinish
from sqlalchemy import select, delete, func, update
import argparse
import asyncio
from app.shared.storage import download_to_path
import ifcopenshell
import ifcopenshell.util.placement
from app.modules.drawings_boq.ifc_reader import _resolve_scales, _read_levels, _type_fields, _dec
import tempfile
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID
import ifcopenshell.util.element
from app.modules.drawings_boq.ifc_spatial import read_spatial
from app.core.database import AsyncSessionLocal
from app.modules.drawings_boq.spatial_repository import persist_spatial

async def backfill_drawing(session, drawing: Drawing, *, force: bool, drop_finishes: bool, dry_run: bool) -> dict:
  spaces = (await session.execute(select(func.count()).select_from(BuildingSpace).where(
    BuildingSpace.drawing_id == drawing.id, BuildingSpace.source == "IFC"))).scalar_one()
  if spaces and not force:
    return {"status": "skipped", "reason": "already has spaces"}
  if spaces:
    finishes = (await session.execute(select(func.count()).select_from(SpaceFinish).join(
      BuildingSpace, BuildingSpace.id == SpaceFinish.space_id).where(
      BuildingSpace.drawing_id == drawing.id, SpaceFinish.is_active.is_(True)))).scalar_one()
    if finishes and not drop_finishes:
      return {"status": "skipped", "reason": f"{finishes} finish(es) would be deleted; use --drop-finishes"}

  with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "drawing.ifc")
    await asyncio.to_thread(download_to_path, drawing.storage_key, path)
    model = await asyncio.to_thread(ifcopenshell.open, path)
    scales = _resolve_scales(model)
    levels = _read_levels(model, scales)
    db_elements = (await session.execute(select(DrawingElement.id, DrawingElement.ifc_global_id,
      DrawingElement.structural_role, DrawingElement.type_mark, DrawingElement.bbox_min_x_mm).where(
      DrawingElement.drawing_id == drawing.id))).all()
    known = {r.ifc_global_id for r in db_elements if r.ifc_global_id}
    read = await asyncio.to_thread(read_spatial, model, scales, levels, known)

    marks: dict = {}
    for r in db_elements:
      if r.structural_role in ("DOOR", "WINDOW") and r.ifc_global_id and (r.type_mark is None or r.bbox_min_x_mm is None):
        try:
          element = model.by_guid(r.ifc_global_id)
          fields = {}
          if r.type_mark is None:
            f = _type_fields(element, ifcopenshell.util.element.get_psets(element, psets_only=True) or {}, r.structural_role)
            fields.update({k: v for k, v in f.items() if v})
          if r.bbox_min_x_mm is None and element.ObjectPlacement is not None:
            o = ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)[:3, 3] * scales.mm_per_unit
            for axis, v in zip("xyz", o):
              fields[f"bbox_min_{axis}_mm"] = fields[f"bbox_max_{axis}_mm"] = _dec(float(v))
          if fields:
            marks[r.id] = fields
        except Exception:
          continue

  result = {"status": "ok", "spaces": len(read.spaces), "boundaries": len(read.boundaries),
    "relations": len(read.relations), "marks_filled": len(marks)}
  if dry_run:
    return {**result, "status": "dry-run"}

  if spaces:
    await session.execute(delete(BuildingSpace).where(BuildingSpace.drawing_id == drawing.id, BuildingSpace.source == "IFC"))
  await session.execute(delete(ElementRelation).where(ElementRelation.drawing_id == drawing.id, ElementRelation.source == "IFC"))
  level_ids = {b.ifc_storey_id: b.id for b in (await session.execute(select(BuildingLevel).where(
    BuildingLevel.drawing_id == drawing.id))).scalars().all() if b.ifc_storey_id}
  
  elements = [SimpleNamespace(id=r.id, ifc_global_id=r.ifc_global_id) for r in db_elements]
  read_result = SimpleNamespace(spaces=read.spaces, boundaries=read.boundaries, relations=read.relations, model_issues=[])
  await persist_spatial(session, drawing, read_result, elements, level_ids)
  for element_id, fields in marks.items():
    await session.execute(update(DrawingElement).where(DrawingElement.id == element_id).values(**fields))
  meta = dict(drawing.ingestion_meta or {})
  meta["spatial_backfilled_at"] = datetime.now(timezone.utc).isoformat()
  if read_result.model_issues:
    meta["backfill_issues"] = read_result.model_issues
    result["issues"] = read_result.model_issues
  drawing.ingestion_meta = meta
  await session.commit()
  return result

async def main() -> None:
  ap = argparse.ArgumentParser()
  ap.add_argument("--org"); ap.add_argument("--project"); ap.add_argument("--drawing")
  ap.add_argument("--force", action="store_true"); ap.add_argument("--drop-finishes", action="store_true")
  ap.add_argument("--dry-run", action="store_true")
  args = ap.parse_args()
  
  async with AsyncSessionLocal() as session:
    stmt = select(Drawing).where(Drawing.format == DrawingFormat.IFC, Drawing.status == DrawingStatus.PARSED,
      Drawing.is_current_revision.is_(True))
    if args.org:
      stmt = stmt.where(Drawing.organization_id == UUID(args.org))
    if args.project:
      stmt = stmt.where(Drawing.project_id == UUID(args.project))
    if args.drawing:
      stmt = stmt.where(Drawing.id == UUID(args.drawing))
    drawings = list((await session.execute(stmt.order_by(Drawing.created_at.asc()))).scalars().all())
    print(f"{len(drawings)} drawing(s) to process")
    for d in drawings:
      try:
        print(d.id, d.original_filename, await backfill_drawing(
          session, d, force=args.force, drop_finishes=args.drop_finishes, dry_run=args.dry_run))
      except Exception as exc:
        await session.rollback()
        print(d.id, d.original_filename, "FAILED", str(exc)[:300])

if __name__ == "__main__":
  asyncio.run(main())