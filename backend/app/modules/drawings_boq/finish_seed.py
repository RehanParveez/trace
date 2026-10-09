from __future__ import annotations
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.models import WorkItem, FinishRule
from sqlalchemy import select
from uuid import uuid4

PLACEHOLDER = {"status": "PLACEHOLDER - confirm with QS"}
WORK_ITEMS = [

  ("FIN-FLOOR", "Floor finish", "m2", "Finishes", "TILING"),
  ("FIN-FLOOR-TILE", "Floor tile finish", "m2", "Finishes", "TILING"),
  ("FIN-FLOOR-STONE", "Stone floor finish", "m2", "Finishes", "TILING"),
  ("FIN-FLOOR-MARBLE", "Marble floor finish", "m2", "Finishes", "TILING"),
  ("FIN-FLOOR-GRANITE", "Granite floor finish", "m2", "Finishes", "TILING"),
  ("FIN-FLOOR-CERAMIC", "Ceramic floor tile finish", "m2", "Finishes", "TILING"),
  ("FIN-FLOOR-PORCELAIN", "Porcelain floor tile finish", "m2", "Finishes", "TILING"),
  ("FIN-FLOOR-VITRIFIED", "Vitrified tile floor finish", "m2", "Finishes", "TILING"),

  ("FIN-SCREED", "Cement screed to floor", "m2", "Finishes", "PLASTER"),
  ("FIN-LEVELING", "Floor leveling screed", "m2", "Finishes", "PLASTER"),

  ("FIN-SKIRT", "Skirting", "m", "Finishes", "TILING"),
  ("FIN-SKIRT-TILE", "Tile skirting", "m", "Finishes", "TILING"),
  ("FIN-SKIRT-MARBLE", "Marble skirting", "m", "Finishes", "TILING"),
  ("FIN-SKIRT-GRANITE", "Granite skirting", "m", "Finishes", "TILING"),
  ("FIN-SKIRT-WOOD", "Wooden skirting", "m", "Finishes", "TIMBER"),

  ("FIN-WALL-PLASTER", "Cement plaster to walls", "m2", "Finishes", "PLASTER"),
  ("FIN-PLASTER", "Cement plaster to walls", "m2", "Finishes", "PLASTER"),
  ("FIN-PLASTER-EXT", "External cement plaster/render", "m2", "Finishes", "PLASTER"),

  ("FIN-WALL-PAINT", "Paint to walls", "m2", "Finishes", "PAINT"),
  ("FIN-PAINT", "Paint to walls", "m2", "Finishes", "PAINT"),
  ("FIN-PAINT-EXT", "External paint/coating to walls", "m2", "Finishes", "PAINT"),

  ("FIN-CEIL-PLASTER", "Cement plaster to ceiling", "m2", "Finishes", "PLASTER"),
  ("FIN-CEIL-PAINT", "Paint to ceiling", "m2", "Finishes", "PAINT"),
  ("FIN-CEIL-GYPSUM", "Gypsum board ceiling", "m2", "Finishes", "CEILING"),
  ("FIN-CEIL-SUSPENDED", "Suspended ceiling", "m2", "Finishes", "CEILING"),
  ("FIN-CEIL-ACOUSTIC", "Acoustic ceiling", "m2", "Finishes", "CEILING"),

  ("FIN-DADO", "Wall tile dado", "m2", "Finishes", "TILING"),
  ("FIN-WALL-TILE", "Wall tile finish", "m2", "Finishes", "TILING"),
  ("FIN-WALL-TILE-WET", "Wet-area wall tile finish", "m2", "Finishes", "TILING"),
  ("FIN-WALL-MARBLE", "Marble wall finish", "m2", "Finishes", "TILING"),
  ("FIN-WALL-GRANITE", "Granite wall finish", "m2", "Finishes", "TILING"),
  ("FIN-WALL-CLADDING", "Wall cladding", "m2", "Finishes", "TILING"),

  ("FIN-WATERPROOF-FLOOR", "Floor waterproofing", "m2", "Finishes", "WATERPROOFING"),
  ("FIN-WATERPROOF-WET", "Wet-area waterproofing", "m2", "Finishes", "WATERPROOFING"),
  ("FIN-WATERPROOF-ROOF", "Roof/terrace waterproofing", "m2", "Finishes", "WATERPROOFING"),
  ("FIN-WATERPROOF-DPC", "Damp proofing", "m2", "Finishes", "WATERPROOFING"),

  ("FIN-STAIR-TILE", "Stair tile finish", "m2", "Finishes", "TILING"),
  ("FIN-STAIR-MARBLE", "Stair marble finish", "m2", "Finishes", "TILING"),
  ("FIN-STAIR-GRANITE", "Stair granite finish", "m2", "Finishes", "TILING"),

  ("FIN-BALCONY-TILE", "Balcony floor tile finish", "m2", "Finishes", "TILING"),
  ("FIN-TERRACE-TILE", "Terrace floor tile finish", "m2", "Finishes", "TILING"),
  ("FIN-PORCH-TILE", "Porch floor tile finish", "m2", "Finishes", "TILING"),

]

