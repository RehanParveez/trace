from __future__ import annotations 
import asyncio 
from decimal import Decimal 
from uuid import uuid4 
from sqlalchemy import select 
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy.orm import selectinload 
from app.core.database import AsyncSessionLocal 
from app.modules.drawings_boq.models import LabourRate, MaterialLibrary, MeasurementRuleSet, AssemblyRecipe, AssemblyRecipeComponent, BOQItemType 
from app.modules.identity.enums import PermissionKey 
from app.modules.identity.models import Organization, Permission, Role 
from datetime import datetime, timezone
from app.shared.seed_utils import seed_module_permissions 
from app.modules.drawings_boq.permissions import DRAWINGS_BOQ_PERMISSIONS 
 
MATERIAL_ENTRIES = [ 
  { 
    "raw_text": "concrete grade 25", 
    "normalized_name": "Concrete Grade 25 (M25)", 
    "category": "Concrete", 
    "default_unit": "m3", 
    "default_rate": Decimal("18500.00"), 
  }, 
  { 
    "raw_text": "concrete grade 30", 
    "normalized_name": "Concrete Grade 30 (M30)", 
    "category": "Concrete", 
    "default_unit": "m3", 
    "default_rate": Decimal("19500.00"), 
  }, 
  { 
    "raw_text": "concrete gr45", 
    "normalized_name": "Concrete Grade 45 (M45)", 
    "category": "Concrete", 
    "default_unit": "m3", 
    "default_rate": Decimal("21500.00"), 
  }, 
  { 
    "raw_text": "steel rebar grade 60", 
    "normalized_name": "Steel Reinforcement Bar Grade 60", 
    "category": "Steel", 
    "default_unit": "kg", 
    "default_rate": Decimal("210.00"), 
  }, 
  { 
    "raw_text": "burnt clay brick", 
    "normalized_name": "Burnt Clay Brick (Standard)", 
    "category": "Masonry", 
    "default_unit": "unit", 
    "default_rate": Decimal("25.00"), 
  }, 
  { 
    "raw_text": "cement opc", 
    "normalized_name": "Ordinary Portland Cement", 
    "category": "Cement", 
    "default_unit": "kg", 
    "default_rate": Decimal("12.50"), 
  }, 
] 
 
LABOUR_RATE_ENTRIES = [ 
  { 
    "trade": "Labour Contractor — grey structure", 
    "unit": "Sft", 
    "rate": Decimal("550.00"), 
  }, 
  { 
    "trade": "Electrician — electrical works labour", 
    "unit": "Sft", 
    "rate": Decimal("30.00"), 
  }, 
  { 
    "trade": "Plumber — plumbing works labour", 
    "unit": "Sft", 
    "rate": Decimal("30.00"), 
  }, 
] 
 
async def seed_permissions( 
  session: AsyncSession, 
) -> dict[PermissionKey, Permission]: 
  permissions: dict[PermissionKey, Permission] = {} 
  for key, description in DRAWINGS_BOQ_PERMISSIONS.items():  
    result = await session.execute( 
      select(Permission).where(Permission.key == str(key)) 
    ) 
    permission = result.scalar_one_or_none() 
    if permission is None: 
      permission = Permission( 
        id=uuid4(), 
        key=str(key), 
        description=description,  
      ) 
      session.add(permission) 
      await session.flush() 
    permissions[key] = permission 
  return permissions 
 
async def grant_permissions_to_admin_roles( 
  session: AsyncSession, 
  permissions: dict[PermissionKey, Permission], 
) -> None: 
  result = await session.execute( 
    select(Role) 
    .where(Role.is_system.is_(True)) 
    .options(selectinload(Role.permissions)) 
  ) 
  admin_roles = list(result.scalars().unique()) 
 
  for role in admin_roles: 
    current_ids = {permission.id for permission in role.permissions} 
    for permission in permissions.values(): 
      if permission.id not in current_ids: 
        role.permissions.append(permission) 
 
  await session.flush() 
 
