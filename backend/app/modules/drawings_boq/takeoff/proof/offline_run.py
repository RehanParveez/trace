from __future__ import annotations
import time
from uuid import UUID, uuid5
from types import SimpleNamespace
from app.modules.drawings_boq.models import ReinforcementRule, MeasurementRuleSet, AssemblyRecipe, AssemblyRecipeComponent, ElementTypeMapping, MaterialWastageRule, OpeningMeasurementRule
from app.modules.drawings_boq.standards import seed_data as SD
from dataclasses import dataclass, field
from decimal import Decimal
from app.engine.measure import company as CO
from app.engine.measure import derived as derived_module
from app.engine.measure import engine as kernel
from app.engine.measure import finishes as fin
from app.engine.measure import model_range as MR
from app.engine.measure import one_total_rules as ONE_TOTAL_RULES
from app.engine.measure import rebar as rb
from app.engine.measure import takeoff as tk
from app.engine.measure.models import CalculationContext, MappingInput
from app.engine.measure.profile import ResolvedRuleProfile
from app.modules.drawings_boq import finish_seed
from app.modules.drawings_boq.rebar.rebar_seed import estimate_rule_rows
from app.modules.drawings_boq.standards.service import build_profile
from app.modules.drawings_boq.standards.repository import RuleSetBundle
from app.modules.drawings_boq.takeoff.prep import printed_params
from app.engine.measure.formulas import FORMULAS
from app.engine.measure.profile import FinishRuleSpec
from dataclasses import replace

NAMESPACE = UUID("5c0a3a52-6a0e-4c1b-9a53-128000000128")
RULE_SET_CODE = "PUNJAB_CSR"
STAGES = ("validate_input", "build_solids", "spatial_index", "find_relations", "allocate", "openings", "measure", "finishes", "schedules", "reinforcement",
  "pdf_takeoff", "pdf_space", "layer_split", "stage_split", "derived_works", "self_check")
SKIPPED_HERE = ("reinforcement",)           

def _uid(*parts) -> UUID:
  return uuid5(NAMESPACE, "|".join(str(p) for p in parts))

def work_item_catalog() -> dict:
  out: dict = {}
  for code, description, unit, trade, material_class in (*SD.WORK_ITEMS, *finish_seed.WORK_ITEMS):
    out[code] = SimpleNamespace(code=code, description=description, unit=unit, trade=trade, extra={"material_class": material_class}, wbs_code=None)
  return out

