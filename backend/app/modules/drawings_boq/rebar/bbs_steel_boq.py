from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import TraceException
from app.engine.measure.rebar import REBAR_WORK_ITEM
from app.modules.audit.models import AuditAction, AuditEntityType
from app.modules.drawings_boq import boq_logic as logic
from app.modules.drawings_boq.boq_service import BOQEngineService, assert_mutable
from app.modules.drawings_boq.rebar import bbs_audited as BA
from app.modules.drawings_boq.rebar.bbs_steel_service import SteelFiguresService

MARK = "BBS audit: "
ZERO = Decimal("0")
ADDED, REPLACED, UNCHANGED, CLEARED, NOTHING = "ADDED", "REPLACED", "UNCHANGED", "CLEARED", "NOTHING"
REASON_CAP = 500

def effect_of(figs: dict) -> Decimal:
  """The kg the audit adds to the bill's steel item: the effect of the accepted findings, and only when the project's steel line is the audited figure."""
  if figs.get("source") != BA.SOURCE_AUDITED:
    return ZERO
  audited = figs["figures"][BA.FORMULA_AUDITED]
  if audited.get("kg") is None:
    return ZERO
  return Decimal(str(audited.get("applied_kg") or 0))

def guard(figs: dict, effect: Decimal) -> None:
  """The effect is a difference on the schedule weight the run billed; it is only carried over when the run billed that schedule."""
  if effect == 0:
    return
  if not figs.get("ledger_bbs_kg"):
    raise TraceException("The calculation run has no bar schedule weight, so there is nothing to apply the audit to.", status_code=422, code="STEEL_RUN_HAS_NO_SCHEDULE")
  if figs.get("ledger_gap_kg") is not None:
    raise TraceException("The calculation run billed another bar schedule than the audited one; re-run the calculation with the current schedule first.", status_code=409, code="STEEL_RUN_DIFFERS_FROM_SCHEDULE")

def choose_item(items: list, item_id: UUID | None):
  """The one steel item the audit goes onto."""
  if item_id is not None:
    for i in items:
      if i.id == item_id:
        return i
    raise TraceException("That item is not a steel item of this BOQ version.", status_code=404, code="STEEL_ITEM_NOT_FOUND")
  if not items:
    raise TraceException("The BOQ version has no calculated steel item.", status_code=422, code="STEEL_ITEM_NOT_FOUND")
  if len(items) > 1:
    names = "; ".join(f"{i.material_name} ({i.id})" for i in items)
    raise TraceException(f"The BOQ version has {len(items)} steel items, so say which one takes the audit (item_id): {names}", status_code=422, code="STEEL_ITEM_AMBIGUOUS")
  return items[0]

def marked(active: list) -> list:
  return [a for a in active if a.kind == "DELTA" and str(a.reason or "").startswith(MARK)]

def delta_of(effect: Decimal, item) -> Decimal:
  if str(item.canonical_unit or "").lower() != "kg":
    raise TraceException(f"The steel item is counted in {item.canonical_unit}, not kg.", status_code=422, code="STEEL_ITEM_UNIT")
  return logic.q4(effect * Decimal(str(item.unit_factor if item.unit_factor is not None else 1)))

def decide(delta: Decimal, mine: list) -> str:
  if delta == 0:
    return CLEARED if mine else NOTHING
  if len(mine) == 1 and mine[0].kind == "DELTA" and Decimal(str(mine[0].value)) == delta:
    return UNCHANGED
  return REPLACED if mine else ADDED

def reason_of(figs: dict, effect: Decimal) -> str:
  audited = figs["figures"][BA.FORMULA_AUDITED]
  bbs = figs["figures"][BA.FORMULA_BBS]["kg"]
  return (f"{MARK}{audited.get('applied_count') or 0} accepted finding(s) change the schedule's {Decimal(str(bbs)):,.2f} kg by {effect:+,.2f} kg; "
    f"{figs['open_findings']['count']} finding(s) still open.")[:REASON_CAP]

def projected(item, active: list, mine: list, delta: Decimal) -> Decimal:
  keep = [a for a in active if a not in mine]
  lines = [logic.AdjustmentLine(a.kind, a.value) for a in keep]
  if delta != 0:
    lines.append(logic.AdjustmentLine("DELTA", delta))
  net = item.net_quantity if item.net_quantity is not None else item.quantity
  return logic.compute_quantity(net, lines)

