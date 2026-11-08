from __future__ import annotations
from app.modules.drawings_boq.takeoff.completeness import ledger as LG
from app.engine.catalogue import loader as CAT
from app.modules.drawings_boq.pricing.billing import group as G, profiles as P, run_lines as RL
from decimal import Decimal
from uuid import UUID
from app.modules.drawings_boq.takeoff.questions.service import QuestionsService
from app.modules.drawings_boq.models import CalculationRun, BuildingLevel, QuantityLedger
from app.core.exceptions import TraceException
from app.engine.catalogue import conventions as CV
from app.engine.catalogue import confidence as CFG
from app.modules.drawings_boq.takeoff.completeness import confidence as CONF
from app.modules.drawings_boq.takeoff.completeness import self_check as SC
from app.modules.drawings_boq import company_conventions as CCV
from sqlalchemy import select

BILLABLE = (LG.MEASURED, LG.ASSUMED)

def primary_yield(item, unit: str):
  if unit != item.unit:
    return None
  return next((y for y in item.yields if y.unit == unit), None)

def measured_from_entries(entries: list, items: dict | None = None) -> dict:
  items = items if items is not None else {i.id: i for i in CAT.items()}
  out = {"measured": [], "assumed": set(), "ranges": {}, "not_measured": [], "unavailable": []}
  seen_unavailable = set()
  claimed: dict = {}
  
  for e in entries:
    state = e["state"]
    if state == LG.NOT_APPLICABLE:
      continue
    item = items.get(e["element"])
    q = e.get("quantity")
    
    floor = None if e["floor"] in (LG.ALL, None) else e["floor"]
    if state not in BILLABLE or not q or item is None:
      why = (e.get("reasons") or [])[:3]
      out["not_measured"].append({"element": e["element"], "name": e.get("name"), "floor": floor, "state": state, "reasons": why,
        "quantity": None if not q else {"value": q["value"], "unit": q["unit"]}})
      continue
    
    y = primary_yield(item, q["unit"])
    if y is None:
      out["not_measured"].append({"element": e["element"], "name": e.get("name"), "floor": floor, "state": state, "reasons": [f"the quantity is in {q['unit']} and the item's yield is in {item.unit}"], "quantity": {"value": q["value"], "unit": q["unit"]}})
      continue
    families = frozenset(b.line for b in item.billing.PRIVATE_QS if b.qty == y.qty)
    same = claimed.get((families, floor, q["value"], q["unit"])) if families else None
    if same is not None:
      out["not_measured"].append({"element": e["element"], "name": e.get("name"), "floor": floor, "state": state, "reasons": [f"the same measurement as {same}: they bill the same line family, so it is billed once, under {same}"],
        "quantity": {"value": q["value"], "unit": q["unit"]}})
      continue
    
    if families:
      claimed[(families, floor, q["value"], q["unit"])] = item.id
    out["measured"].append(G.Measured(item.id, y.qty, Decimal(str(q["value"])), q["unit"], floor))
    if state == LG.ASSUMED:
      out["assumed"].add((item.id, y.qty))
    if q.get("range"):
      out["ranges"][(item.id, floor)] = (float(q["range"][0]), float(q["range"][1]))
    for other in item.yields:
      if other.qty != y.qty and (item.id, other.qty) not in seen_unavailable:
        seen_unavailable.add((item.id, other.qty))
        out["unavailable"].append({"element": item.id, "name": item.name, "qty": other.qty, "unit": other.unit, "why": "the ledger holds the primary quantity of an item only"})
        
  out["assumed"] = frozenset(out["assumed"])
  return out

def range_factors(billed: G.Billed, ranges: dict) -> dict:
  acc: dict = {}
  
  for line in billed.lines:
    for item_id, _key, floor, value, _unit in line.sources:
      lo_hi = ranges.get((item_id, floor))
      v = float(value)
      a = acc.setdefault(line.code, [0.0, 0.0, 0.0, False])
      a[2] += v
      if lo_hi:
        a[0] += lo_hi[0]; a[1] += lo_hi[1]; a[3] = True
      else:
        a[0] += v; a[1] += v
  return {c: (a[0] / a[2], a[1] / a[2]) for c, a in acc.items() if a[3] and a[2]}

def _num(x: Decimal | None, places: int = 3):
  return None if x is None else float(round(x, places))

