from __future__ import annotations
from datetime import datetime, timezone
from app.core.exceptions import TraceException
from sqlalchemy import select
from app.modules.drawings_boq.models import BOQItem, BOQItemAdjustment, BOQItemRateSource, BOQItemStatus, BOQItemType, BOQSnapshot, BOQVersion, ExportJob, ReviewIssue
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.repository import BOQItemRepository, BOQVersionRepository, DrawingRepository, MaterialLibraryRepository, MeasurementRuleSetRepository
from app.modules.drawings_boq.calc_repository import CalculationRunRepository
from app.modules.identity.models import Organization
from app.modules.drawings_boq.standards.service import StandardsService
from app.modules.audit.service import AuditLogService
from app.modules.drawings_boq.standards.material_class import classify_material_class
from app.modules.drawings_boq import boq_logic as logic
from decimal import Decimal
from uuid import UUID, uuid4
from app.modules.audit.models import AuditAction, AuditEntityType
from app.engine.measure.engine import COUNT_ROLES, VOLUME_ROLES
from app.modules.drawings_boq.boq_repository import BOQEngineRepository
from app.modules.drawings_boq import export as exp
from app.modules.drawings_boq.rebar import rebar_repository as rebar_repo

_LOCKED = frozenset({"CALCULATING", "APPROVED", "ISSUED", "SUPERSEDED", "ARCHIVED"})
_NON_WAIVABLE = logic.NON_WAIVABLE_CODES
_COPY = ("material_name", "category", "unit", "quantity", "unit_rate", "rate_source", "item_type", "description",
  "work_item_code", "canonical_unit", "unit_factor", "net_quantity", "waste_factor_applied", "confidence",
  "level_id", "material_grade", "item_key", "calculation_formula", "source_element_count")
_EXPORTS = {"CONTRACT_BOQ": {"pdf", "xlsx"}, "PROCUREMENT": {"xlsx"}, "MEASUREMENT_BOOK": {"pdf", "xlsx"},
  "AUDIT_REPORT": {"pdf"}, "BBS": {"xlsx"}}

def _now():
  return datetime.now(timezone.utc)

def assert_mutable(version) -> None:
  if version.origin == "ENGINE" and version.lifecycle in _LOCKED:
    raise TraceException(f"BOQ version is {version.lifecycle} and cannot be edited.",
      status_code=409, code="BOQ_IMMUTABLE")

def _clone(src: BOQItem, version_id: UUID, org: UUID, **over) -> BOQItem:
  data = {k: getattr(src, k) for k in _COPY}
  data.update(over)
  return BOQItem(id=uuid4(), organization_id=org, boq_version_id=version_id, status=BOQItemStatus.DRAFT, version=1,
    created_by_user_id=src.created_by_user_id, source_kind=src.source_kind, is_manual=src.is_manual,
    review_status=src.review_status, **data)

def _row_dict(obj) -> dict:
  return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

