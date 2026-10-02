from __future__ import annotations
import copy
from app.core.exceptions import TraceException
from app.modules.drawings_boq.standards.repository import RuleSetBundle, StandardsRepository
from app.engine.measure.profile import RecipeComponentSpec, RecipeSpec, MappingSpec, OpeningRuleSpec, ReinforcementRuleSpec, ResolvedRuleProfile, WastageRuleSpec
from uuid import UUID, uuid4
from app.modules.drawings_boq.models import AssemblyRecipe, AssemblyRecipeComponent, ElementTypeMapping, MaterialWastageRule, MeasurementRuleSet, OpeningMeasurementRule, ReinforcementRule, WorkItem
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.audit.models import AuditAction, AuditEntityType
from app.modules.audit.service import AuditLogService
from app.modules.drawings_boq.repository import MeasurementRuleSetRepository
from app.modules.drawings_boq.standards.schemas import RecipeUpsertRequest, RuleSetCreateRequest, RuleSetDraftUpdateRequest, WorkItemCreateRequest, WorkItemUpdateRequest
from app.modules.drawings_boq.standards.validation import validate_bundle
from datetime import date, datetime, timezone
from sqlalchemy import delete
from decimal import Decimal
from app.engine.measure.formulas import CANONICAL_UNITS, check_component_units, get_formula

DEFAULT_RULE_CODE = "PUNJAB_CSR"
FALLBACK_RULE_CODE = "GENERIC_METRIC"
DEFAULT_TOLERANCES = {"touch_mm": 50, "snap_mm": 0.1}  

SCALAR_FIELDS = (
  "name", "description", "jurisdiction", "province", "city", "standard_name", "standard_edition",
  "effective_from", "effective_to", "convention_code", "wall_measurement_method",
  "net_vs_gross_preference", "preferred_units", "extra_config",
)

def _clone_row(model_cls, row, **overrides):
  data = {
    c.name: copy.deepcopy(getattr(row, c.name))
    for c in model_cls.__table__.columns
    if c.name not in ("id", "created_at", "updated_at")
  }
  data.update(overrides)
  data["id"] = uuid4()
  return model_cls(**data)

def _assert_unique(rows, key, label: str) -> None:
  seen = set()
  for row in rows:
    k = key(row)
    if k in seen:
      raise TraceException(f"Duplicate {label}: {k}", status_code=422, code="DUPLICATE_RULE_ROW")
    seen.add(k)

def build_profile(bundle: RuleSetBundle, *, conserves_volume: bool, work_items: dict[str, WorkItem]) -> ResolvedRuleProfile:
  rs = bundle.rule_set

  def material_class(code: str | None) -> str | None:
    wi = work_items.get(code) if code else None
    return (wi.extra or {}).get("material_class") if wi else None

  recipes = []
  for r in bundle.recipes:
    if not r.is_active:
      continue
    comps = tuple(
      RecipeComponentSpec(
        sequence=c.sequence, work_item_code=c.work_item_code, description_template=c.description_template,
        unit=c.unit, formula_code=c.quantity_formula_code, category=c.category, item_type=c.item_type,
        is_optional=c.is_optional, material_class=material_class(c.work_item_code),
      )
      for c in sorted(r.components, key=lambda c: c.sequence)
    )
    recipes.append(RecipeSpec(
      id=str(r.id), code=r.code, name=r.name,
      trigger_ifc_types=tuple(sorted(r.trigger_ifc_types or [])),
      trigger_conditions=dict(r.trigger_conditions or {}), components=comps,
    ))

  return ResolvedRuleProfile(
    rule_set_id=str(rs.id), code=rs.code, immutable_version=rs.immutable_version,
    content_hash=rs.content_hash, convention_code=rs.convention_code, conserves_volume=conserves_volume,
    jurisdiction=rs.jurisdiction, province=rs.province, standard_name=rs.standard_name,
    standard_edition=rs.standard_edition, wall_measurement_method=rs.wall_measurement_method,
    net_vs_gross_preference=(rs.net_vs_gross_preference or "net").lower(),
    preferred_units=dict(rs.preferred_units or {}),
    tolerances={**DEFAULT_TOLERANCES, **((rs.extra_config or {}).get("tolerances") or {})},
    
    opening_rules=tuple(sorted(
      (OpeningRuleSpec(r.element_scope, r.lower_area_m2, r.upper_area_m2, r.deduction_behavior,
        r.deduction_fraction, r.edge_behavior) for r in bundle.opening_rules),
      key=lambda s: (s.element_scope, s.lower_area_m2))),
    
    wastage_rules=tuple(sorted(
      (WastageRuleSpec(r.material_class.upper(), r.procurement_stage, r.factor) for r in bundle.wastage_rules),
      key=lambda s: (s.material_class, s.procurement_stage))),
    
    reinforcement_rules=tuple(sorted(
      (ReinforcementRuleSpec(r.element_scope, r.bar_role, r.lap_basis, r.lap_coefficient, dict(r.hook_rules or {}),
        dict(r.bend_rules or {}), r.dev_length_method, dict(r.splice_constraints or {}),
        dict(r.extra_config or {})) for r in bundle.reinforcement_rules),
      key=lambda s: (s.element_scope, s.bar_role))),
    
    mappings=tuple(sorted(
      (MappingSpec(m.ifc_type, m.work_item_code, m.default_category, m.quantity_source_preference,
        m.unit_override, m.confidence_base, (m.extra_mapping or {}).get("material_class")) for m in bundle.mappings),
      key=lambda s: s.ifc_type)),
    recipes=tuple(sorted(recipes, key=lambda s: s.code)),
  )

