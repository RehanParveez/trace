from __future__ import annotations
from dataclasses import dataclass
from app.modules.drawings_boq.models import MeasurementRuleSet, OpeningMeasurementRule, MaterialWastageRule, ReinforcementRule, AssemblyRecipe, ElementTypeMapping, MeasurementConvention, WorkItem
from sqlalchemy import select, func, or_
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

@dataclass
class RuleSetBundle:
  rule_set: MeasurementRuleSet
  opening_rules: list[OpeningMeasurementRule]
  wastage_rules: list[MaterialWastageRule]
  reinforcement_rules: list[ReinforcementRule]
  mappings: list[ElementTypeMapping]
  recipes: list[AssemblyRecipe]

def _org_clause(column, organization_id: UUID | None):
  return column.is_(None) if organization_id is None else column == organization_id

class StandardsRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def get_visible_rule_set(self, rule_set_id: UUID, organization_id: UUID) -> MeasurementRuleSet | None:
    result = await self.session.execute(
      select(MeasurementRuleSet).where(
        MeasurementRuleSet.id == rule_set_id,
        or_(MeasurementRuleSet.organization_id.is_(None), MeasurementRuleSet.organization_id == organization_id),
      )
    )
    return result.scalar_one_or_none()

  async def list_rule_sets(self, organization_id: UUID) -> list[MeasurementRuleSet]:
    result = await self.session.execute(
      select(MeasurementRuleSet)
      .where(or_(MeasurementRuleSet.organization_id.is_(None), MeasurementRuleSet.organization_id == organization_id))
      .order_by(MeasurementRuleSet.code.asc(), MeasurementRuleSet.immutable_version.desc())
    )
    return list(result.scalars().all())

  async def max_version(self, organization_id: UUID | None, code: str) -> int:
    result = await self.session.execute(
      select(func.max(MeasurementRuleSet.immutable_version)).where(
        MeasurementRuleSet.code == code,
        _org_clause(MeasurementRuleSet.organization_id, organization_id),
      )
    )
    return int(result.scalar_one_or_none() or 0)

  async def get_active_exact(self, organization_id: UUID | None, code: str) -> MeasurementRuleSet | None:
    result = await self.session.execute(
      select(MeasurementRuleSet).where(
        MeasurementRuleSet.code == code,
        MeasurementRuleSet.status == "ACTIVE",
        _org_clause(MeasurementRuleSet.organization_id, organization_id),
      )
    )
    return result.scalar_one_or_none()

  async def load_bundle(self, rule_set_id: UUID) -> RuleSetBundle | None:
    rule_set = (await self.session.execute(
      select(MeasurementRuleSet).where(MeasurementRuleSet.id == rule_set_id)
    )).scalar_one_or_none()
    if rule_set is None:
      return None

    async def _all(model, *order):
      res = await self.session.execute(select(model).where(model.rule_set_id == rule_set_id).order_by(*order))
      return list(res.scalars().all())

    recipes = (await self.session.execute(
      select(AssemblyRecipe)
      .where(AssemblyRecipe.rule_set_id == rule_set_id)
      .options(selectinload(AssemblyRecipe.components))
      .order_by(AssemblyRecipe.code.asc())
    )).scalars().all()

    return RuleSetBundle(
      rule_set=rule_set,
      opening_rules=await _all(OpeningMeasurementRule, OpeningMeasurementRule.element_scope, OpeningMeasurementRule.lower_area_m2),
      wastage_rules=await _all(MaterialWastageRule, MaterialWastageRule.material_class, MaterialWastageRule.procurement_stage),
      reinforcement_rules=await _all(ReinforcementRule, ReinforcementRule.element_scope, ReinforcementRule.bar_role),
      mappings=await _all(ElementTypeMapping, ElementTypeMapping.ifc_type),
      recipes=list(recipes),
    )

  async def conventions_by_code(self) -> dict[str, MeasurementConvention]:
    result = await self.session.execute(select(MeasurementConvention).where(MeasurementConvention.is_active.is_(True)))
    return {c.code: c for c in result.scalars().all()}

  async def list_work_items(self, organization_id: UUID | None) -> list[WorkItem]:
    stmt = select(WorkItem).where(WorkItem.is_active.is_(True))
    if organization_id is None:
      stmt = stmt.where(WorkItem.organization_id.is_(None))
    else:
      stmt = stmt.where(or_(WorkItem.organization_id.is_(None), WorkItem.organization_id == organization_id))
    result = await self.session.execute(stmt.order_by(WorkItem.code.asc()))
    return list(result.scalars().all())

  async def work_item_index(self, organization_id: UUID | None) -> dict[str, WorkItem]:
    """code -> WorkItem; an organisation's own row overrides the system row."""
    rows = await self.list_work_items(organization_id)
    index: dict[str, WorkItem] = {}
    for row in sorted(rows, key=lambda r: r.organization_id is not None):
      index[row.code] = row
    return index

  async def get_work_item(self, work_item_id: UUID, organization_id: UUID) -> WorkItem | None:
    result = await self.session.execute(
      select(WorkItem).where(
        WorkItem.id == work_item_id,
        or_(WorkItem.organization_id.is_(None), WorkItem.organization_id == organization_id),
      )
    )
    return result.scalar_one_or_none()

  async def get_work_item_by_code(self, organization_id: UUID, code: str) -> WorkItem | None:
    result = await self.session.execute(
      select(WorkItem).where(WorkItem.organization_id == organization_id, WorkItem.code == code)
    )
    return result.scalar_one_or_none()