def seed_profile(code: str = RULE_SET_CODE) -> tuple:
  spec = next(p for p in SD.PROFILES if p["code"] == code)
  rs = MeasurementRuleSet(
    id=_uid("rule_set", code), organization_id=None, code=spec["code"], name=spec["name"], description=spec["description"], jurisdiction=spec["jurisdiction"],
    province=spec["province"], standard_name=spec["standard_name"], convention_code=spec.get("convention", "FRAME_MONOLITHIC_A"), is_system=True, is_active=True,
    status="PUBLISHED", immutable_version=1, content_hash="offline", opening_deduction_threshold_m2=SD.OPENING_THRESHOLD_M2, wall_measurement_method="centre_line",
    net_vs_gross_preference="net", preferred_units=dict(spec.get("preferred_units") or {}), extra_config={}, standard_edition=None)

  opening = [
    OpeningMeasurementRule(id=_uid(code, "open", 1), rule_set_id=rs.id, element_scope="ALL", lower_area_m2=Decimal("0"), upper_area_m2=SD.OPENING_THRESHOLD_M2,
      deduction_behavior="IGNORE", deduction_fraction=None, edge_behavior=None),
    OpeningMeasurementRule(id=_uid(code, "open", 2), rule_set_id=rs.id, element_scope="ALL", lower_area_m2=SD.OPENING_THRESHOLD_M2, upper_area_m2=None,
      deduction_behavior="DEDUCT", deduction_fraction=None, edge_behavior=None)]
  wastage = [MaterialWastageRule(id=_uid(code, "waste", mc), rule_set_id=rs.id, material_class=mc, procurement_stage="SITE", factor=Decimal(f))
    for mc, f in (SD.WASTAGE_FULL if spec["full"] else SD.WASTAGE_MIN)]
  mappings = [ElementTypeMapping(id=_uid(code, "map", t), rule_set_id=rs.id, ifc_type=t, work_item_code=wi, default_category=cat, extra_mapping={"material_class": mc},
    quantity_source_preference=None, unit_override=None, confidence_base=Decimal("1")) for t, wi, cat, mc in SD.MAPPINGS]
  rebar, recipes, finish = [], [], ()

  if spec["full"]:
    for i, r in enumerate(SD.REBAR_RULES):
      stock = Decimal(str(r["splice_constraints"]["stock_length_m"])) * 1000 if (r.get("splice_constraints") or {}).get("stock_length_m") else None
      rebar.append(ReinforcementRule(id=_uid(code, "rebar", i), rule_set_id=rs.id, stock_length_mm=stock, cover_mm=None, min_lap_mm=None, use_couplers=False,
        weight_tolerance_pct=None, **r))
    for i, row in enumerate(estimate_rule_rows(rs.id)):
      row.id = _uid(code, "estimate", i)
      row.stock_length_mm = row.cover_mm = row.min_lap_mm = None
      row.use_couplers = False
      row.weight_tolerance_pct = None
      row.hook_rules = row.bend_rules = row.splice_constraints = {}
      rebar.append(row)

    for rec in SD.RECIPES:
      row = AssemblyRecipe(id=_uid(code, "recipe", rec["code"]), organization_id=None, rule_set_id=rs.id, code=rec["code"], name=rec["name"], trigger_ifc_types=rec["triggers"],
        trigger_conditions={}, is_system=True, is_active=True)
      row.components = [AssemblyRecipeComponent(id=_uid(code, "comp", rec["code"], seq), recipe_id=row.id, sequence=seq, work_item_code=wi, description_template=tpl, unit=unit,
        quantity_formula_code=formula, output_unit=FORMULAS[formula].output_unit, category=cat, item_type="MATERIAL", waste_factor=Decimal("1.0"), is_optional=opt)
        for seq, wi, tpl, unit, formula, cat, opt in rec["components"]]
      recipes.append(row)
    rules = finish_seed.finish_rule_rows(rs.id)
    for i, r in enumerate(rules):
      r.id = _uid(code, "finish", i)
    finish = tuple(sorted((FinishRuleSpec(r.space_category, r.surface, r.work_item_code, r.height_mm, r.deduct_openings, r.priority, bool((r.extra_config or {}).get("exclude")), str(r.id))
      for r in rules), key=lambda s: (s.space_category, s.surface, s.work_item_code)))

  bundle = RuleSetBundle(rule_set=rs, opening_rules=opening, wastage_rules=wastage, reinforcement_rules=rebar, mappings=mappings, recipes=recipes)
  catalog = {c: SimpleNamespace(extra=w.extra) for c, w in work_item_catalog().items()}
  conv = kernel.get_convention(rs.convention_code)
  profile = build_profile(bundle, conserves_volume=bool(getattr(conv, "conserves_volume", True)), work_items=catalog)
  return replace(profile, finish_rules=finish), rs

def run_settings(printed: dict, *, derived_params: dict | None = None, stages: bool = True, layers: bool = True) -> dict:
  out: dict = {"scope": "building", "preferred_rule_code": RULE_SET_CODE, "spec": True, "derived": True}
  if stages:
    out["stages"] = True
  if layers:
    out["layers"] = True
  cleaned = {}

  for name in (*derived_module.PARAMS, derived_module.NGL_PARAM, *derived_module.ASKED_PARAMS):
    v = (derived_params or {}).get(name)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
      cleaned[name] = float(v)
  if cleaned:
    out["derived_params"] = cleaned
  run = printed_params.for_run(printed)
  grades = printed.get("grades") or {}
  if run["params"] or run["lap_table_mm"] or grades.get("concrete") or grades.get("steel"):
    out["drawing_params"] = run
  return out

@dataclass
class EngineResult:
  rows: list = field(default_factory=list)            
  stages: dict = field(default_factory=dict)          
  errors: list = field(default_factory=list)
  stats: dict = field(default_factory=dict)
  deductions: list = field(default_factory=list)

def _row(run_id: UUID, e, stage: str) -> dict:
  stage_key = getattr(e, "work_stage", None)
  return {
    "id": str(uuid5(run_id, f"ledger|{e.solid_id}|{e.work_item_code}" + (f"|{stage_key}" if stage_key else ""))), "solid_id": str(e.solid_id) if e.solid_id else None,
    "element_id": str(e.element_id) if e.element_id else None, "level_id": str(e.level_id) if e.level_id else None, "work_item_code": e.work_item_code,
    "quantity": e.quantity, "quantity_net": e.quantity, "unit": e.unit, "material_grade": e.material_grade, "confidence": e.confidence, "formula_code": e.formula_code,
    "trace": MR.with_range(e), "warnings": list(e.warnings), "spec_key": getattr(e, "spec_key", None), "spec": getattr(e, "spec", None), "work_stage": stage_key, "stage": stage,
    "_entry": e}