class BOQEngineService:
  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = BOQEngineRepository(session)
    self.versions = BOQVersionRepository(session)
    self.items = BOQItemRepository(session)
    self.runs = CalculationRunRepository(session)
    self.rule_sets = MeasurementRuleSetRepository(session)
    self.library = MaterialLibraryRepository(session)
    self.drawings = DrawingRepository(session)
    self.standards = StandardsService(session)
    self.audit = AuditLogService(session)

  @staticmethod
  def _apply_quantities(item: BOQItem, adjustments: list) -> None:
    net = item.net_quantity if item.net_quantity is not None else item.quantity
    quantity = logic.compute_quantity(net, [logic.AdjustmentLine(a.kind, a.value) for a in adjustments])
    item.adjustment_total = logic.q4(quantity - net)
    item.quantity = quantity
    if item.waste_factor_applied is not None:
      item.gross_quantity = logic.q4(quantity * item.waste_factor_applied)

  async def _engine_version(self, org: UUID, version_id: UUID, lock: bool = False) -> BOQVersion:
    version = await (self.repo.version_for_update(version_id, org) if lock
      else self.versions.get_by_id_and_org(version_id, org))
    if version is None:
      raise TraceException("BOQ version not found.", status_code=404, code="BOQ_VERSION_NOT_FOUND")
    if version.origin != "ENGINE":
      raise TraceException("This action only applies to engine-generated BOQ versions.",
        status_code=422, code="NOT_ENGINE_VERSION")
    return version

  async def _library_rate(self, org: UUID, description: str | None, unit: str):
    entry = await self.library.get_by_raw_text(org, (description or "").strip().lower())
    if entry is None or entry.default_rate is None:
      return None, "none"
    if entry.default_unit and entry.default_unit.strip().lower() != unit.strip().lower():
      converted = logic.convert_rate(entry.default_rate, entry.default_unit, unit)
      return (converted, "ok") if converted is not None else (None, "mismatch")
    return logic.q2(entry.default_rate), "ok"

  async def _org_name(self, org: UUID) -> str:
    r = await self.session.execute(select(Organization.name).where(Organization.id == org))
    return r.scalar_one_or_none() or "Your Company"

  async def build_from_run(self, org: UUID, run_id: UUID, actor_user_id: UUID | None = None) -> dict:
    run = await self.runs.get_by_id_and_org(run_id, org)
    if run is None:
      raise TraceException("Calculation run not found.", status_code=404, code="RUN_NOT_FOUND")
    if run.status != "COMPLETED":
      raise TraceException("Only a COMPLETED run can build a BOQ.", status_code=409, code="RUN_NOT_COMPLETED")
    rule_set = await self.rule_sets.get_by_id(run.rule_set_id)
    profile = await self.standards.profile_for_rule_set(run.rule_set_id)

    ledger = await self.repo.ledger_for_run(run.id, org)
    lines = [logic.LedgerLine(
      id=r.id, solid_id=r.solid_id, element_id=r.element_id, level_id=r.level_id, work_item_code=r.work_item_code,
      quantity=r.quantity_net, unit=r.unit, material_grade=r.material_grade, confidence=r.confidence,
      warnings=tuple(r.warnings or ())) for r in ledger]
    catalog = await self.repo.work_items_by_codes(org, {l.work_item_code for l in lines})
    work_items = {
      code: logic.WorkItemInfo(
        code=w.code, description=w.description, unit=w.unit, trade=w.trade, wbs_code=w.wbs_code,
        material_class=(w.extra or {}).get("material_class") or classify_material_class(
          mapping_material_class=None, material_text=w.description, structural_role=None))
      for code, w in catalog.items()}
    drafts, unknown, mismatch = logic.aggregate(
      lines, scope=(run.settings or {}).get("scope", "building"),
      preferred_units=rule_set.preferred_units if rule_set else None, work_items=work_items,
      waste_for=lambda mc: profile.waste_factor(mc or "DEFAULT"))

    version = await self.repo.working_engine_version(org, run.project_id)
    created = version is None
    seed_items: dict = {}
    seed_adj: dict = {}
    seed_manual: list = []
    
    if created:
      previous = await self.repo.latest_engine_version(org, run.project_id)
      ids = list(run.drawing_revision_ids)
      version = BOQVersion(
        id=uuid4(), organization_id=org, project_id=run.project_id, drawing_id=ids[0] if len(ids) == 1 else None,
        label=f"Engine BOQ - {rule_set.code if rule_set else 'rules'}"[:200], lifecycle="CALCULATING",
        origin="ENGINE", calculation_run_id=run.id, rule_set_id=run.rule_set_id, export_meta={}, generation_meta={})
      await self.versions.create(version)
      
      if previous is not None:
        seed_items = await self.repo.items_by_key(previous.id, org)
        seed_adj = await self.repo.active_adjustments([i.id for i in seed_items.values()])
        seed_manual = [i for i in await self.items.list_by_version(previous.id, org) if i.is_manual]
    else:
      if not await self.repo.transition(version.id, org, version.lifecycle, "CALCULATING",
        calculation_run_id=run.id, rule_set_id=run.rule_set_id):
        raise TraceException("BOQ version changed during the build.", status_code=409, code="CONCURRENT_MODIFICATION")
      await self.session.refresh(version)

    target: dict[str, BOQItem] = {} if created else await self.repo.items_by_key(version.id, org)
    adj_map: dict = {} if created else await self.repo.active_adjustments([i.id for i in target.values()])
    await self.repo.delete_links(version.id)

    drafts_by_key = {d.item_key: d for d in drafts}
    rate_mismatch: list[BOQItem] = []
    new_adjustments: list[BOQItemAdjustment] = []
    item_for_key: dict[str, BOQItem] = {}
    adj_for_item: dict[UUID, list] = {}
    counts = {"created": 0, "updated": 0, "removed": 0, "orphaned": 0}

    for d in drafts:
      item = target.get(d.item_key)
      is_new = item is None
      seed = seed_items.get(d.item_key)
      if is_new:
        item = BOQItem(id=uuid4(), organization_id=org, boq_version_id=version.id, item_type=BOQItemType.MATERIAL,
          status=BOQItemStatus.DRAFT, version=1, created_by_user_id=actor_user_id,
          source_kind="MODEL", is_manual=False, item_key=d.item_key, quantity=Decimal("0"))
        if seed is not None:
          item.unit_rate, item.rate_source = seed.unit_rate, seed.rate_source
        counts["created"] += 1
      else:
        item.status, item.approved_by_user_id, item.approved_at = BOQItemStatus.DRAFT, None, None
        item.version += 1
        counts["updated"] += 1
      keep_waived = item.review_status == "WAIVED" and d.review_status == "REVIEW_REQUIRED"
      item.work_item_code, item.material_name, item.description = d.work_item_code, d.material_name, d.description
      item.category, item.unit, item.canonical_unit, item.unit_factor = d.category, d.unit, d.canonical_unit, d.unit_factor
      item.net_quantity, item.waste_factor_applied, item.confidence = d.net_quantity, d.waste_factor, d.confidence
      item.review_status = "WAIVED" if keep_waived else d.review_status
      item.level_id, item.material_grade, item.calculation_formula = d.level_id, d.material_grade, d.formula_text
      item.rule_set_id, item.calculation_run_id, item.engine_version = run.rule_set_id, run.id, run.engine_version
      item.source_element_count, item.drawing_element_id = d.element_count, None

      adjustments = list(seed_adj.get(seed.id, [])) if (is_new and seed is not None) else list(adj_map.get(item.id, []))
      self._apply_quantities(item, adjustments)
      if item.quantity < 0:
        item.review_status = "REVIEW_REQUIRED"

      if item.unit_rate is None:
        rate, flag = await self._library_rate(org, d.description, d.unit)
        if flag == "ok":
          item.unit_rate, item.rate_source = rate, BOQItemRateSource.LIBRARY
        elif flag == "mismatch":
          rate_mismatch.append(item)
      if is_new:
        self.session.add(item)
        if seed is not None:
          for a in seed_adj.get(seed.id, []):
            new_adjustments.append(BOQItemAdjustment(
              id=uuid4(), organization_id=org, boq_item_id=item.id, kind=a.kind, value=a.value, reason=a.reason,
              created_by_user_id=a.created_by_user_id))
      item_for_key[d.item_key] = item

    orphans: list[BOQItem] = []
    for key, old in list(target.items()):
      if key in drafts_by_key or old.source_kind != "MODEL":
        continue
      if adj_map.get(old.id):
        old.net_quantity, old.confidence, old.review_status = Decimal("0"), None, "REVIEW_REQUIRED"
        old.status = BOQItemStatus.DRAFT
        self._apply_quantities(old, adj_map[old.id])
        orphans.append(old)
        counts["orphaned"] += 1
      else:
        await self.items.delete(old)
        counts["removed"] += 1
    for key, old in seed_items.items():
      if key in drafts_by_key or not seed_adj.get(old.id):
        continue
      stub = _clone(old, version.id, org, net_quantity=Decimal("0"), review_status="REVIEW_REQUIRED")
      self.session.add(stub)
      for a in seed_adj[old.id]:
        new_adjustments.append(BOQItemAdjustment(
          id=uuid4(), organization_id=org, boq_item_id=stub.id, kind=a.kind, value=a.value, reason=a.reason,
          created_by_user_id=a.created_by_user_id))
      stub_adj = list(seed_adj[old.id])
      self._apply_quantities(stub, stub_adj)
      orphans.append(stub)
      counts["orphaned"] += 1
    for m in seed_manual:
      self.session.add(_clone(m, version.id, org, item_key=None))

    await self.session.flush()
    for a in new_adjustments:
      self.session.add(a)
    await self.session.flush()

    link_rows, source_rows = [], []
    for d in drafts:
      item = item_for_key[d.item_key]
      seen_elements: set = set()
      for l in d.lines:
        link_rows.append({"id": uuid4(), "organization_id": org, "boq_version_id": version.id,
          "boq_item_id": item.id, "ledger_id": l.id, "quantity_contributed": l.quantity})
        if l.element_id is not None and l.element_id not in seen_elements:
          seen_elements.add(l.element_id)
          source_rows.append({"id": uuid4(), "organization_id": org, "boq_item_id": item.id,
            "drawing_element_id": l.element_id,
            "quantity_contributed": Decimal(l.quantity).quantize(Decimal("0.001")),
            "formula_snippet": d.formula_text[:300], "contribution_type": "ledger"})
    await self.repo.add_links(link_rows)
    await self.repo.add_source_elements(source_rows)

    items_now = await self.items.list_by_version(version.id, org)
    specs = await self._issue_specs(org, run, ledger, items_now, profile, unknown, mismatch, rate_mismatch, orphans)
    await self.sync_issues(org, version, run.id, specs)

    version.audit_score = await self.repo.min_audit_score(org, list(run.drawing_revision_ids))
    version.generation_meta = {
      "run_id": str(run.id), "rule_set_code": rule_set.code if rule_set else None,
      "rule_set_version": rule_set.immutable_version if rule_set else None,
      "convention_code": run.convention_code, "engine_version": run.engine_version,
      "scope": (run.settings or {}).get("scope", "building"), "item_count": len(items_now), **counts,
    }
    await self.versions.update(version)
    if not await self.repo.transition(version.id, org, "CALCULATING", "CALCULATED"):
      raise TraceException("BOQ version changed during the build.", status_code=409, code="CONCURRENT_MODIFICATION")
    await self.audit.log(org, actor_user_id, AuditEntityType.BOQ_VERSION, version.id,
      AuditAction.CREATE if created else AuditAction.UPDATE,
        f"Built BOQ from calculation run {str(run.id)[:8]}: {counts}")
    await self.session.commit()
    open_issues = len([i for i in await self.repo.issues_for_version(version.id, org, "OPEN")])
    return {"boq_version_id": version.id, "items_created": counts["created"], "items_updated": counts["updated"],
      "items_removed": counts["removed"], "orphaned_items": counts["orphaned"], "open_issues": open_issues}

  async def _issue_specs(self, org, run, ledger, items, profile, unknown, mismatch, rate_mismatch, orphans):
    specs = list(logic.ledger_warning_specs((r.id, r.warnings) for r in ledger))
    stats = run.stats or {}
    for t, n in sorted((stats.get("unmapped_by_type") or {}).items()):
      specs.append(logic.IssueSpec(
        code="UNMAPPED_ELEMENT_TYPE", severity="warning", blocks="NONE", dedupe_key=f"UNMAPPED:{t}",
        message=f"{n} element(s) of type {t} have no work-item mapping, so no quantity was produced.",
        suggested_fix="Map this IFC type to a work item in the rule set.", details={"ifc_type": t, "count": n}))
    for role, n in sorted((stats.get("skipped_by_role") or {}).items()):
      specs.append(logic.IssueSpec(
        code="ROLE_NOT_MEASURED", severity="info", blocks="NONE", dedupe_key=f"ROLE_SKIPPED:{role}",
        message=f"{n} element(s) with role {role} are not measured by this engine version.",
        details={"role": role, "count": n}))
      
    for reason, n in sorted((stats.get("finishes_skipped") or {}).items()):
      specs.append(logic.IssueSpec(
        code="FINISH_SKIPPED", severity="warning", blocks="NONE", dedupe_key=f"FINISH_SKIPPED:{reason}",
        message=f"{n} finish line(s) were not measured: {reason}.",
        suggested_fix="Fix the space in the model, or set the finish manually.", details={"reason": reason, "count": n}))
      
    for reason, n in sorted((stats.get("rebar_skipped") or {}).items()):
      specs.append(logic.IssueSpec(
        code="REBAR_ROW_SKIPPED", severity="warning", blocks="NONE", dedupe_key=f"REBAR_SKIPPED:{reason}",
        message=f"{n} bar schedule row(s) were not measured ({reason}).",
        suggested_fix="Fix the row's shape, dimensions or length and re-run.", details={"reason": reason, "count": n}))
      
    mapped = [m.ifc_type for m in profile.mappings if m.work_item_code]
    invalid = await self.repo.invalid_counts(org, list(run.drawing_revision_ids), mapped,
      sorted(VOLUME_ROLES | COUNT_ROLES))
    for t, n in sorted(invalid.items()):
      specs.append(logic.IssueSpec(
        code="ELEMENT_NOT_MEASURED", severity="error", blocks="APPROVAL", dedupe_key=f"INVALID:{t}",
        message=f"{n} {t} element(s) failed model validation and have no quantity.",
        suggested_fix="Fix the missing dimensions or quantities in the model and re-upload.",
        details={"ifc_type": t, "count": n}))
      
    for did in run.drawing_revision_ids:
      drawing = await self.drawings.get_by_id_and_org(did, org)
      for mi in ((drawing.ingestion_meta or {}).get("model_issues") or []) if drawing else []:
        if mi.get("code") == "UNIT_SCALE_AMBIGUOUS":
          specs.append(logic.IssueSpec(
            code="UNIT_SCALE_AMBIGUOUS", severity="error", blocks="APPROVAL", dedupe_key=f"UNIT_SCALE:{did}",
            message="The IFC file has no length unit; metres were assumed.",
            suggested_fix="Export the model with explicit units.", details={"drawing_id": str(did)}))
          
    for code in unknown:
      specs.append(logic.IssueSpec(
        code="WORK_ITEM_NOT_IN_CATALOG", severity="warning", blocks="NONE", dedupe_key=f"WI_UNKNOWN:{code}",
        message=f"Work item {code} is not in the work-item catalog.", details={"work_item_code": code}))
      
    for code in mismatch:
      specs.append(logic.IssueSpec(
        code="WORK_ITEM_UNIT_MISMATCH", severity="error", blocks="APPROVAL", dedupe_key=f"WI_UNIT:{code}",
        message=f"Work item {code} is catalogued in a different unit family than the measured quantity.",
        details={"work_item_code": code}))
      
    for it in rate_mismatch:
      specs.append(logic.IssueSpec(
        code="RATE_UNIT_MISMATCH", severity="error", blocks="APPROVAL", dedupe_key=f"RATE_UNIT:{it.item_key}",
        message=f"The library rate for '{it.material_name}' cannot be converted to {it.unit}.",
        suggested_fix="Set a rate in the item's unit.", boq_item_id=it.id))
      
    for it in orphans:
      specs.append(logic.IssueSpec(
        code="ADJUSTMENT_ORPHANED", severity="warning", blocks="APPROVAL", dedupe_key=f"ORPHAN:{it.item_key}",
        message=f"'{it.material_name}' no longer exists after recalculation but has adjustments.",
        suggested_fix="Revoke the adjustments or recreate the quantity manually.", boq_item_id=it.id))
      
    pricing = self._pricing_spec(items)
    if pricing is not None:
      specs.append(pricing)
    return specs

  @staticmethod
  def _pricing_spec(items):
    unpriced = [i for i in items if i.unit_rate is None]
    if not unpriced:
      return None
    return logic.IssueSpec(
      code="UNPRICED_ITEM", severity="warning", blocks="ISSUE", dedupe_key="UNPRICED",
      message=f"{len(unpriced)} item(s) have no rate; the BOQ total is understated until they are priced.",
      suggested_fix="Set rates, or waive this issue with a reason.",
      details={"count": len(unpriced), "item_ids": [str(i.id) for i in unpriced][:50]})

  async def refresh_pricing_issue(self, org: UUID, version_id: UUID) -> None:
    version = await self.versions.get_by_id_and_org(version_id, org)
    if version is None:
      return
    items = await self.items.list_by_version(version_id, org)
    spec = self._pricing_spec(items)
    await self.sync_issues(org, version, version.calculation_run_id, [spec] if spec else [], prefixes=("UNPRICED",))

  async def sync_issues(self, org, version, run_id, specs, prefixes=None) -> None:
    existing = {i.dedupe_key: i for i in await self.repo.issues_for_version(version.id, org)}
    now, seen = _now(), set()
    for s in specs:
      seen.add(s.dedupe_key)
      cur = existing.get(s.dedupe_key)
      if cur is None:
        self.session.add(ReviewIssue(
          id=uuid4(), organization_id=org, project_id=version.project_id, boq_version_id=version.id,
          calculation_run_id=run_id, drawing_element_id=s.drawing_element_id, boq_item_id=s.boq_item_id,
          code=s.code, severity=s.severity, blocks=s.blocks, message=s.message, suggested_fix=s.suggested_fix,
          details=s.details, dedupe_key=s.dedupe_key))
      elif cur.status == "OPEN" or (cur.status == "RESOLVED" and cur.resolved_by_user_id is None):
        cur.status, cur.resolved_at, cur.resolution_note = "OPEN", None, None
        cur.severity, cur.blocks, cur.message, cur.details = s.severity, s.blocks, s.message, s.details
        cur.suggested_fix, cur.calculation_run_id, cur.boq_item_id = s.suggested_fix, run_id, s.boq_item_id
    for key, cur in existing.items():
      if key in seen or cur.status != "OPEN":
        continue
      if prefixes and not any(key.startswith(p) for p in prefixes):
        continue
      cur.status, cur.resolved_at = "RESOLVED", now
      cur.resolution_note = "No longer applies after recalculation."
    await self.session.flush()

  async def list_issues(self, org: UUID, project_id: UUID, status: str | None, version_id: UUID | None):
    return await self.repo.issues_for_project(org, project_id, status, version_id)

  async def resolve_issue(self, org: UUID, issue_id: UUID, user_id: UUID, status: str, note: str | None):
    issue = await self.repo.get_issue(issue_id, org)
    if issue is None:
      raise TraceException("Review issue not found.", status_code=404, code="REVIEW_ISSUE_NOT_FOUND")
    if issue.status != "OPEN":
      raise TraceException("Issue is already closed.", status_code=409, code="ISSUE_NOT_OPEN")
    if status == "WAIVED":
      if not (note or "").strip():
        raise TraceException("Waiving an issue needs a reason.", status_code=422, code="WAIVER_REQUIRES_REASON")
      if issue.code in _NON_WAIVABLE:
        raise TraceException("This issue cannot be waived.", status_code=422, code="ISSUE_NOT_WAIVABLE")
    if issue.boq_version_id is not None:
      assert_mutable(await self.versions.get_by_id_and_org(issue.boq_version_id, org))
    issue.status, issue.resolution_note = status, (note or "").strip() or None
    issue.resolved_by_user_id, issue.resolved_at = user_id, _now()
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.REVIEW_ISSUE, issue.id, AuditAction.UPDATE,
      f"{status.title()} review issue {issue.code}")
    return issue

  async def _item_for_edit(self, org: UUID, item_id: UUID) -> tuple[BOQItem, BOQVersion]:
    item = await self.items.get_by_id_and_org_for_update(item_id, org)
    if item is None:
      raise TraceException("BOQ item not found.", status_code=404, code="BOQ_ITEM_NOT_FOUND")
    version = await self.versions.get_by_id_and_org(item.boq_version_id, org)
    assert_mutable(version)
    return item, version

  async def _add_adjustment(self, org, item, user_id, kind, value, reason) -> BOQItemAdjustment:
    if item.source_kind != "MODEL":
      raise TraceException("Adjustments apply to calculated items only; edit manual items directly.",
        status_code=422, code="ADJUSTMENT_NOT_APPLICABLE")
    if not (reason or "").strip():
      raise TraceException("An adjustment needs a reason.", status_code=422, code="ADJUSTMENT_REQUIRES_REASON")
    if kind not in ("DELTA", "REPLACE"):
      raise TraceException("Unknown adjustment kind.", status_code=422, code="INVALID_ADJUSTMENT_KIND")
    active = (await self.repo.active_adjustments([item.id])).get(item.id, [])
    if kind == "REPLACE":
      for a in active:
        if a.kind == "REPLACE":
          a.revoked_at, a.revoked_by_user_id = _now(), user_id
          a.revoke_reason = "Replaced by a newer REPLACE adjustment."
      await self.session.flush()
      active = [a for a in active if a.kind != "REPLACE"]
      
    adj = BOQItemAdjustment(id=uuid4(), organization_id=org, boq_item_id=item.id, kind=kind,
      value=Decimal(value), reason=reason.strip(), created_by_user_id=user_id)
    self.session.add(adj)
    await self.session.flush()
    self._apply_quantities(item, [*active, adj])
    if item.quantity < 0:
      raise TraceException("The adjustment would make the quantity negative.",
        status_code=422, code="ADJUSTMENT_NEGATIVE_QUANTITY")
    item.version += 1
    await self.items.update(item)
    return adj

  async def apply_quantity_change(self, org, item, user_id, new_quantity, reason) -> None:
    delta = Decimal(new_quantity) - item.quantity
    if delta != 0:
      await self._add_adjustment(org, item, user_id, "DELTA", delta, reason)

  async def add_adjustment(self, org: UUID, item_id: UUID, user_id: UUID, kind: str, value: Decimal, reason: str):
    item, _ = await self._item_for_edit(org, item_id)
    adj = await self._add_adjustment(org, item, user_id, kind, value, reason)
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.BOQ_ADJUSTMENT, adj.id, AuditAction.CREATE,
      f'{kind} adjustment {value} on "{item.material_name}": {reason.strip()[:200]}')
    return adj

  async def revoke_adjustment(self, org: UUID, adjustment_id: UUID, user_id: UUID, reason: str):
    adj = await self.repo.get_adjustment(adjustment_id, org)
    
    if adj is None:
      raise TraceException("Adjustment not found.", status_code=404, code="ADJUSTMENT_NOT_FOUND")
    if adj.revoked_at is not None:
      raise TraceException("Adjustment is already revoked.", status_code=409, code="ADJUSTMENT_REVOKED")
    if not (reason or "").strip():
      raise TraceException("Revoking needs a reason.", status_code=422, code="ADJUSTMENT_REQUIRES_REASON")
  
    item, _ = await self._item_for_edit(org, adj.boq_item_id)
    adj.revoked_at, adj.revoked_by_user_id, adj.revoke_reason = _now(), user_id, reason.strip()
    await self.session.flush()
    active = (await self.repo.active_adjustments([item.id])).get(item.id, [])
    self._apply_quantities(item, active)
    item.version += 1
    await self.items.update(item)
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.BOQ_ADJUSTMENT, adj.id, AuditAction.UPDATE,
      f'Revoked adjustment on "{item.material_name}"')
    return adj

  async def list_adjustments(self, org: UUID, item_id: UUID):
    if await self.items.get_by_id_and_org_for_update(item_id, org) is None:
      raise TraceException("BOQ item not found.", status_code=404, code="BOQ_ITEM_NOT_FOUND")
    return await self.repo.list_adjustments(item_id, org)

  async def waive_item_review(self, org: UUID, item_id: UUID, user_id: UUID, reason: str):
    item, _ = await self._item_for_edit(org, item_id)
    if not (reason or "").strip():
      raise TraceException("Waiving a review needs a reason.", status_code=422, code="WAIVER_REQUIRES_REASON")
    item.review_status = "WAIVED"
    item.version += 1
    await self.items.update(item)
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.BOQ_ITEM, item.id, AuditAction.UPDATE,
      f'Waived review of "{item.material_name}": {reason.strip()[:200]}')
    return item

  async def confirm_rate(self, org: UUID, item_id: UUID, user_id: UUID):
    item, version = await self._item_for_edit(org, item_id)
    if item.unit_rate is None:
      raise TraceException("The item has no rate to confirm.", status_code=422, code="BOQ_ITEM_UNPRICED")
    item.rate_source = BOQItemRateSource.MANUAL
    item.version += 1
    await self.items.update(item)
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.BOQ_ITEM, item.id, AuditAction.UPDATE,
      f'Confirmed rate for "{item.material_name}"')
    return item

  async def item_trace(self, org: UUID, item_id: UUID) -> dict:
    item = await self.items.get_by_id_and_org_for_update(item_id, org)
    if item is None:
      raise TraceException("BOQ item not found.", status_code=404, code="BOQ_ITEM_NOT_FOUND")
    ledger = await self.repo.ledger_for_item(item_id, org)
    deductions, bar_marks = [], []
    if ledger:
      deductions = await self.repo.deductions_for_solids(ledger[0].run_id, org, [l.solid_id for l in ledger])
      steel = [l.solid_id for l in ledger if l.formula_code in ("REBAR_BBS_WEIGHT", "REBAR_RULE_ESTIMATE")]
      bar_marks = await rebar_repo.marks_for_solids(self.session, org, ledger[0].run_id, steel)
    return {"item": item, "ledger": ledger, "deductions": deductions,
      "adjustments": await self.repo.list_adjustments(item_id, org), "bar_marks": bar_marks}

  async def ledger_for_version(self, org: UUID, version_id: UUID, *, limit: int, after, work_item_code):
    await self._engine_version(org, version_id)
    rows = await self.repo.ledger_for_version(version_id, org, limit=limit, after=after, work_item_code=work_item_code)
    return rows[:limit], (rows[limit - 1].id if len(rows) > limit else None)

  async def _create_snapshot(self, version: BOQVersion, purpose: str, user_id: UUID | None, note: str | None):
    org = version.organization_id
    items = await self.items.list_by_version(version.id, org)
    links = await self.repo.link_pairs(version.id, org)
    rule_set = await self.rule_sets.get_by_id(version.rule_set_id) if version.rule_set_id else None
    run = await self.runs.get_by_id_and_org(version.calculation_run_id, org) if version.calculation_run_id else None
    
    dicts = []
    for i in items:
      pairs = links.get(i.id, [])
      dicts.append({
        "id": i.id, "item_key": i.item_key, "work_item_code": i.work_item_code, "material_name": i.material_name,
        "description": i.description, "category": i.category, "item_type": i.item_type.value,
        "level_id": i.level_id, "material_grade": i.material_grade, "unit": i.unit,
        "canonical_unit": i.canonical_unit, "unit_factor": i.unit_factor, "net_quantity": i.net_quantity,
        "adjustment_total": i.adjustment_total, "quantity": i.quantity, "waste_factor_applied": i.waste_factor_applied,
        "gross_quantity": i.gross_quantity, "unit_rate": i.unit_rate,
        "rate_source": i.rate_source.value if i.rate_source else None, "confidence": i.confidence,
        "review_status": i.review_status, "source_kind": i.source_kind, "is_manual": i.is_manual,
        "ledger_row_count": len(pairs), "ledger_hash": logic.ledger_hash(pairs)})
    header = {"version_id": str(version.id), "run_id": str(version.calculation_run_id),
              "rule_set": [rule_set.code, rule_set.immutable_version] if rule_set else None,
              "convention": run.convention_code if run else None, "engine": run.engine_version if run else None,
              "covered_area_sqft": str(version.covered_area_sqft) if version.covered_area_sqft else None}
    rows, totals, content_hash = logic.build_snapshot(dicts, header)
    
    snap = BOQSnapshot(
      id=uuid4(), organization_id=org, boq_version_id=version.id, version_no=await self.repo.next_snapshot_no(version.id),
      purpose=purpose, content_hash=content_hash, item_count=len(rows), totals=totals,
      calculation_run_id=version.calculation_run_id, rule_set_id=version.rule_set_id,
      rule_set_code=rule_set.code if rule_set else None,
      rule_set_version=rule_set.immutable_version if rule_set else None,
      convention_code=run.convention_code if run else None, engine_version=run.engine_version if run else None,
      note=note, created_by_user_id=user_id)
    self.session.add(snap)
    await self.session.flush()
    await self.repo.add_snapshot_items([{**r, "id": uuid4(), "organization_id": org, "snapshot_id": snap.id} for r in rows])
    return snap

  async def list_snapshots(self, org: UUID, version_id: UUID):
    await self._engine_version(org, version_id)
    return await self.repo.list_snapshots(version_id, org)

  async def snapshot_items(self, org: UUID, snapshot_id: UUID):
    if await self.repo.get_snapshot(snapshot_id, org) is None:
      raise TraceException("Snapshot not found.", status_code=404, code="SNAPSHOT_NOT_FOUND")
    return await self.repo.snapshot_items(snapshot_id, org)

  async def _move(self, org, version_id, expected, to, **values):
    if not await self.repo.transition(version_id, org, expected, to, **values):
      raise TraceException(f"The BOQ version is not in {expected}.", status_code=409,
        code="INVALID_LIFECYCLE_TRANSITION")

  async def _guards(self, version: BOQVersion, items, blocks: tuple) -> None:
    if not items:
      raise TraceException("The BOQ has no items.", status_code=422, code="BOQ_EMPTY")
    if await self.repo.count_open(version.id, version.organization_id, blocks):
      raise TraceException("Open blocking review issues must be resolved or waived first.",
        status_code=409, code="OPEN_BLOCKING_ISSUES")
    if any(i.unit_rate is None for i in items):
      issue = await self.repo.issue_by_dedupe(version.id, "UNPRICED")
      if issue is None or issue.status != "WAIVED":
        raise TraceException("Every item must be priced, or the unpriced-items issue waived with a reason.",
          status_code=409, code="UNPRICED_ITEMS")
    if any(i.rate_source == BOQItemRateSource.AI_SUGGESTED for i in items):
      raise TraceException("AI-suggested rates must be confirmed before approval.",
        status_code=409, code="AI_RATE_UNCONFIRMED")

  async def submit_for_review(self, org, version_id, user_id):
    version = await self._engine_version(org, version_id, lock=True)
    await self._move(org, version.id, "CALCULATED", "UNDER_REVIEW")
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.BOQ_VERSION, version.id, AuditAction.UPDATE, "Submitted BOQ for review")
    return await self.versions.get_by_id_and_org(version.id, org)

  async def reopen(self, org, version_id, user_id):
    version = await self._engine_version(org, version_id, lock=True)
    await self._move(org, version.id, "UNDER_REVIEW", "CALCULATED")
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.BOQ_VERSION, version.id, AuditAction.UPDATE, "Sent BOQ back from review")
    return await self.versions.get_by_id_and_org(version.id, org)

  async def approve_version(self, org, version_id, user_id, note: str | None = None):
    version = await self._engine_version(org, version_id, lock=True)
    if version.lifecycle != "UNDER_REVIEW":
      raise TraceException("The BOQ version is not under review.", status_code=409, code="INVALID_LIFECYCLE_TRANSITION")
    items = await self.items.list_by_version(version.id, org)
    await self._guards(version, items, ("APPROVAL",))
    
    now = _now()
    await self.repo.supersede_engine(org, version.project_id, version.id)
    await self._move(org, version.id, "UNDER_REVIEW", "APPROVED", approved_by_user_id=user_id, approved_at=now)
    await self.repo.approve_items(version.id, org, user_id, now)
    await self.session.refresh(version)
    snap = await self._create_snapshot(version, "APPROVAL", user_id, note)
    version.snapshot_id = snap.id
    await self.session.flush()
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.BOQ_VERSION, version.id, AuditAction.APPROVE,
      f"Approved BOQ (snapshot v{snap.version_no}, hash {snap.content_hash[:12]})")
    return await self.versions.get_by_id_and_org(version.id, org)

  async def issue_version(self, org, version_id, user_id, note: str | None = None):
    version = await self._engine_version(org, version_id, lock=True)
    if version.lifecycle != "APPROVED":
      raise TraceException("Only an APPROVED BOQ can be issued.", status_code=409, code="INVALID_LIFECYCLE_TRANSITION")
    items = await self.items.list_by_version(version.id, org)
    await self._guards(version, items, ("APPROVAL", "ISSUE"))
    snap = await self._create_snapshot(version, "ISSUE", user_id, note)
    await self._move(org, version.id, "APPROVED", "ISSUED", snapshot_id=snap.id, issued_by_user_id=user_id, issued_at=_now())
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.BOQ_VERSION, version.id, AuditAction.UPDATE,
      f"Issued BOQ (snapshot v{snap.version_no}, hash {snap.content_hash[:12]})")
    return await self.versions.get_by_id_and_org(version.id, org)

  async def archive_version(self, org, version_id, user_id):
    version = await self._engine_version(org, version_id, lock=True)
    if version.lifecycle in ("CALCULATING", "ARCHIVED"):
      raise TraceException("This version cannot be archived now.", status_code=409, code="INVALID_LIFECYCLE_TRANSITION")
    if version.lifecycle == "ISSUED" and await self.repo.count_issued(org, version.project_id, version.id) == 0:
      raise TraceException("The only issued version of a project cannot be archived.",
        status_code=409, code="SOLE_ISSUED_VERSION")
    await self._move(org, version.id, version.lifecycle, "ARCHIVED")
    await self.session.commit()
    await self.audit.log(org, user_id, AuditEntityType.BOQ_VERSION, version.id, AuditAction.UPDATE, "Archived BOQ")
    return await self.versions.get_by_id_and_org(version.id, org)

  async def export_snapshot(self, org: UUID, version_id: UUID, kind: str, fmt: str, user_id: UUID,
    snapshot_id: UUID | None = None) -> tuple[bytes, str, str]:
    if kind not in _EXPORTS:
      raise TraceException("This export is not available yet.", status_code=422, code="EXPORT_NOT_AVAILABLE")
    if fmt not in _EXPORTS[kind]:
      raise TraceException(f"{kind} is not available as {fmt}.", status_code=422, code="EXPORT_FORMAT_UNSUPPORTED")
    version = await self._engine_version(org, version_id)
    if version.lifecycle not in ("APPROVED", "ISSUED"):
      raise TraceException("Exports need an APPROVED or ISSUED BOQ.", status_code=409, code="EXPORT_REQUIRES_APPROVED")
    snap = await self.repo.get_snapshot(snapshot_id or version.snapshot_id, org)
    if snap is None or snap.boq_version_id != version.id:
      raise TraceException("Snapshot not found for this version.", status_code=404, code="SNAPSHOT_NOT_FOUND")
    started = _now()

    rows = [_row_dict(r) for r in await self.repo.snapshot_items(snap.id, org)]
    snapshot = {k: getattr(snap, k) for k in ("id", "version_no", "purpose", "content_hash", "created_at", "totals",
      "rule_set_code", "rule_set_version", "convention_code", "engine_version", "item_count")}
    meta = version.export_meta or {}
    company = meta.get("company_name") or await self._org_name(org)
    version_meta = {**meta, "covered_area_sqft": version.covered_area_sqft}
    
    if kind == "CONTRACT_BOQ":
      data = (exp.build_contract_boq_pdf if fmt == "pdf" else exp.build_contract_boq_xlsx)(snapshot, rows, version_meta, company)
    elif kind == "PROCUREMENT":
      data = exp.build_procurement_xlsx(snapshot, rows, version_meta, company)
    elif kind == "BBS":
      data = await self._bbs_workbook(org, snap, snapshot, version_meta, company)
    elif kind == "MEASUREMENT_BOOK":
      evidence = await self._evidence(org, version.id)
      data = (exp.build_measurement_book_pdf if fmt == "pdf" else exp.build_measurement_book_xlsx)(
        snapshot, rows, evidence, version_meta, company)
    else:
      issues = [{"code": i.code, "severity": i.severity, "blocks": i.blocks, "status": i.status,
        "message": i.message, "note": i.resolution_note} for i in await self.repo.issues_for_version(version.id, org)]
      adjustments = [{"item": name, "kind": a.kind, "value": a.value, "reason": a.reason,
        "created_at": a.created_at, "revoked": a.revoked_at is not None, "revoke_reason": a.revoke_reason}
        for a, name in await self.repo.adjustments_for_version(version.id, org)]
      data = exp.build_audit_report_pdf(snapshot, rows, issues, adjustments, version_meta, company)

    safe = version.label.replace(" ", "_").encode("ascii", "ignore").decode("ascii")
    filename = f"{kind}-{safe}-s{snap.version_no}.{fmt}"
    self.repo.add_export_job(ExportJob(
      id=uuid4(), organization_id=org, boq_version_id=version.id, snapshot_id=snap.id, kind=kind, format=fmt.upper(),
      status="SUCCEEDED", parameters={"snapshot_version_no": snap.version_no}, requested_by_user_id=user_id,
      file_size_bytes=len(data), started_at=started, finished_at=_now()))
    await self.session.commit()
    media = "application/pdf" if fmt == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return data, media, filename
   
  async def _bbs_workbook(self, org: UUID, snap, snapshot: dict, version_meta: dict, company: str) -> bytes:
    if snap.calculation_run_id is None:
      raise TraceException("This snapshot was not built from a calculation run.", status_code=422, code="NOT_ENGINE_VERSION")
    marks = await rebar_repo.marks_for_run(self.session, org, snap.calculation_run_id)
    scheduled = [m for m in marks if m.provenance != "RULE_ESTIMATE"]
    
    if not scheduled:
      raise TraceException("There is no scheduled steel to export. Estimated steel is never exported as a bar "
        "bending schedule; import and confirm a bar schedule, then re-run the calculation.",
        status_code=409, code="BBS_NO_SCHEDULED_STEEL")
      
    estimated_kg = sum((m.total_kg for m in marks if m.provenance == "RULE_ESTIMATE"), Decimal("0"))
    names = await self.repo.element_names([m.element_id for m in scheduled if m.element_id])
    levels = await self.repo.level_names(org, [m.level_id for m in scheduled if m.level_id])
    rows = [{**_row_dict(m),
      "member": names.get(m.element_id) if m.element_id else ((m.trace or {}).get("member_mark") or "-"),
      "level": levels.get(m.level_id, "-") if m.level_id else "-"} for m in scheduled]
    return exp.build_bbs_xlsx(snapshot, rows, version_meta, company, estimated_kg)

  async def _evidence(self, org: UUID, version_id: UUID) -> dict[str, list[dict]]:
    links = await self.repo.link_pairs(version_id, org)
    all_ids = [lid for pairs in links.values() for lid, _ in pairs]
    ledger = {l.id: l for l in await self.repo.ledger_by_ids(all_ids)}
    owner_ids = {UUID(s["to"]) for l in ledger.values() for s in (l.trace or {}).get("steps", [])
    if s.get("to") and s["to"] != "None"}
    names = await self.repo.element_names([l.element_id for l in ledger.values() if l.element_id] + list(owner_ids))
    levels = await self.repo.level_names(org, [l.level_id for l in ledger.values() if l.level_id])
    out: dict[str, list[dict]] = {}
    
    for item_id, pairs in links.items():
      lines = []
      for lid, qty in pairs[:300]:
        l = ledger.get(lid)
        if l is None:
          continue
        steps = []
        for s in (l.trace or {}).get("steps", []):
          op = s.get("op") or ""
          step_qty = s.get("m3") or s.get("m2") or s.get("m")
          if op.startswith("gross"):
            steps.append(f"gross {step_qty} {l.unit}")
          elif op == "deduction":
            steps.append(f"less {step_qty} {l.unit} ({s.get('type')}) {s.get('note') or s.get('rule') or ''}".strip())
          elif op == "count":
            steps.append(f"count {s['nos']}")
          elif op == "bar_mark":
            steps.append(f"bar {s['mark']} dia {s['dia_mm']} x {s['count']} = {s['kg']} kg")
          elif op == "schedule_quantity":
            steps.append(f"schedule {step_qty or s.get(l.unit)} {l.unit}")
        steps.append(f"net {(l.trace or {}).get('net')}")
        lines.append({"element": names.get(l.element_id, "-") if l.element_id else (l.trace or {}).get("label", "-"),
          "level": levels.get(l.level_id, "-") if l.level_id else "-",
          "quantity": qty, "unit": l.unit, "steps": steps, "warnings": list(l.warnings or [])})
      out[str(item_id)] = lines
    return out