class StandardsService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = StandardsRepository(session)
    self.rule_sets = MeasurementRuleSetRepository(session)
    self.audit = AuditLogService(session)

  async def _visible(self, organization_id: UUID, rule_set_id: UUID) -> MeasurementRuleSet:
    rs = await self.repo.get_visible_rule_set(rule_set_id, organization_id)
    if rs is None:
      raise TraceException("Rule set not found.", status_code=404, code="RULESET_NOT_FOUND")
    return rs

  @staticmethod
  def _require_mutable(rs: MeasurementRuleSet, organization_id: UUID) -> None:
    if rs.organization_id is None or rs.is_system:
      raise TraceException("System rule sets are read-only. Clone it into your organisation first.",
        status_code=403, code="RULESET_SYSTEM_READONLY")
    if rs.organization_id != organization_id:
      raise TraceException("Rule set not found.", status_code=404, code="RULESET_NOT_FOUND")
    if rs.status != "DRAFT":
      raise TraceException("Published rule sets are immutable. Clone to create a new draft version.",
        status_code=409, code="RULESET_IMMUTABLE")

  async def _check_convention(self, code: str | None) -> None:
    if code and code not in await self.repo.conventions_by_code():
      raise TraceException(f"Unknown convention '{code}'.", status_code=422, code="CONVENTION_UNKNOWN")

  async def list_rule_sets(self, organization_id: UUID) -> list[MeasurementRuleSet]:
    return await self.repo.list_rule_sets(organization_id)

  async def get_detail(self, organization_id: UUID, rule_set_id: UUID) -> RuleSetBundle:
    await self._visible(organization_id, rule_set_id)
    return await self.repo.load_bundle(rule_set_id)

  async def _profile_from_bundle(self, bundle: RuleSetBundle) -> ResolvedRuleProfile:
    conventions = await self.repo.conventions_by_code()
    conv = conventions.get(bundle.rule_set.convention_code or "")
    items = await self.repo.work_item_index(bundle.rule_set.organization_id)
    return build_profile(bundle, conserves_volume=conv.conserves_volume if conv else True, work_items=items)

  async def profile_for_rule_set(self, rule_set_id: UUID) -> ResolvedRuleProfile:
    bundle = await self.repo.load_bundle(rule_set_id)
    if bundle is None:
      raise TraceException("Rule set not found.", status_code=404, code="RULESET_NOT_FOUND")
    return await self._profile_from_bundle(bundle)

  async def resolve_profile(self, organization_id: UUID | None, code: str | None = None,
    as_of: date | None = None) -> ResolvedRuleProfile:
    code = code or DEFAULT_RULE_CODE
    rs = (
      await self.rule_sets.get_by_code_and_org(code, organization_id, as_of)
      or await self.rule_sets.get_system_default(code)
      or await self.rule_sets.get_system_default(FALLBACK_RULE_CODE)
    )
    if rs is None:
      raise TraceException("No active rule set found. Run the standards seed.", status_code=404, code="RULESET_NOT_FOUND")
    return await self.profile_for_rule_set(rs.id)

  async def create_draft(self, organization_id: UUID, user_id: UUID, payload: RuleSetCreateRequest) -> RuleSetBundle:
    await self._check_convention(payload.convention_code)
    version = await self.repo.max_version(organization_id, payload.code) + 1
    rs = MeasurementRuleSet(
      id=uuid4(), organization_id=organization_id, is_system=False, is_active=False,
      status="DRAFT", immutable_version=version, **payload.model_dump(),
    )
    await self.rule_sets.create(rs)

    rule_set_id = rs.id
    rule_set_code = rs.code
    rule_set_version = rs.immutable_version

    await self.session.commit()

    await self.audit.log(
      organization_id, user_id, AuditEntityType.RULE_SET, rule_set_id, AuditAction.CREATE,
      f'Created rule set draft "{rule_set_code}" v{rule_set_version}',
    )
    return await self.repo.load_bundle(rule_set_id)

  async def update_draft(self, organization_id: UUID, user_id: UUID, rule_set_id: UUID,
    payload: RuleSetDraftUpdateRequest) -> RuleSetBundle:
    rs = await self._visible(organization_id, rule_set_id)
    self._require_mutable(rs, organization_id)

    if "convention_code" in payload.model_fields_set:
      await self._check_convention(payload.convention_code)
    for key in SCALAR_FIELDS:
      if key in payload.model_fields_set and getattr(payload, key) is not None:
        setattr(rs, key, getattr(payload, key))

    if payload.opening_rules is not None:
      _assert_unique(payload.opening_rules, lambda r: (r.element_scope, r.lower_area_m2), "opening rule")
      await self.session.execute(delete(OpeningMeasurementRule).where(OpeningMeasurementRule.rule_set_id == rs.id))
      self.session.add_all([OpeningMeasurementRule(id=uuid4(), rule_set_id=rs.id, **r.model_dump()) for r in payload.opening_rules])
    if payload.wastage_rules is not None:
      rows = [{**r.model_dump(), "material_class": r.material_class.upper()} for r in payload.wastage_rules]
      _assert_unique(rows, lambda r: (r["material_class"], r["procurement_stage"]), "wastage rule")
      await self.session.execute(delete(MaterialWastageRule).where(MaterialWastageRule.rule_set_id == rs.id))
      self.session.add_all([MaterialWastageRule(id=uuid4(), rule_set_id=rs.id, **r) for r in rows])
    if payload.reinforcement_rules is not None:
      _assert_unique(payload.reinforcement_rules, lambda r: (r.element_scope, r.bar_role), "reinforcement rule")
      await self.session.execute(delete(ReinforcementRule).where(ReinforcementRule.rule_set_id == rs.id))
      self.session.add_all([ReinforcementRule(id=uuid4(), rule_set_id=rs.id, **r.model_dump()) for r in payload.reinforcement_rules])
    if payload.mappings is not None:
      _assert_unique(payload.mappings, lambda r: r.ifc_type, "element type mapping")
      await self.session.execute(delete(ElementTypeMapping).where(ElementTypeMapping.rule_set_id == rs.id))
      self.session.add_all([ElementTypeMapping(id=uuid4(), rule_set_id=rs.id, **r.model_dump()) for r in payload.mappings])

    await self.session.flush()
    captured_id = rs.id
    captured_code = rs.code
    captured_version = rs.immutable_version

    await self.session.commit()

    await self.audit.log(
      organization_id, user_id, AuditEntityType.RULE_SET, captured_id, AuditAction.UPDATE,
      f'Updated rule set draft "{captured_code}" v{captured_version}',
    )
    return await self.repo.load_bundle(captured_id)

  async def upsert_recipe(self, organization_id: UUID, user_id: UUID, rule_set_id: UUID,
    payload: RecipeUpsertRequest) -> RuleSetBundle:
    rs = await self._visible(organization_id, rule_set_id)
    self._require_mutable(rs, organization_id)

    _assert_unique(payload.components, lambda c: c.sequence, "recipe component sequence")
    for c in payload.components:
      problems = check_component_units(c.quantity_formula_code, c.unit)
      if problems:
        raise TraceException(problems[0][1], status_code=422, code=problems[0][0])

    await self.session.execute(
      delete(AssemblyRecipe).where(AssemblyRecipe.rule_set_id == rs.id, AssemblyRecipe.code == payload.code)
    )
    recipe = AssemblyRecipe(
      id=uuid4(), organization_id=organization_id, rule_set_id=rs.id, code=payload.code, name=payload.name,
      description=payload.description, trigger_ifc_types=list(payload.trigger_ifc_types),
      trigger_conditions=dict(payload.trigger_conditions), is_system=False, is_active=True,
    )
    
    self.session.add(recipe)
    await self.session.flush()
    for c in payload.components:
      spec = get_formula(c.quantity_formula_code)
      self.session.add(AssemblyRecipeComponent(
        id=uuid4(), recipe_id=recipe.id, sequence=c.sequence, work_item_code=c.work_item_code,
        description_template=c.description_template, unit=c.unit, quantity_formula_code=c.quantity_formula_code,
        output_unit=spec.output_unit, category=c.category, item_type=c.item_type,
        waste_factor=Decimal("1.0"), is_optional=c.is_optional,
      ))
    await self.session.flush()
    
    captured_id = rs.id
    captured_code = rs.code
    captured_version = rs.immutable_version

    await self.session.commit()
    await self.audit.log(
      organization_id, user_id, AuditEntityType.RULE_SET, captured_id, AuditAction.UPDATE,
      f'Saved recipe "{payload.code}" on rule set "{captured_code}" v{captured_version}',
    )
    return await self.repo.load_bundle(captured_id)

  async def delete_recipe(self, organization_id: UUID, user_id: UUID, rule_set_id: UUID, recipe_id: UUID) -> None:
    rs = await self._visible(organization_id, rule_set_id)
    self._require_mutable(rs, organization_id)
    await self.session.execute(
      delete(AssemblyRecipe).where(AssemblyRecipe.id == recipe_id, AssemblyRecipe.rule_set_id == rs.id)
    )

    captured_id = rs.id
    captured_code = rs.code
    captured_version = rs.immutable_version

    await self.session.commit()

    await self.audit.log(
      organization_id, user_id, AuditEntityType.RULE_SET, captured_id, AuditAction.UPDATE,
      f'Removed a recipe from rule set "{captured_code}" v{captured_version}',
    )

  async def clone(self, organization_id: UUID, user_id: UUID, rule_set_id: UUID) -> RuleSetBundle:
    src = await self._visible(organization_id, rule_set_id)
    src_bundle = await self.repo.load_bundle(src.id)
    version = await self.repo.max_version(organization_id, src.code) + 1

    new = _clone_row(
      MeasurementRuleSet, src, organization_id=organization_id, is_system=False, is_active=False,
      status="DRAFT", immutable_version=version, published_at=None, published_by_user_id=None,
      content_hash=None, supersedes_rule_set_id=src.id,
    )
    self.session.add(new)
    await self.session.flush()

    for model, rows in (
      (OpeningMeasurementRule, src_bundle.opening_rules), (MaterialWastageRule, src_bundle.wastage_rules),
      (ReinforcementRule, src_bundle.reinforcement_rules), (ElementTypeMapping, src_bundle.mappings),
    ):
      self.session.add_all([_clone_row(model, r, rule_set_id=new.id) for r in rows])
    for recipe in src_bundle.recipes:
      new_recipe = _clone_row(AssemblyRecipe, recipe, organization_id=organization_id, rule_set_id=new.id, is_system=False)
      self.session.add(new_recipe)
      await self.session.flush()
      self.session.add_all([_clone_row(AssemblyRecipeComponent, c, recipe_id=new_recipe.id) for c in recipe.components])
    await self.session.flush()

    new_id = new.id
    src_code = src.code
    src_version = src.immutable_version

    await self.session.commit()

    await self.audit.log(
      organization_id, user_id, AuditEntityType.RULE_SET, new_id, AuditAction.CREATE,
      f'Cloned rule set "{src_code}" v{src_version} to draft v{version}',
    )
    return await self.repo.load_bundle(new_id)

  async def _validate_bundle(self, bundle: RuleSetBundle) -> list[dict]:
    items = await self.repo.work_item_index(bundle.rule_set.organization_id)
    return validate_bundle(
      rule_set=bundle.rule_set, opening_rules=bundle.opening_rules, wastage_rules=bundle.wastage_rules,
      reinforcement_rules=bundle.reinforcement_rules, mappings=bundle.mappings, recipes=bundle.recipes,
      work_item_units={code: wi.unit for code, wi in items.items()},
      known_conventions=set((await self.repo.conventions_by_code()).keys()),
    )

  async def validate(self, organization_id: UUID, rule_set_id: UUID) -> list[dict]:
    await self._visible(organization_id, rule_set_id)
    return await self._validate_bundle(await self.repo.load_bundle(rule_set_id))

  async def _publish_core(self, rs: MeasurementRuleSet, actor_user_id: UUID | None) -> list[dict]:
    bundle = await self.repo.load_bundle(rs.id)
    issues = await self._validate_bundle(bundle)
    errors = [i for i in issues if i["severity"] == "error"]
    if errors:
      raise TraceException(
        "Rule set failed validation: " + "; ".join(i["message"] for i in errors[:5]),
        status_code=422, code="RULESET_INVALID",
      )

    content_hash = (await self._profile_from_bundle(bundle)).content_fingerprint()
    previous = await self.repo.get_active_exact(rs.organization_id, rs.code)
    if previous is not None and previous.id != rs.id:
      if previous.content_hash == content_hash:
        issues.append({"code": "NO_CHANGES_FROM_ACTIVE", "severity": "warning", "ref": None,
          "message": "Content is identical to the currently active version."})
      previous.status = "SUPERSEDED"
      previous.is_active = False
      await self.session.flush()

    rs.content_hash = content_hash
    rs.published_at = datetime.now(timezone.utc)
    rs.published_by_user_id = actor_user_id
    rs.status = "ACTIVE"
    rs.is_active = True
    await self.session.flush()
    return [i for i in issues if i["severity"] != "error"]

  async def publish(self, organization_id: UUID, user_id: UUID, rule_set_id: UUID) -> tuple[MeasurementRuleSet, list[dict]]:
    rs = await self._visible(organization_id, rule_set_id)
    self._require_mutable(rs, organization_id)
    warnings = await self._publish_core(rs, user_id)
    captured_id = rs.id
    captured_code = rs.code
    captured_version = rs.immutable_version
    await self.session.commit()
    
    await self.audit.log(
      organization_id, user_id, AuditEntityType.RULE_SET, captured_id, AuditAction.UPDATE,
      f'Published rule set "{captured_code}" v{captured_version}',
    )

    published = await self._visible(organization_id, captured_id)
    return published, warnings

  async def list_work_items(self, organization_id: UUID) -> list[WorkItem]:
    return await self.repo.list_work_items(organization_id)

  @staticmethod
  def _check_work_item(unit: str | None, formula_code: str | None) -> None:
    if unit is not None and unit not in CANONICAL_UNITS:
      raise TraceException(f"Unit must be one of {sorted(CANONICAL_UNITS)}.", status_code=422, code="WORK_ITEM_UNIT_NOT_CANONICAL")
    if formula_code:
      spec = get_formula(formula_code)
      if spec is None:
        raise TraceException(f"Unknown formula code '{formula_code}'.", status_code=422, code="FORMULA_UNKNOWN")
      if unit is not None and spec.output_unit != unit:
        raise TraceException(f"Formula {formula_code} outputs '{spec.output_unit}', not '{unit}'.", status_code=422, code="RECIPE_UNIT_MISMATCH")

  async def create_work_item(self, organization_id: UUID, user_id: UUID, payload: WorkItemCreateRequest) -> WorkItem:
    self._check_work_item(payload.unit, payload.default_formula_code)
    if await self.repo.get_work_item_by_code(organization_id, payload.code) is not None:
      raise TraceException("A work item with this code already exists.", status_code=409, code="WORK_ITEM_ALREADY_EXISTS")
    item = WorkItem(
      id=uuid4(),
      organization_id=organization_id,
      is_system=False,
      is_active=True,
      **payload.model_dump(),
    )
    self.session.add(item)
    await self.session.flush()
    item_id = item.id
    item_code = item.code
    await self.session.commit()

    await self.audit.log(
      organization_id, user_id, AuditEntityType.RULE_SET, item_id, AuditAction.CREATE,
      f'Created work item "{item_code}"',
    )
    return await self.repo.get_work_item(item_id, organization_id)

  async def update_work_item(self, organization_id: UUID, user_id: UUID, work_item_id: UUID,
    payload: WorkItemUpdateRequest) -> WorkItem:
    item = await self.repo.get_work_item(work_item_id, organization_id)
    if item is None:
      raise TraceException("Work item not found.", status_code=404, code="WORK_ITEM_NOT_FOUND")
    if item.organization_id is None or item.is_system:
      raise TraceException("System work items are read-only.", status_code=403, code="WORK_ITEM_SYSTEM_READONLY")
    self._check_work_item(item.unit, payload.default_formula_code)

    for key, value in payload.model_dump(exclude_unset=True).items():
      if value is None and key in ("description", "is_active", "extra"):
        continue
      setattr(item, key, value)
    await self.session.flush()

    item_id = item.id
    item_code = item.code

    await self.session.commit()
    await self.audit.log(
      organization_id, user_id, AuditEntityType.RULE_SET, item_id, AuditAction.UPDATE,
      f'Updated work item "{item_code}"',
    )
    return await self.repo.get_work_item(item_id, organization_id)