def _now():
  return datetime.now(timezone.utc)

class SteelBoqService:
  def __init__(self, session: AsyncSession, engine=None, steel=None):
    self.session = session
    self.eng = engine or BOQEngineService(session)
    self.steel = steel or SteelFiguresService(session)

  async def steel_items(self, org: UUID, version_id: UUID) -> list:
    return [i for i in await self.eng.items.list_by_version(version_id, org) if i.work_item_code == REBAR_WORK_ITEM and i.source_kind == "MODEL"]

  async def plan(self, org: UUID, version_id: UUID, item_id: UUID | None, lock: bool) -> dict:
    version = await self.eng._engine_version(org, version_id, lock=lock)
    assert_mutable(version)
    if version.calculation_run_id is None:
      raise TraceException("The BOQ version has no calculation run.", status_code=422, code="STEEL_NO_RUN")
    figs = await self.steel.figures(org, version.calculation_run_id)
    effect = effect_of(figs)
    guard(figs, effect)
    item = choose_item(await self.steel_items(org, version_id), item_id)
    delta = delta_of(effect, item)
    active = (await self.eng.repo.active_adjustments([item.id])).get(item.id, [])
    mine = marked(active)
    state = decide(delta, mine)
    return {"version": version, "figs": figs, "effect": effect, "item": item, "delta": delta, "active": active, "mine": mine, "state": state}

  @staticmethod
  def _out(p: dict, *, dry_run: bool, quantity_after, adjustment_id=None, revoked: int = 0) -> dict:
    item, figs = p["item"], p["figs"]
    return {"version_id": p["version"].id, "item_id": item.id, "item_name": item.material_name, "unit": item.unit, "source": figs.get("source"), "effect_kg": p["effect"], "delta": p["delta"],
      "state": p["state"], "in_sync": p["state"] in (UNCHANGED, NOTHING), "quantity_now": item.quantity if dry_run else p["before"], "quantity_after": quantity_after, "net_quantity": item.net_quantity,
      "adjustment_id": adjustment_id, "revoked": revoked, "applied_count": figs["figures"][BA.FORMULA_AUDITED].get("applied_count") or 0, "open_count": figs["open_findings"]["count"],
      "note": figs["line"]["note"], "dry_run": dry_run}

  async def preview(self, org: UUID, version_id: UUID, item_id: UUID | None = None) -> dict:
    p = await self.plan(org, version_id, item_id, lock=False)
    return self._out(p, dry_run=True, quantity_after=projected(p["item"], p["active"], p["mine"], p["delta"]))

  async def apply(self, org: UUID, version_id: UUID, user_id: UUID, item_id: UUID | None = None) -> dict:
    p = await self.plan(org, version_id, item_id, lock=True)
    item, mine, state = p["item"], p["mine"], p["state"]
    p["before"] = item.quantity
    if state in (UNCHANGED, NOTHING):
      return self._out(p, dry_run=False, quantity_after=item.quantity)
    item, _ = await self.eng._item_for_edit(org, item.id)
    p["item"] = item
    why = "Replaced by the current audited steel." if p["delta"] != 0 else "The project's steel line no longer takes the audited figure, or no finding is accepted."
    for a in mine:
      a.revoked_at, a.revoked_by_user_id, a.revoke_reason = _now(), user_id, why
    await self.session.flush()
    adj = None
    if p["delta"] != 0:
      adj = await self.eng._add_adjustment(org, item, user_id, "DELTA", p["delta"], reason_of(p["figs"], p["effect"]))
    else:
      self.eng._apply_quantities(item, [a for a in p["active"] if a not in mine])
      item.version += 1
      await self.eng.items.update(item)
    await self.session.commit()
    for a in mine:
      await self.eng.audit.log(org, user_id, AuditEntityType.BOQ_ADJUSTMENT, a.id, AuditAction.UPDATE, f'Revoked the audited steel adjustment on "{item.material_name}"')
    if adj is not None:
      await self.eng.audit.log(org, user_id, AuditEntityType.BOQ_ADJUSTMENT, adj.id, AuditAction.CREATE, f'DELTA adjustment {p["delta"]} on "{item.material_name}": {adj.reason[:200]}')
    return self._out(p, dry_run=False, quantity_after=item.quantity, adjustment_id=adj.id if adj is not None else None, revoked=len(mine))
