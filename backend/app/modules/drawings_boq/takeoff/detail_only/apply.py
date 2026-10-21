from __future__ import annotations
from uuid import UUID
from app.modules.drawings_boq.takeoff.detail_only.repository import DetailOnlyRepository
from app.modules.drawings_boq.takeoff.detail_only import detail_only as DO

async def apply_decisions(svc, org: UUID, drawing_id: UUID) -> set:
  decisions = await DetailOnlyRepository(svc.session).decisions(org, drawing_id)
  if not decisions:
    return set()
  sheets = await svc.core.repo.sheets(org, drawing_id)
  rows = await svc.repo.candidates(org, [s.id for s in sheets])
  by_key = {(r.sheet_id, r.ckey): r for r in rows}
  touched: set = set()
  for d in decisions:
    if d.kind == DO.COLUMN_MARK:
      row = by_key.get((d.sheet_id, d.ckey))
      if row is not None and DO.apply_column_mark(row, d.mark, str(d.id)):
        touched.add(row.sheet_id)
    elif d.kind == DO.BEAM_DEPTH and d.value_mm is not None:
      for row in rows:
        if DO.apply_beam_depth(row, d.mark, float(d.value_mm), str(d.id), (d.basis or {}).get("from") or []):
          touched.add(row.sheet_id)
  await svc.session.flush()
  return touched