async def seed_material_library( 
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
      "Skipping material library seed: " 
      "no organization exists." 
    ) 
    return 
 
  for data in MATERIAL_ENTRIES: 
    existing = await session.execute( 
      select(MaterialLibrary).where( 
        MaterialLibrary.organization_id == organization.id, 
        MaterialLibrary.raw_text == data["raw_text"], 
      ) 
    ) 
    if existing.scalar_one_or_none() is None: 
      session.add( 
        MaterialLibrary( 
          id=uuid4(), 
          organization_id=organization.id, 
          raw_text=data["raw_text"], 
          normalized_name=data["normalized_name"], 
          category=data["category"], 
          default_unit=data["default_unit"], 
          default_rate=data["default_rate"], 
        ) 
      ) 
 
async def seed_labour_rates(session: AsyncSession) -> None: 
  organization_result = await session.execute( 
    select(Organization).order_by(Organization.created_at.asc()).limit(1) 
  ) 
  organization = organization_result.scalar_one_or_none() 
  if organization is None: 
    return 
   
  now = datetime.now(timezone.utc) 
   
  for data in LABOUR_RATE_ENTRIES: 
    existing = await session.execute( 
      select(LabourRate).where( 
        LabourRate.organization_id == organization.id, 
        LabourRate.trade == data["trade"], 
      ) 
    ) 
    if existing.scalar_one_or_none() is None: 
      session.add( 
        LabourRate( 
          id=uuid4(), 
          organization_id=organization.id, 
          trade=data["trade"], 
          unit=data["unit"], 
          rate=data["rate"], 
          created_at=now, 
          updated_at=now, 
        ) 
      ) 
 
