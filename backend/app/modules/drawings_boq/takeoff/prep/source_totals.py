from __future__ import annotations
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import func, select
from app.modules.projects.repository import ProjectRepository
from app.core.exceptions import TraceException
from app.modules.drawings_boq.finish_schedule.common import work_item_catalog
from app.modules.drawings_boq.models import CalculationRun, QuantityLedger

SOURCE_ORDER = ("MODEL", "PDF_TAKEOFF", "DERIVED", "SCHEDULE_IMPORT", "MANUAL", "ESTIMATE")
ZERO = Decimal("0")
ROW_CAP = 100

def _q(value) -> str:
  """A plain decimal string to 6 places with no trailing zeros (never scientific notation)."""
  if value is None:
    return "0"
  text = format(Decimal(str(value)).quantize(Decimal("0.000001")), "f")
  return text.rstrip("0").rstrip(".") if "." in text else text

def build_items(rows: list, names: dict) -> list:
  by: dict = {}
  for code, unit, source, quantity, count in rows:
    slot = by.setdefault((code, unit), {"sources": {}, "rows": 0})
    slot["sources"][source] = slot["sources"].get(source, ZERO) + Decimal(str(quantity or 0))
    slot["rows"] += int(count or 0)
  out = []
  
  for (code, unit), slot in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][1])):
    total = sum(slot["sources"].values(), ZERO)
    present = [s for s in SOURCE_ORDER if slot["sources"].get(s, ZERO) != 0] + sorted(s for s in slot["sources"] if s not in SOURCE_ORDER and slot["sources"][s] != 0)
    out.append({
      "work_item_code": code, "name": names.get(code), "unit": unit, "total": _q(total), "rows": slot["rows"],
      "sources": [{"source": s, "quantity": _q(slot["sources"][s])} for s in present],
      "mixed": len(present) > 1,
    })
  return out

def reconciliation_of(stats: dict) -> dict:
  t = (stats or {}).get("pdf_takeoff") or {}
  def count(key):
    v = t.get(key)
    return len(v) if isinstance(v, (list, tuple, dict)) else int(v or 0)
  def rows(key):
    v = t.get(key)
    return [dict(x) for x in v[:ROW_CAP] if isinstance(x, dict)] if isinstance(v, (list, tuple)) else []
  return {"replaced": count("replaced"), "variances": count("variances"), "not_counted": count("not_counted"), "verified": count("verified"),
    "tolerance_pct": str(t["tolerance_pct"]) if t.get("tolerance_pct") is not None else None,
    "replaced_rows": rows("replaced"), "variance_rows": rows("variances"), "not_counted_rows": rows("not_counted")}

async def project_source_totals(session: AsyncSession, org: UUID, project_id: UUID) -> dict:
  if await ProjectRepository(session).get_by_id_and_org(project_id, org) is None:
    raise TraceException("Project not found.", status_code=404, code="PROJECT_NOT_FOUND")
  run = (await session.execute(select(CalculationRun).where(CalculationRun.organization_id == org, CalculationRun.project_id == project_id, CalculationRun.status == "COMPLETED")
    .order_by(CalculationRun.completed_at.desc().nullslast(), CalculationRun.id).limit(1))).scalars().first()
  
  if run is None:
    return {"run": None, "items": [], "reconciliation": reconciliation_of({}), "mixed_items": 0}
  rows = (await session.execute(select(QuantityLedger.work_item_code, QuantityLedger.unit, QuantityLedger.source_kind, func.sum(QuantityLedger.quantity_net), func.count(QuantityLedger.id))
    .where(QuantityLedger.organization_id == org, QuantityLedger.run_id == run.id).group_by(QuantityLedger.work_item_code, QuantityLedger.unit, QuantityLedger.source_kind))).all()
  catalog = await work_item_catalog(session, org, {r[0] for r in rows})
  items = build_items([tuple(r) for r in rows], {c: w.description for c, w in catalog.items()})
  return {"run": {"id": run.id, "completed_at": run.completed_at}, "items": items, "reconciliation": reconciliation_of(run.stats or {}), "mixed_items": sum(1 for i in items if i["mixed"])}