def run_engine(inputs: tk.TakeoffInputs | None, profile: ResolvedRuleProfile, rule_set, printed: dict, *, case: str = "offline", derived_params: dict | None = None,
  stages: bool = True, layers: bool = True) -> EngineResult:
  result = EngineResult()
  run_id = _uid("run", case)
  settings = run_settings(printed, derived_params=derived_params, stages=stages, layers=layers)
  result.stats["settings"] = settings
  mappings = tuple(sorted((MappingInput(ifc_type=m.ifc_type, work_item_code=m.work_item_code, confidence_base=Decimal(str(m.confidence_base))) for m in profile.mappings),
    key=lambda m: m.ifc_type))
  conv = kernel.get_convention(rule_set.convention_code)
  
  convention_params = {}
  if conv is not None:
    row = next((c for c in SD.CONVENTIONS if c["code"] == rule_set.convention_code), None)
    convention_params = dict((row or {}).get("parameters") or {})

  CO.hold(None)
  ctx = CalculationContext(
    run_id=run_id, engine_version=kernel.ENGINE_VERSION, fingerprint="offline", convention_code=rule_set.convention_code, rule_set_code=rule_set.code,
    rule_set_version=rule_set.immutable_version, mappings=mappings, convention_params=convention_params, openings=(), spaces=(), schedule_lines=(), rebar=(), takeoff=inputs,
    spec_mode=bool(settings.get("spec")), stage_mode=bool(settings.get("stages")), layer_mode=bool(settings.get("layers")), derived_mode=bool(settings.get("derived")), derived_params=dict(settings.get("derived_params") or {}),
    drawing_params=dict(settings.get("drawing_params") or {}), one_total_rules=ONE_TOTAL_RULES.clean(None), detected_params={}, level_names={}, datum_overrides={},
    element_overrides={})
  state: dict = {"accepted": [], "rejected": [], "solids": [], "skipped": {}, "alloc": kernel.AllocationResult.empty(), "ledger": [], "extra_solids": [], "extra_ledger": [],
    "marks": [], "pdf_deductions": ()}
  elements: list = []                      

  def stage(name: str, work) -> None:
    started = time.perf_counter()
    try:
      note = work()
      result.stages[name] = {"ok": True, "ms": int((time.perf_counter() - started) * 1000), **({"note": note} if note else {})}
    except Exception as exc:                                                                    
      result.stages[name] = {"ok": False, "ms": int((time.perf_counter() - started) * 1000)}
      result.errors.append({"stage": name, "error": f"{type(exc).__name__}: {str(exc)[:300]}"})

  def validate():
    state["accepted"], state["rejected"] = kernel.validate_input(ctx, elements)

  def build():
    state["solids"], state["skipped"] = kernel.build_solids(ctx, state["accepted"])

  def planner_stages():
    from app.engine.measure.incremental import AllocationPlanner
    concrete_solids, concrete_elements = kernel.split_steel(state["solids"], state["accepted"])
    planner = AllocationPlanner(ctx, conv, concrete_solids, concrete_elements, None, 0.5)
    planner.spatial()
    planner.relations()
    state["alloc"] = planner.allocate()

  def openings():
    res = fin.apply_openings(ctx, profile, state["solids"], ctx.openings)
    state["alloc"] = fin.merge_openings(state["alloc"], res)

  def measure():
    state["ledger"], _unmapped = kernel.measure(ctx, state["solids"], state["alloc"])

  def finishes():
    res = fin.measure_finishes(ctx, profile, ctx.spaces, ctx.openings)
    state["extra_solids"] += res.solids
    state["extra_ledger"] += res.ledger

  def schedules():
    codes = frozenset(e.work_item_code for e in state["ledger"] + state["extra_ledger"])
    res = fin.schedule_lines_ledger(ctx, ctx.schedule_lines, codes)
    state["extra_solids"] += res.solids
    state["extra_ledger"] += res.ledger

  def pdf_takeoff():
    res = tk.measure_takeoff(ctx, profile, inputs, state["ledger"] + state["extra_ledger"], state["accepted"])
    if res.dropped_keys:
      state["ledger"] = tk.apply_replacements(state["ledger"], res.dropped_keys)
      state["extra_ledger"] = tk.apply_replacements(state["extra_ledger"], res.dropped_keys)
      live = {e.solid_id for e in state["ledger"] + state["extra_ledger"]}
      gone = {sid for sid, _ in res.dropped_keys if sid not in live}
      state["extra_solids"] = [s for s in state["extra_solids"] if s.id not in gone]
    state["extra_solids"] += res.solids
    state["extra_ledger"] += res.ledger
    result.stats["takeoff"] = res.stats
    result.stats["takeoff_results"] = res.results
    return {"measurements": res.stats.get("measurements", 0), "skipped": res.stats.get("skipped", {})}

  def pdf_space():
    res = kernel.split_space(ctx, state["extra_ledger"])
    state["extra_ledger"] = res.ledger
    state["pdf_deductions"] = res.deductions
    result.stats["space"] = res.stats

  def layer_split():
    res = kernel.split_layers(ctx, state["accepted"], state["solids"], state["ledger"])
    state["ledger"] = res.ledger
    result.stats["layers"] = res.stats

  def stage_split():
    res = kernel.split_stages(ctx, state["accepted"], state["solids"], state["alloc"], state["ledger"])
    state["ledger"] = res.ledger
    result.stats["stages"] = res.stats

  def derived_works():
    L, X = state["ledger"], state["extra_ledger"]
    def add(res_solids, res_rows):
      state["extra_solids"] += res_solids
      state["extra_ledger"] += res_rows
      
    res = kernel.measure_derived(ctx, profile, state["accepted"], state["solids"], L, X)
    add(res.solids, res.ledger)
    dp = kernel.measure_dpc(ctx, profile, state["accepted"], state["solids"], L, state["extra_ledger"])
    add(dp.solids, dp.ledger)
    ww = kernel.measure_wall_foundation(ctx, profile, state["accepted"], state["solids"], L, state["extra_ledger"])
    add(ww.solids, ww.ledger)
    wf = kernel.measure_wall_finishes(ctx, profile, state["accepted"], state["solids"], L, state["extra_ledger"])
    add(wf.solids, wf.ledger)
    oa = kernel.measure_opening_area(ctx, state["accepted"], state["solids"], L, state["extra_ledger"])
    add(oa.solids, oa.ledger)
    rt = kernel.measure_roof_treatment(ctx, state["accepted"], state["solids"], L, state["extra_ledger"])
    add(rt.solids, rt.ledger)
    rd = kernel.measure_roof_deck(ctx, L, state["extra_ledger"])
    add(rd.solids, rd.ledger)
    pm = kernel.measure_plaster_mortar(ctx, L, state["extra_ledger"])
    add(pm.solids, pm.ledger)
    ss = kernel.measure_soil_stabilisation(ctx, L, state["extra_ledger"])
    add(ss.solids, ss.ledger)
    fl_solids, fl_rows, fl_stats = kernel.measure_floor_works(ctx, state["accepted"], L, state["extra_ledger"])
    add(fl_solids, fl_rows)
    fw = kernel.measure_formwork(ctx, profile, L, state["extra_ledger"], state["accepted"])
    add(fw.solids, fw.ledger)
    st = kernel.measure_pdf_steel(ctx, L, state["extra_ledger"])
    add(st.solids, st.ledger)
    sa = kernel.measure_steel_allowances(ctx, L, state["extra_ledger"])
    add(sa.solids, sa.ledger)
    result.stats["derived"] = {**res.stats, "dpc": dp.stats, "floor_works": fl_stats, "formwork": fw.stats, "steel": st.stats, "wall_foundation": ww.stats,
      "wall_finishes": wf.stats, "opening_area": oa.stats, "roof_treatment": rt.stats, "roof_deck": rd.stats, "plaster_mortar": pm.stats, "soil_stabilisation": ss.stats,
      "steel_allowances": sa.stats}

  def check():
    kernel.self_check(state["solids"] + state["extra_solids"], state["ledger"] + state["extra_ledger"], state["alloc"], state.get("pdf_deductions") or ())
    failures = rb.self_check_rebar(state["marks"], state["extra_ledger"])
    if failures:
      raise kernel.InvariantViolation(failures)

  stage("validate_input", validate)
  stage("build_solids", build)
  if conv is not None:
    stage("spatial_index", planner_stages)
  stage("openings", openings)
  stage("measure", measure)
  stage("finishes", finishes)
  stage("schedules", schedules)

  if inputs is not None and getattr(inputs, "measurements", None):
    stage("pdf_takeoff", pdf_takeoff)
    if getattr(inputs, "space", None) and (ctx.derived_mode or ctx.stage_mode):
      stage("pdf_space", pdf_space)
    if ctx.layer_mode and ctx.spec_mode:
      stage("layer_split", layer_split)
    if ctx.stage_mode:
      stage("stage_split", stage_split)
    if ctx.derived_mode:
      stage("derived_works", derived_works)

  stage("self_check", check)
  result.rows = [_row(run_id, e, "measure") for e in state["ledger"]] + [_row(run_id, e, "extra") for e in state["extra_ledger"]]
  result.deductions = list(state.get("pdf_deductions") or [])
  result.stats["ledger_rows"] = len(result.rows)
  return result