async def seed_drawings_boq_rules(session: AsyncSession) -> None: 
  existing = await session.execute( 
    select(MeasurementRuleSet).where( 
      MeasurementRuleSet.code == "PUNJAB_CSR", 
      MeasurementRuleSet.organization_id.is_(None), 
    ) 
  ) 
  if existing.scalar_one_or_none() is None: 
    rule = MeasurementRuleSet( 
      id=uuid4(), 
      organization_id=None, 
      code="PUNJAB_CSR", 
      name="Punjab CSR (default)", 
      description="Default Pakistan / Punjab measurement conventions for BOQ generation.", 
      is_system=True, 
      is_active=True, 
      opening_deduction_threshold_m2=Decimal("0.5"), 
      wall_measurement_method="centre_line", 
      preferred_units={ 
        "area": "sft", 
        "volume": "cft", 
        "length": "rft", 
        "weight": "kg", 
        "count": "nos", 
      }, 
      waste_factors={ 
        "default": 1.05, 
        "brick": 1.05, 
        "brickwork": 1.05, 
        "concrete": 1.02, 
        "plaster": 1.10, 
        "paint": 1.08, 
        "steel": 1.03, 
        "formwork": 1.05, 
      }, 
      net_vs_gross_preference="net", 
      extra_config={"province": "Punjab", "csr_year": 2024}, 
    ) 
    session.add(rule) 
    await session.flush() 
 
  existing_g = await session.execute( 
    select(MeasurementRuleSet).where( 
      MeasurementRuleSet.code == "GENERIC_METRIC", 
      MeasurementRuleSet.organization_id.is_(None), 
    ) 
  ) 
  if existing_g.scalar_one_or_none() is None: 
    session.add( 
      MeasurementRuleSet( 
        id=uuid4(), 
        organization_id=None, 
        code="GENERIC_METRIC", 
        name="Generic Metric", 
        description="International metric fallback.", 
        is_system=True, 
        is_active=True, 
        opening_deduction_threshold_m2=Decimal("0.5"), 
        wall_measurement_method="centre_line", 
        preferred_units={"area": "m2", "volume": "m3", "length": "m", "weight": "kg", "count": "nos"}, 
        waste_factors={"default": 1.05}, 
        net_vs_gross_preference="net", 
        extra_config={}, 
      ) 
    ) 
    await session.flush() 
 
  async def _ensure_recipe(code: str, name: str, triggers: list, conditions: dict, components: list[dict]): 
    exists = await session.execute( 
      select(AssemblyRecipe).where( 
        AssemblyRecipe.code == code, 
        AssemblyRecipe.organization_id.is_(None), 
      ) 
    ) 
    if exists.scalar_one_or_none() is not None: 
      return 
    recipe = AssemblyRecipe( 
      id=uuid4(), 
      organization_id=None, 
      code=code, 
      name=name, 
      description=None, 
      trigger_ifc_types=triggers, 
      trigger_conditions=conditions, 
      is_system=True, 
      is_active=True, 
    ) 
    session.add(recipe) 
    await session.flush() 
    for idx, c in enumerate(components): 
      session.add( 
        AssemblyRecipeComponent( 
          id=uuid4(), 
          recipe_id=recipe.id, 
          sequence=idx, 
          work_item_code=c.get("work_item_code"), 
          description_template=c["description"], 
          unit=c["unit"], 
          quantity_factor=Decimal(str(c.get("factor", 1.0))), 
          quantity_formula=c.get("formula"), 
          category=c.get("category"), 
          item_type=BOQItemType(c.get("item_type", "MATERIAL")), 
          waste_factor=Decimal(str(c.get("waste", 1.0))), 
          is_optional=c.get("optional", False), 
        ) 
      ) 
    await session.flush() 
 
  await _ensure_recipe( 
    code="EXT_BRICK_WALL_230", 
    name="External 230 mm Brick Wall", 
    triggers=["IfcWall", "IfcWallStandardCase"], 
    conditions={}, 
    components=[ 
      {"description": "Brick masonry in {material}", "unit": "cft", "factor": 1.0, "waste": 1.05, "category": "Masonry"}, 
      {"description": "Internal plaster on {material}", "unit": "sft", "factor": 1.0, "waste": 1.10, "category": "Plaster"}, 
      {"description": "External plaster on {material}", "unit": "sft", "factor": 1.0, "waste": 1.10, "category": "Plaster"}, 
      {"description": "External paint on {material}", "unit": "sft", "factor": 1.0, "waste": 1.08, "category": "Paint"}, 
      {"description": "Scaffolding allowance for external wall", "unit": "sft", "factor": 1.0, "waste": 1.0, "category": "Scaffolding", "item_type": "CUSTOM"}, 
    ], 
  ) 
 
  await _ensure_recipe( 
    code="RCC_SLAB", 
    name="RCC Slab", 
    triggers=["IfcSlab"], 
    conditions={}, 
    components=[ 
      {"description": "RCC concrete in slab", "unit": "cft", "factor": 1.0, "waste": 1.02, "category": "Concrete"}, 
      {"description": "Formwork for slab soffit", "unit": "sft", "factor": 1.0, "waste": 1.05, "category": "Formwork"}, 
      {"description": "Curing of concrete slab", "unit": "sft", "factor": 1.0, "waste": 1.0, "category": "Curing", "item_type": "CUSTOM"}, 
    ], 
  ) 
 
  await _ensure_recipe( 
    code="INTERNAL_DOOR", 
    name="Internal Door", 
    triggers=["IfcDoor"], 
    conditions={}, 
    components=[ 
      {"description": "Door frame", "unit": "nos", "factor": 1.0, "waste": 1.0, "category": "Doors"}, 
      {"description": "Door shutter", "unit": "nos", "factor": 1.0, "waste": 1.0, "category": "Doors"}, 
      {"description": "Door hardware set", "unit": "nos", "factor": 1.0, "waste": 1.0, "category": "Hardware"}, 
      {"description": "Painting to door", "unit": "sft", "factor": 1.0, "waste": 1.08, "category": "Paint"}, 
    ], 
  ) 
 
  await _ensure_recipe( 
    code="RCC_COLUMN", 
    name="RCC Column", 
    triggers=["IfcColumn"], 
    conditions={}, 
    components=[ 
      {"description": "RCC concrete in column", "unit": "cft", "factor": 1.0, "waste": 1.02, "category": "Concrete"}, 
      {"description": "Formwork for column", "unit": "sft", "factor": 1.0, "waste": 1.05, "category": "Formwork"}, 
      {"description": "Curing of column", "unit": "sft", "factor": 1.0, "waste": 1.0, "category": "Curing", "item_type": "CUSTOM"}, 
    ], 
  ) 
  await session.flush() 
 
async def main(): 
  async with AsyncSessionLocal() as session: 
    await seed_module_permissions(session, DRAWINGS_BOQ_PERMISSIONS) 
    await seed_material_library(session) 
    await seed_labour_rates(session) 
    await seed_drawings_boq_rules(session) 
    await session.commit() 
  print( 
    "Drawings & BOQ module seeding completed successfully." 
  ) 
 
if __name__ == "__main__": 
  asyncio.run(main())