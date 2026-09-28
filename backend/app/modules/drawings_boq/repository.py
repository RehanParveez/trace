from __future__ import annotations
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.models import BOQItem, BOQVersionStatus, BOQVersion, LabourRate, Drawing, DrawingElement, MaterialLibrary, MaterialNormalizationCache, MeasurementRuleSet, ElementTypeMapping, AssemblyRecipe, ModelAuditResult, BOQItem

class DrawingRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, drawing: Drawing) -> Drawing:
    self.session.add(drawing)
    await self.session.flush()
    return drawing

  async def get_by_id(self, drawing_id: UUID) -> Drawing | None:
    result = await self.session.execute(
      select(Drawing).where(Drawing.id == drawing_id)
    )
    return result.scalar_one_or_none()

  async def get_by_id_and_org(
    self,
    drawing_id: UUID,
    organization_id: UUID,
  ) -> Drawing | None:
    result = await self.session.execute(
      select(Drawing).where(
        Drawing.id == drawing_id,
        Drawing.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def list_by_project(
    self,
    organization_id: UUID,
    project_id: UUID,
  ) -> list[Drawing]:
    result = await self.session.execute(
      select(Drawing)
      .where(
        Drawing.organization_id == organization_id,
        Drawing.project_id == project_id,
      )
      .order_by(Drawing.created_at.desc())
    )
    return list(result.scalars().all())

  async def update(self, drawing: Drawing) -> Drawing:
    self.session.add(drawing)
    await self.session.flush()
    return drawing

class DrawingElementRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def bulk_create(
    self,
    elements: list[DrawingElement],
  ) -> list[DrawingElement]:
    self.session.add_all(elements)
    await self.session.flush()
    return elements

  async def list_by_drawing(
   self,
   drawing_id: UUID,
   organization_id: UUID,
  ) -> list[DrawingElement]:
   result = await self.session.execute(
    select(DrawingElement)
    .where(
      DrawingElement.drawing_id == drawing_id,
      DrawingElement.organization_id == organization_id,
    )
    .order_by(DrawingElement.ifc_type.asc())
  )
   return list(result.scalars().all())

class BOQVersionRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, boq_version: BOQVersion) -> BOQVersion:
    self.session.add(boq_version)
    await self.session.flush()
    return boq_version

  async def get_by_id_and_org(
    self,
    boq_version_id: UUID,
    organization_id: UUID,
  ) -> BOQVersion | None:
    result = await self.session.execute(
      select(BOQVersion).where(
        BOQVersion.id == boq_version_id,
        BOQVersion.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def list_by_project(
    self,
    organization_id: UUID,
    project_id: UUID,
  ) -> list[BOQVersion]:
    result = await self.session.execute(
      select(BOQVersion)
      .where(
        BOQVersion.organization_id == organization_id,
        BOQVersion.project_id == project_id,
      )
      .order_by(BOQVersion.created_at.desc())
    )
    return list(result.scalars().all())
  
  async def update(self, boq_version: BOQVersion) -> BOQVersion:
    self.session.add(boq_version)
    await self.session.flush()
    return boq_version

  async def supersede_active_for_project(
    self,
    organization_id: UUID,
    project_id: UUID,
    exclude_id: UUID,
  ) -> None:
    result = await self.session.execute(
      select(BOQVersion).where(
        BOQVersion.organization_id == organization_id,
        BOQVersion.project_id == project_id,
        BOQVersion.status == BOQVersionStatus.ACTIVE,
        BOQVersion.id != exclude_id,
      )
    )
    for version in result.scalars().all():
      version.status = BOQVersionStatus.SUPERSEDED
    await self.session.flush()

class BOQItemRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def bulk_create(self, items: list[BOQItem]) -> list[BOQItem]:
    self.session.add_all(items)
    await self.session.flush()
    return items

  async def create(self, item: BOQItem) -> BOQItem:
    self.session.add(item)
    await self.session.flush()
    return item
  
  async def get_by_id_and_org_for_update(
    self,
    item_id: UUID,
    organization_id: UUID,
  ) -> BOQItem | None:
    result = await self.session.execute(
      select(BOQItem)
      .where(
        BOQItem.id == item_id,
        BOQItem.organization_id == organization_id,
      )
      .with_for_update()
    )
    return result.scalar_one_or_none()

  async def list_by_version(
    self,
    boq_version_id: UUID,
    organization_id: UUID,
  ) -> list[BOQItem]:
    result = await self.session.execute(
      select(BOQItem)
      .where(BOQItem.boq_version_id == boq_version_id,
        BOQItem.organization_id == organization_id,
      )
      .order_by(BOQItem.material_name.asc())
    )
    return list(result.scalars().all())

  async def update(self, item: BOQItem) -> BOQItem:
    self.session.add(item)
    await self.session.flush()
    return item

class MaterialLibraryRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def get_by_raw_text(
    self,
    organization_id: UUID,
    raw_text: str,
  ) -> MaterialLibrary | None:
    result = await self.session.execute(
      select(MaterialLibrary).where(
        MaterialLibrary.organization_id == organization_id,
        MaterialLibrary.raw_text == raw_text,
      )
    )
    return result.scalar_one_or_none()

  async def list_by_org(
    self,
    organization_id: UUID,
  ) -> list[MaterialLibrary]:
    result = await self.session.execute(
      select(MaterialLibrary)
      .where(MaterialLibrary.organization_id == organization_id)
      .order_by(MaterialLibrary.normalized_name.asc())
    )
    return list(result.scalars().all())

  async def create(
    self,
    entry: MaterialLibrary,
  ) -> MaterialLibrary:
    self.session.add(entry)
    await self.session.flush()
    return entry
  
  async def get_by_id_and_org(
    self,
    entry_id: UUID,
    organization_id: UUID,
  ) -> MaterialLibrary | None:
    result = await self.session.execute(
      select(MaterialLibrary).where(
        MaterialLibrary.id == entry_id,
        MaterialLibrary.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def update(self, entry: MaterialLibrary) -> MaterialLibrary:
    self.session.add(entry)
    await self.session.flush()
    return entry

class MaterialNormalizationCacheRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def get_by_hash(
    self,
    input_hash: str,
    organization_id: UUID | None = None, 
  ) -> MaterialNormalizationCache | None:
    stmt = select(MaterialNormalizationCache).where(
    MaterialNormalizationCache.input_hash == input_hash
  )
    if organization_id is not None:
     stmt = stmt.where(
       MaterialNormalizationCache.organization_id == organization_id
     )
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()

  async def create(
    self,
    entry: MaterialNormalizationCache,
  ) -> MaterialNormalizationCache:
    self.session.add(entry)
    await self.session.flush()
    return entry
  
class LabourRateRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def list_by_org(self, organization_id: UUID) -> list[LabourRate]:
    result = await self.session.execute(
      select(LabourRate)
      .where(LabourRate.organization_id == organization_id)
      .order_by(LabourRate.trade.asc())
    )
    return list(result.scalars().all())

  async def get_by_id_and_org(
    self,
    rate_id: UUID,
    organization_id: UUID,
  ) -> LabourRate | None:
    result = await self.session.execute(
      select(LabourRate).where(
        LabourRate.id == rate_id,
        LabourRate.organization_id == organization_id,
      )
    )
    return result.scalar_one_or_none()

  async def get_by_trade(
    self,
    organization_id: UUID,
    trade: str,
  ) -> LabourRate | None:
    result = await self.session.execute(
      select(LabourRate).where(
        LabourRate.organization_id == organization_id,
        LabourRate.trade == trade,
      )
    )
    return result.scalar_one_or_none()

  async def create(self, rate: LabourRate) -> LabourRate:
    self.session.add(rate)
    await self.session.flush()
    return rate

  async def update(self, rate: LabourRate) -> LabourRate:
    self.session.add(rate)
    await self.session.flush()
    return rate
  
  async def get_latest_item_counts_by_project(
    self,
    organization_id: UUID,
  ) -> list[dict]:
    ranked = (
      select(
        BOQVersion.id,
        BOQVersion.project_id,
        func.row_number()
          .over(
            partition_by=BOQVersion.project_id,
            order_by=BOQVersion.created_at.desc(),
          )
          .label("rn"),
      )
      .where(BOQVersion.organization_id == organization_id)
      .subquery()
    )

    result = await self.session.execute(
      select(
        ranked.c.project_id,
        func.count(BOQItem.id).label("item_count"),
      )
      .select_from(ranked)
      .outerjoin(BOQItem, BOQItem.boq_version_id == ranked.c.id)
      .where(ranked.c.rn == 1)
      .group_by(ranked.c.project_id)
    )
    return [
      {"project_id": row.project_id, "latest_boq_item_count": row.item_count}
      for row in result.all()
    ]
  
  async def list_by_revision_group(self, organization_id: UUID, revision_group_id: UUID) -> list[Drawing]:
    result = await self.session.execute(
      select(Drawing)
      .where(Drawing.organization_id == organization_id, Drawing.revision_group_id == revision_group_id)
      .order_by(Drawing.created_at.asc())
    )
    return list(result.scalars().all())
  
class MeasurementRuleSetRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, rule_set: MeasurementRuleSet) -> MeasurementRuleSet:
    self.session.add(rule_set)
    await self.session.flush()
    return rule_set

  async def get_by_id(self, rule_set_id: UUID) -> MeasurementRuleSet | None:
    result = await self.session.execute(
      select(MeasurementRuleSet).where(MeasurementRuleSet.id == rule_set_id)
    )
    return result.scalar_one_or_none()

  async def get_by_code_and_org(
    self,
    code: str,
    organization_id: UUID | None,
  ) -> MeasurementRuleSet | None:
    stmt = select(MeasurementRuleSet).where(
      MeasurementRuleSet.code == code,
      MeasurementRuleSet.is_active.is_(True),
    )
    if organization_id is not None:
      stmt = stmt.where(
        (MeasurementRuleSet.organization_id == organization_id)
        | (MeasurementRuleSet.organization_id.is_(None))
      )
    else:
      stmt = stmt.where(MeasurementRuleSet.organization_id.is_(None))
    result = await self.session.execute(stmt.order_by(MeasurementRuleSet.organization_id.desc().nullslast()))
    return result.scalars().first()

  async def list_active(self, organization_id: UUID | None = None) -> list[MeasurementRuleSet]:
    stmt = select(MeasurementRuleSet).where(MeasurementRuleSet.is_active.is_(True))
    if organization_id is not None:
      stmt = stmt.where(
        (MeasurementRuleSet.organization_id == organization_id)
        | (MeasurementRuleSet.organization_id.is_(None))
      )
    else:
      stmt = stmt.where(MeasurementRuleSet.organization_id.is_(None))
    result = await self.session.execute(stmt.order_by(MeasurementRuleSet.code.asc()))
    return list(result.scalars().all())

  async def get_system_default(self, preferred_code: str = "PUNJAB_CSR") -> MeasurementRuleSet | None:
    result = await self.session.execute(
      select(MeasurementRuleSet).where(
        MeasurementRuleSet.code == preferred_code,
        MeasurementRuleSet.organization_id.is_(None),
        MeasurementRuleSet.is_system.is_(True),
        MeasurementRuleSet.is_active.is_(True),
      )
    )
    rule = result.scalar_one_or_none()
    if rule is not None:
      return rule
    # fallback
    result = await self.session.execute(
      select(MeasurementRuleSet).where(
        MeasurementRuleSet.organization_id.is_(None),
        MeasurementRuleSet.is_system.is_(True),
        MeasurementRuleSet.is_active.is_(True),
      ).order_by(MeasurementRuleSet.created_at.asc()).limit(1)
    )
    return result.scalar_one_or_none()

class ElementTypeMappingRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, mapping: ElementTypeMapping) -> ElementTypeMapping:
    self.session.add(mapping)
    await self.session.flush()
    return mapping

  async def list_by_rule_set(self, rule_set_id: UUID) -> list[ElementTypeMapping]:
    result = await self.session.execute(
      select(ElementTypeMapping)
      .where(ElementTypeMapping.rule_set_id == rule_set_id)
      .order_by(ElementTypeMapping.ifc_type.asc())
    )
    return list(result.scalars().all())

  async def get_by_rule_and_ifc(
    self,
    rule_set_id: UUID,
    ifc_type: str,
  ) -> ElementTypeMapping | None:
    result = await self.session.execute(
      select(ElementTypeMapping).where(
        ElementTypeMapping.rule_set_id == rule_set_id,
        ElementTypeMapping.ifc_type == ifc_type,
      )
    )
    return result.scalar_one_or_none()

class AssemblyRecipeRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, recipe: AssemblyRecipe) -> AssemblyRecipe:
    self.session.add(recipe)
    await self.session.flush()
    return recipe

  async def get_by_id(self, recipe_id: UUID) -> AssemblyRecipe | None:
    result = await self.session.execute(
      select(AssemblyRecipe).where(AssemblyRecipe.id == recipe_id)
    )
    return result.scalar_one_or_none()

  async def get_by_code(
    self,
    code: str,
    organization_id: UUID | None = None,
  ) -> AssemblyRecipe | None:
    stmt = select(AssemblyRecipe).where(
      AssemblyRecipe.code == code,
      AssemblyRecipe.is_active.is_(True),
    )
    if organization_id is not None:
      stmt = stmt.where(
        (AssemblyRecipe.organization_id == organization_id)
        | (AssemblyRecipe.organization_id.is_(None))
      )
    else:
      stmt = stmt.where(AssemblyRecipe.organization_id.is_(None))
    result = await self.session.execute(stmt.order_by(AssemblyRecipe.organization_id.desc().nullslast()))
    return result.scalars().first()

  async def list_active_for_org(self, organization_id: UUID | None = None) -> list[AssemblyRecipe]:
    stmt = (
      select(AssemblyRecipe)
      .where(AssemblyRecipe.is_active.is_(True))
      .options(
      
      )
    )
    if organization_id is not None:
      stmt = stmt.where(
        (AssemblyRecipe.organization_id == organization_id)
        | (AssemblyRecipe.organization_id.is_(None))
      )
    else:
      stmt = stmt.where(AssemblyRecipe.organization_id.is_(None))
    result = await self.session.execute(stmt.order_by(AssemblyRecipe.code.asc()))
    return list(result.scalars().all())

  async def get_matching_recipes(
    self,
    organization_id: UUID | None,
    ifc_type: str,
    properties: dict | None = None,
  ) -> list[AssemblyRecipe]:
    """
    Returns active recipes (system + org) whose trigger_ifc_types contain ifc_type
    and whose trigger_conditions match the given properties (simple equality checks).
    """
    candidates = await self.list_active_for_org(organization_id)
    matched: list[AssemblyRecipe] = []
    props = properties or {}
    for recipe in candidates:
      triggers = recipe.trigger_ifc_types or []
      if ifc_type not in triggers:
        continue
      conditions = recipe.trigger_conditions or {}
      ok = True
      for key, expected in conditions.items():
        actual = props.get(key)
        if actual is None:
          actual = props.get("properties", {}).get(key) if isinstance(props.get("properties"), dict) else None
        if actual is None or str(actual).lower() != str(expected).lower():
          try:
            if abs(float(actual) - float(expected)) > 1e-3:
              ok = False
              break
          except (TypeError, ValueError):
            ok = False
            break
      if ok:
        matched.append(recipe)
    return matched

class ModelAuditResultRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create(self, result: ModelAuditResult) -> ModelAuditResult:
    self.session.add(result)
    await self.session.flush()
    return result

  async def get_latest_by_drawing(
    self,
    drawing_id: UUID,
    organization_id: UUID,
  ) -> ModelAuditResult | None:
    result = await self.session.execute(
      select(ModelAuditResult)
      .where(
        ModelAuditResult.drawing_id == drawing_id,
        ModelAuditResult.organization_id == organization_id,
      )
      .order_by(ModelAuditResult.created_at.desc())
      .limit(1)
    )
    return result.scalar_one_or_none()

async def list_by_version_filtered(
  self,
  boq_version_id: UUID,
  organization_id: UUID,
  recipe_id: UUID | None = None,
  rule_set_id: UUID | None = None,
) -> list[BOQItem]:
  stmt = select(BOQItem).where(
    BOQItem.boq_version_id == boq_version_id,
    BOQItem.organization_id == organization_id,
  )
  if recipe_id is not None:
    stmt = stmt.where(BOQItem.recipe_id == recipe_id)
  if rule_set_id is not None:
    stmt = stmt.where(BOQItem.rule_set_id == rule_set_id)
  result = await self.session.execute(stmt.order_by(BOQItem.material_name.asc()))
  return list(result.scalars().all())