RULES = [

  ("ALL", "FLOOR", "FIN-FLOOR", None, True, False),
  ("ALL", "FLOOR", "FIN-SCREED", None, False, False),

  ("ALL", "SKIRTING", "FIN-SKIRT", None, True, False),

  ("ALL", "WALL", "FIN-PLASTER", None, True, False),
  ("ALL", "WALL", "FIN-PAINT", None, True, False),

  ("ALL", "CEILING", "FIN-CEIL-PLASTER", None, False, False),
  ("ALL", "CEILING", "FIN-CEIL-PAINT", None, False, False),

  ("STAIR", "STAIR", "FIN-STAIR-TILE", None, True, False),

  ("BATHROOM", "FLOOR", "FIN-FLOOR-TILE", None, True, True),
  ("BATHROOM", "WALL", "FIN-WALL-TILE-WET", None, True, True),
  ("BATHROOM", "SKIRTING", "FIN-SKIRT", None, True, True),
  ("BATHROOM", "DADO", "FIN-DADO", Decimal("2134"), True, False),
  ("BATHROOM", "WATERPROOFING", "FIN-WATERPROOF-WET", None, True, True),

  ("TOILET", "FLOOR", "FIN-FLOOR-TILE", None, True, True),
  ("TOILET", "WALL", "FIN-WALL-TILE-WET", None, True, True),
  ("TOILET", "SKIRTING", "FIN-SKIRT", None, True, True),
  ("TOILET", "DADO", "FIN-DADO", Decimal("2134"), True, False),
  ("TOILET", "WATERPROOFING", "FIN-WATERPROOF-WET", None, True, True),

  ("KITCHEN", "FLOOR", "FIN-FLOOR-TILE", None, True, True),
  ("KITCHEN", "DADO", "FIN-DADO", Decimal("600"), True, True),

  ("PANTRY", "FLOOR", "FIN-FLOOR-TILE", None, True, True),
  ("PANTRY", "DADO", "FIN-DADO", Decimal("600"), True, True),

  ("BALCONY", "FLOOR", "FIN-BALCONY-TILE", None, True, True),
  ("TERRACE", "FLOOR", "FIN-TERRACE-TILE", None, True, True),
  ("PORCH", "FLOOR", "FIN-PORCH-TILE", None, True, True),

  ("ROOF", "WATERPROOFING", "FIN-WATERPROOF-ROOF", None, True, True),
  ("TERRACE", "WATERPROOFING", "FIN-WATERPROOF-ROOF", None, True, True),

]

def finish_rule_rows(rule_set_id) -> list[FinishRule]:
  return [
    FinishRule(id=uuid4(), rule_set_id=rule_set_id, space_category=cat, surface=surface, work_item_code=code,
      height_mm=height, deduct_openings=deduct, priority=0, extra_config={"exclude": exclude, **PLACEHOLDER})
    for cat, surface, code, height, deduct, exclude in RULES
  ]

async def seed_finish_defaults(session: AsyncSession) -> None:
  for code, desc, unit, trade, mclass in WORK_ITEMS:
    exists = await session.execute(select(WorkItem).where(WorkItem.code == code, WorkItem.organization_id.is_(None)))
    if exists.scalar_one_or_none() is None:
      session.add(WorkItem(id=uuid4(), organization_id=None, code=code, description=desc, unit=unit, trade=trade,
        is_system=True, is_active=True, extra={"material_class": mclass, **PLACEHOLDER}))
  await session.flush()