from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract.floor_sources_service import FloorSourceService, _now
from uuid import UUID
from app.modules.drawings_boq.takeoff.extract import combine_plan as CP
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.takeoff.extract import floor_union as FU

class FloorUnionService(FloorSourceService):

  async def combine(self, org: UUID, user_id: UUID, drawing_id: UUID, floors: list | None = None, automatic: bool = False) -> dict:
    read, by = await self._read(org, drawing_id)
    view = FS.build(read)
    sheet_floor = {r["sheet_id"]: (None if (r["title"] or {}).get("composite") else (r["title"] or {}).get("level_hint")) for r in read}
    combined: list = []
    skipped: list = []
    touched: set = set()
    
    for entry in view["floors"]:
      floor = entry["floor"]
      if floors and floor not in floors:
        continue
      if entry["state"] not in ("DOUBLE", "COMBINED"):
        continue
      own = [s for s in entry["sources"] if not s["from_plans"]]
      among = [s for s in entry["sources"] if s["from_plans"]]
      if len(own) != 1 or len(among) != 1:
        skipped.append({"floor": floor, "code": "FLOOR_SOURCES_NOT_A_PAIR", "message": "This floor is read from more than two sheets, or from none that is a floor's own sheet, so the sheets cannot be laid over each other."})
        continue
    
      first, second = own[0], among[0]
      rows_first = CP.pool([c for c in by.get(first["sheet_id"], []) if FS.in_floor(c, floor, sheet_floor[first["sheet_id"]])])
      rows_second = CP.pool([c for c in by.get(second["sheet_id"], []) if FS.in_floor(c, floor, sheet_floor[second["sheet_id"]])])
      union = FU.combine(rows_first, rows_second)
      if not union.combined:
        skipped.append({"floor": floor, "code": "FLOOR_NOT_REGISTERED", "message": "The two sheets could not be laid over each other (too few marks in common). Choose one of them.",
          "reason": union.reason})
        continue
      plan = CP.decide(union, floor=floor, primary_page=first["page_no"], secondary_page=second["page_no"])
      changed = CP.apply_decisions(plan, user_id=user_id, now=_now())
      
      for row in rows_first + rows_second:
        if (row.facts or {}).get(CP.STAMP) is not None or CP.combined_away(row):
          touched.add(row.sheet_id)
      if plan["blocked"]:
        skipped += [{**b, "message": "Both sheets have this item accepted. Delete one of the measurements."} for b in plan["blocked"]]
      combined.append({"floor": floor, "sheet_id": str(first["sheet_id"]), "page_no": first["page_no"], "other_page_no": second["page_no"], "combined": True,
        "same": plan["same"], "added": plan["added"], "derived_set_aside": plan["derived_set_aside"], "set_aside": len(plan["reject"]), "restored": len(plan["restore"]), "changed": changed,
        "registration": union.registration.brief(), "count_differs": len(FU.counts_differ(union))})
    if any(c["changed"] or c["restored"] for c in combined):
      await self.core._log(org, user_id, drawing_id, AuditAction.UPDATE,
        ("Combined the sheets of " if automatic else "Combined the two sheets of ") + ", ".join(f"{c['floor'].lower()} (pages {c['page_no']} and {c['other_page_no']})" for c in combined)
        + f": {sum(c['set_aside'] for c in combined)} repeated items set aside, {sum(c['added'] for c in combined)} kept from the second sheet")
    await self.session.flush()
    
    if touched:
      await self._sync_register(org, touched)
    await self.session.commit()
    return {"combined": combined, "skipped": skipped, "floors": self._view(drawing_id, read)}

  async def _default_floors(self, org: UUID, user_id: UUID, drawing_id: UUID) -> list:
    out = await self.combine(org, user_id, drawing_id, automatic=True)
    rest = await super()._default_floors(org, user_id, drawing_id)
    return [*out["combined"], *rest]