def view(billed: G.Billed, parts: dict, measured: list, profile: P.Profile) -> dict:
  accounted, totals = G.accounted_for(billed), G.measured_totals(measured)
  lost = {k: _num(totals[k] - accounted.get(k, Decimal(0))) for k in totals if abs(totals[k] - accounted.get(k, Decimal(0))) > Decimal("0.0005")}
  
  return {
    "profile": profile.id,
    "lines": [{"code": l.code, "unit": l.unit, "qty": _num(l.qty), "spec": None if not l.spec else {"name": l.spec[0], "value": l.spec[1], "basis": l.spec[2]}, "floor": l.floor,
      "sources": [{"element": s[0], "qty_key": s[1], "floor": s[2], "value": _num(s[3]), "unit": s[4], "assumed": (s[0], s[1]) in parts["assumed"]} for s in l.sources]} for l in billed.lines],
    "included": [{"qty_key": k, "where": w, "value": _num(v), "unit": u} for k, w, v, u in billed.included],
    "rate_needed": [{"element": i, "qty_key": k, "value": _num(v), "unit": u, "why": why} for i, k, v, u, why in billed.rate_needed],
    "questions": billed.questions,
    "not_measured": parts["not_measured"],
    "unavailable": parts["unavailable"],
    "counts": {"measured_entries": len(measured), "assumed_entries": sum(1 for m in measured if (m.item_id, m.qty_key) in parts["assumed"]), "not_measured": len(parts["not_measured"])},
    "reconciled": not lost,
    "lost": {f"{k[0]}:{k[1]}:{k[2]}": v for k, v in lost.items()},
  }

class BillingService(QuestionsService):
  async def run_rows(self, org: UUID, project_id: UUID) -> tuple:
    run = (await self.session.execute(select(CalculationRun).where(CalculationRun.organization_id == org, CalculationRun.project_id == project_id, CalculationRun.status == "COMPLETED")
      .order_by(CalculationRun.completed_at.desc().nullslast(), CalculationRun.id).limit(1))).scalars().first()
    if run is None:
      return None, [], {}
    
    got = (await self.session.execute(select(QuantityLedger.level_id, QuantityLedger.work_item_code, QuantityLedger.quantity_net, QuantityLedger.unit, QuantityLedger.formula_code,
      QuantityLedger.trace).where(QuantityLedger.organization_id == org, QuantityLedger.run_id == run.id))).all()
    rows = [{"level_id": r[0], "work_item_code": r[1], "quantity": r[2], "unit": r[3], "formula_code": r[4], "trace": r[5]} for r in got]
    ids = {r["level_id"] for r in rows if r["level_id"]}
    names = {}
    
    if ids:
      names = {str(i): n for i, n in (await self.session.execute(select(BuildingLevel.id, BuildingLevel.name).where(BuildingLevel.id.in_(ids)))).all()}
    return run, rows, {k: RL.floor_name(v) for k, v in names.items()}

  async def entries(self, org: UUID, project_id: UUID) -> tuple:
    _drawings, snapshot, answers = await self._project(org, project_id)
    if snapshot is None:
      return None, {"run": None, "lines": 0, "no_family": 0, "no_unit": []}
    run, rows, floor_of = await self.run_rows(org, project_id)
    given = RL.lines_from_rows(rows, floor_of)
    
    evidence = {**snapshot["evidence"], "lines": given["lines"]}
    on = CV.on_ids(await CCV.in_force(self.session, org))
    entries = LG.build(CAT.items(), snapshot["facts"], evidence, on, snapshot.get("methods") or {}, answers)
    checks = SC.current(entries, evidence, snapshot.get("checks"))
    confidence = {"shown": CFG.shown(), "calibrated": CFG.doc().get("calibrated"), "elements": CONF.of_entries(entries, evidence, checks)}
    return entries, {"run": None if run is None else {"id": run.id, "completed_at": run.completed_at}, "lines": len(given["lines"]), "no_family": given["no_family"], "no_unit": given["no_unit"],
      "checks": [{"check": c["check"], "result": c["result"], "detail": c["detail"]} for c in checks], "confidence": confidence}

  async def billed(self, org: UUID, project_id: UUID, profile_id: str | None = None, decisions: dict | None = None) -> dict:
    try:
      profile = P.get(profile_id) if profile_id else P.get(P.DEFAULT_PROFILE)
    except ValueError:
      raise TraceException(f"'{profile_id}' is not a billing profile.", status_code=422, code="PROFILE_UNKNOWN")
    entries, source = await self.entries(org, project_id)
    head = {"project_id": project_id, "profiles": [{"id": p.id, "label": p.label} for p in P.all_profiles().values()], "source": source}
    if entries is None:
      return {**head, "has_ledger": False, "profile": profile.id, "lines": [], "included": [], "rate_needed": [], "questions": [], "not_measured": [], "unavailable": [],
        "counts": {"measured_entries": 0, "assumed_entries": 0, "not_measured": 0}, "reconciled": True, "lost": {}}
      
    parts = measured_from_entries(entries)
    billed = G.group(parts["measured"], profile, decisions)
    return {**head, "has_ledger": True, **view(billed, parts, parts["measured"], profile)}
