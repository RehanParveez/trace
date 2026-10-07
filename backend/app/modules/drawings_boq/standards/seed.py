from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.standards.service import StandardsService
from app.modules.drawings_boq.standards.seed_data import CONVENTIONS, MAPPINGS, OPENING_THRESHOLD_M2, PLACEHOLDER, PROFILES, RECIPES, REBAR_RULES, WASTAGE_FULL, WASTAGE_MIN, WORK_ITEMS
from app.modules.drawings_boq.models import (MeasurementConvention, AssemblyRecipe, AssemblyRecipeComponent, ElementTypeMapping, MaterialWastageRule, MeasurementRuleSet,
  OpeningMeasurementRule, ReinforcementRule, WorkItem,
)
from decimal import Decimal
from uuid import uuid4
from app.engine.measure.formulas import FORMULAS
from sqlalchemy import select
from app.modules.drawings_boq.models import FinishRule
from app.modules.drawings_boq.finish_seed import finish_rule_rows, seed_finish_defaults
from app.modules.drawings_boq.rebar.rebar_seed import estimate_rule_rows

async def _missing_defaults(session: AsyncSession, rule_set_id) -> bool:
  has_finish = (await session.execute(select(FinishRule.id).where(FinishRule.rule_set_id == rule_set_id).limit(1))).first()
  has_estimate = (await session.execute(select(ReinforcementRule.id).where(
    ReinforcementRule.rule_set_id == rule_set_id, ReinforcementRule.bar_role == "ESTIMATE").limit(1))).first()
  return has_finish is None or has_estimate is None

async def seed_standards(session: AsyncSession) -> dict:
  svc = StandardsService(session)
  report = {"conventions": 0, "work_items": 0, "rule_sets": []}
  await seed_finish_defaults(session)

  existing_conventions = await svc.repo.conventions_by_code()
  for c in CONVENTIONS:
    if c["code"] not in existing_conventions:
      session.add(MeasurementConvention(id=uuid4(), is_system=True, is_active=True, **c))
      report["conventions"] += 1
  await session.flush()

  index = await svc.repo.work_item_index(None)
  for code, description, unit, trade, material_class in WORK_ITEMS:
    if code not in index:
      session.add(WorkItem(id=uuid4(), organization_id=None, code=code, description=description, unit=unit,
      trade=trade, is_system=True, is_active=True, extra={"material_class": material_class}))
      report["work_items"] += 1
  await session.flush()

  for spec in PROFILES:
    current = await svc.rule_sets.get_by_code_and_org(spec["code"], None)
    if current is not None and current.convention_code and not (spec["full"] and await _missing_defaults(session, current.id)):
      continue
    version = await svc.repo.max_version(None, spec["code"]) + 1
    rs = MeasurementRuleSet(
      id=uuid4(), organization_id=None, code=spec["code"], name=spec["name"], description=spec["description"],
      jurisdiction=spec["jurisdiction"], province=spec["province"], standard_name=spec["standard_name"],
      convention_code="FRAME_MONOLITHIC_A", is_system=True, is_active=False, status="DRAFT",
      immutable_version=version, opening_deduction_threshold_m2=OPENING_THRESHOLD_M2,
      wall_measurement_method="centre_line", net_vs_gross_preference="net",
      preferred_units=dict(spec.get("preferred_units") or {}),
    )
    session.add(rs)
    await session.flush()

    session.add_all([
      OpeningMeasurementRule(id=uuid4(), rule_set_id=rs.id, element_scope="ALL", lower_area_m2=Decimal("0"),
        upper_area_m2=OPENING_THRESHOLD_M2, deduction_behavior="IGNORE"),
      OpeningMeasurementRule(id=uuid4(), rule_set_id=rs.id, element_scope="ALL", lower_area_m2=OPENING_THRESHOLD_M2,
        upper_area_m2=None, deduction_behavior="DEDUCT"),
    ])
    for material_class, factor in (WASTAGE_FULL if spec["full"] else WASTAGE_MIN):
      session.add(MaterialWastageRule(id=uuid4(), rule_set_id=rs.id, material_class=material_class,
        procurement_stage="SITE", factor=Decimal(factor), justification=PLACEHOLDER))
    for ifc_type, work_item_code, category, material_class in MAPPINGS:
      session.add(ElementTypeMapping(id=uuid4(), rule_set_id=rs.id, ifc_type=ifc_type, work_item_code=work_item_code,
        default_category=category, extra_mapping={"material_class": material_class}))
    if spec["full"]:
      session.add_all([
        ReinforcementRule(id=uuid4(), rule_set_id=rs.id,
          stock_length_mm=(Decimal(str(r["splice_constraints"]["stock_length_m"])) * 1000
            if (r.get("splice_constraints") or {}).get("stock_length_m") else None),
          **r)
        for r in REBAR_RULES
      ])
      session.add_all(estimate_rule_rows(rs.id))
      session.add_all(finish_rule_rows(rs.id))
      await session.flush()
      for recipe in RECIPES:
        row = AssemblyRecipe(id=uuid4(), organization_id=None, rule_set_id=rs.id, code=recipe["code"],
        name=recipe["name"], trigger_ifc_types=recipe["triggers"], is_system=True, is_active=True)
        session.add(row)
        await session.flush()
        for seq, wi_code, template, unit, formula, category, optional in recipe["components"]:
          session.add(AssemblyRecipeComponent(
            id=uuid4(), recipe_id=row.id, sequence=seq, work_item_code=wi_code, description_template=template,
            unit=unit, quantity_formula_code=formula, output_unit=FORMULAS[formula].output_unit, category=category,
            item_type="MATERIAL", waste_factor=Decimal("1.0"), is_optional=optional))
    await session.flush()

    await svc._publish_core(rs, actor_user_id=None)
    report["rule_sets"].append(f'{spec["code"]} v{version}')

  await session.commit()
  return report