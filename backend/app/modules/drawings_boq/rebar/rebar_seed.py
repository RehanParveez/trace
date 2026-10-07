from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.models import BarSize, MeasurementRuleSet, RebarShape, ReinforcementRule
from decimal import Decimal
import asyncio
from uuid import uuid4
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.dependencies.tenancy import scope_session_as_platform_admin

ASTM = [("#3", "9.525", "0.560"), ("#4", "12.700", "0.994"), ("#5", "15.875", "1.552"), ("#6", "19.050", "2.235"),
  ("#7", "22.225", "3.042"), ("#8", "25.400", "3.973"), ("#9", "28.575", "5.060"), ("#10", "32.258", "6.404"),
  ("#11", "35.814", "7.907")]
METRIC = [("8", "8", "0.395"), ("10", "10", "0.617"), ("12", "12", "0.888"), ("16", "16", "1.579"), ("20", "20", "2.466"),
  ("25", "25", "3.853"), ("32", "32", "6.313")]
SHAPES = [
  ("STRAIGHT", "Straight bar", ["A"], [], 0),
  ("HOOKED", "Straight bar with hooks at both ends", ["A"], [], 2),
  ("L_BAR", "L-shaped bar", ["A", "B"], [90], 0),
  ("U_BAR", "U-shaped bar", ["A", "B", "C"], [90, 90], 0),
  ("STIRRUP_RECT", "Rectangular stirrup, 135 degree hooks", ["A", "B", "A", "B"], [90, 90, 90, 135, 135], 2),
]
PLACEHOLDER = "PLACEHOLDER - confirm with QS"
ESTIMATES = {"SLAB": 90, "BEAM": 150, "COLUMN": 200, "FOOTING": 80} 

async def seed_rebar_defaults(session: AsyncSession) -> None:
  for standard, rows in (("ASTM A615", ASTM), ("METRIC", METRIC)):
    for designation, dia, kg in rows:
      exists = await session.execute(select(BarSize.id).where(BarSize.organization_id.is_(None), BarSize.standard == standard,
        BarSize.designation == designation, BarSize.grade == "ALL"))
      if exists.first() is None:
        session.add(BarSize(id=uuid4(), organization_id=None, standard=standard, designation=designation, grade="ALL",
          nominal_dia_mm=Decimal(dia), unit_weight_kg_m=Decimal(kg), is_system=True, is_active=True))
        
  for code, name, segments, bends, hooks in SHAPES:
    exists = await session.execute(select(RebarShape.id).where(RebarShape.organization_id.is_(None), RebarShape.code == code))
    if exists.first() is None:
      session.add(RebarShape(id=uuid4(), organization_id=None, code=code, name=name, description=PLACEHOLDER,
        standard="TRACE-DEFAULT", segments=segments, bend_spec=bends, bend_count=len(bends), hook_ends=hooks,
        is_system=True, is_active=True))
  await session.flush()
  rule_sets = (await session.execute(select(MeasurementRuleSet).where(
    MeasurementRuleSet.code.like("PUNJAB%"), MeasurementRuleSet.published_at.is_(None)))).scalars().all()
  
  for rs in rule_sets:
    await apply_rebar_rules(session, rs)

async def apply_rebar_rules(session: AsyncSession, rs: MeasurementRuleSet) -> None:
    rules = (await session.execute(select(ReinforcementRule).where(ReinforcementRule.rule_set_id == rs.id))).scalars().all()
    changed = False
    for r in rules:
      stock_m = (r.splice_constraints or {}).get("stock_length_m")
      if getattr(r, "stock_length_mm", None) is None and stock_m:
        r.stock_length_mm = Decimal(str(stock_m)) * 1000
        changed = True
        
    await session.flush()

def estimate_rule_rows(rule_set_id) -> list[ReinforcementRule]:
  return [
    ReinforcementRule(id=uuid4(), rule_set_id=rule_set_id, element_scope=scope, bar_role="ESTIMATE",
      extra_config={"kg_per_m3": intensity, "assumed_dia_mm": 12, "confidence": "0.5", "status": PLACEHOLDER})
    for scope, intensity in ESTIMATES.items()
  ]

async def main() -> None:
  async with AsyncSessionLocal() as session:
    await scope_session_as_platform_admin(session)
    await seed_rebar_defaults(session)
    await session.commit()
  print("Rebar reference data seeded.")

if __name__ == "__main__":
  asyncio.run(main())