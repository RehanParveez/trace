from __future__ import annotations
from datetime import datetime, timezone
from app.modules.drawings_boq.takeoff.extract.floor_sources_service import FloorSourceService
from uuid import UUID
from app.modules.drawings_boq.takeoff.extract import layout_groups as LG
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.takeoff import corrections as CR

def _now() -> datetime:
  return datetime.now(timezone.utc)

class LayoutGroupService(FloorSourceService):

  @staticmethod
  def _layouts(drawing_id: UUID, read: list) -> dict:
    return {"drawing_id": drawing_id, **LG.build(read)}

  async def layout_groups(self, org: UUID, drawing_id: UUID) -> dict:
    read, _ = await self._read(org, drawing_id)
    return self._layouts(drawing_id, read)

  async def choose_layouts(self, org: UUID, user_id: UUID, drawing_id: UUID, payload) -> dict:
    read, by = await self._read(org, drawing_id)
    view = LG.build(read)
    entries = {g["key"]: g for g in view["groups"]}

    if payload.use_suggested:
      wanted = [(g["key"], g["suggested_sheet_id"]) for g in view["groups"] if g["state"] == "DOUBLE" and g["suggested_sheet_id"]]
    else:
      wanted = [(c.key, c.sheet_id) for c in payload.choices or []]
    chosen: list = []
    blocked: list = []
    set_aside = restored = 0
    touched: set = set()
    for key, sheet_id in wanted:
      entry = entries.get(key)
      if entry is None or not entry["choosable"]:
        blocked.append({"key": key, "code": "LAYOUT_NOT_FOUND", "message": "These sheets are not listed as carrying the same layout, so there is nothing to choose."})
        continue
      plan = FS.plan_choice(entry, sheet_id)
      if plan["blocked"] == "FLOOR_OTHER_SOURCE_ACCEPTED":
        pages = ", ".join(str(p) for p in plan["pages"])
        blocked.append({"key": key, "code": "LAYOUT_OTHER_SOURCE_ACCEPTED", "message": f"Page {pages} already has measurements from this layout. Delete them first, or use that page."})
        continue
      if plan["blocked"]:
        blocked.append({"key": key, "code": plan["blocked"], "message": "Nothing to choose here."})
        continue

      keep = plan["keep"]
      away = [c for s in plan["set_aside"] for c in by.get(s["sheet_id"], []) if LG.in_layout(c) and c.decision == "NEW"]
      back = [c for c in by.get(keep["sheet_id"], []) if LG.in_layout(c) and c.decision == "REJECTED" and LG.is_layout_set_aside(c)]

      for c in away:
        c.decision, c.decided_by_user_id, c.decided_at = "REJECTED", user_id, _now()
        c.facts = {**(c.facts or {}), FS.SET_ASIDE: {"by": LG.BY, "page_no": keep["page_no"]}}
        touched.add(c.sheet_id)
      for c in back:
        c.decision, c.decided_by_user_id, c.decided_at = "NEW", None, None
        c.facts = {k: v for k, v in (c.facts or {}).items() if k != FS.SET_ASIDE}
        touched.add(c.sheet_id)
      set_aside += len(away)
      restored += len(back)
      chosen.append({"key": key, "sheet_id": str(keep["sheet_id"]), "page_no": keep["page_no"], "set_aside": len(away), "restored": len(back)})
      project_id = next((c.project_id for c in [*away, *back]), None)
      if project_id is not None:
        await CR.record(self.session, org=org, user_id=user_id, project_id=project_id, drawing_id=drawing_id, sheet_id=keep["sheet_id"], kind=CR.LAYOUT_CHOICE, subject=f"page {keep['page_no']}",
          before={"pages": [s["page_no"] for s in entry["sources"]], "suggested": str(entry["suggested_sheet_id"]) if entry["suggested_sheet_id"] else None},
          after={"governing_page": keep["page_no"], "set_aside": len(away), "restored": len(back)})

    if chosen:
      await self.core._log(org, user_id, drawing_id, AuditAction.UPDATE,
        "Chose the sheet to use for the layout printed on several sheets: " + ", ".join(f"page {c['page_no']}" for c in chosen) + f"; {set_aside} items set aside, {restored} restored")
    await self.session.flush()
    if touched:
      await self._sync_register(org, touched)
    await self.session.commit()
    return {"chosen": chosen, "set_aside": set_aside, "restored": restored, "blocked": blocked, "layouts": self._layouts(drawing_id, read)}
