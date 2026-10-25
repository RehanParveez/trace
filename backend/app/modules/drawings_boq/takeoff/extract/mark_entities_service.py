from __future__ import annotations
from datetime import datetime, timezone
from app.modules.drawings_boq.takeoff.extract.crosschecks import _sheet_floor
from app.modules.drawings_boq.takeoff.extract.layout_groups_service import LayoutGroupService
from uuid import UUID
from app.modules.drawings_boq.takeoff.extract import accept_guard as AG
from app.modules.drawings_boq.takeoff.extract import mark_entities as ME
from app.modules.drawings_boq.takeoff.extract.ready import mark_skip
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.takeoff import corrections as CR
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.extract import layout_groups as LG

def _now() -> datetime:
  return datetime.now(timezone.utc)

def _rows(sheet: dict, entity: dict) -> list:
  sf = _sheet_floor(sheet)
  want = "SITE" if entity["category"] == "SITE" else entity["floor"]
  return [c for c in sheet["candidates"] if AG.mark_key(c.category, c.tag, c.facts) == (entity["category"], entity["mark"]) and ME.floor_of_item(c, sf) == want]

class MarkEntityService(LayoutGroupService):

  @staticmethod
  def _marks(drawing_id: UUID, read: list) -> dict:
    plans = [s for s in read if "title" in s and "stats" in s]
    return {"drawing_id": drawing_id, **ME.build(plans, mark_skip(LG.undecided_sheets(plans)))}

  async def mark_entities(self, org: UUID, drawing_id: UUID) -> dict:
    read, _ = await self._read(org, drawing_id)
    return self._marks(drawing_id, read)

  async def choose_marks(self, org: UUID, user_id: UUID, drawing_id: UUID, payload) -> dict:
    read, _ = await self._read(org, drawing_id)
    view = self._marks(drawing_id, read)
    entries = {e["key"]: e for e in view["entities"]}
    sheets = {s["sheet_id"]: s for s in read}

    if payload.use_suggested:
      wanted = [(e["key"], e["suggested_sheet_id"]) for e in view["entities"] if e["state"] == ME.DOUBLE and e["suggested_sheet_id"]]
    else:
      wanted = [(c.key, c.sheet_id) for c in payload.choices or []]
    chosen: list = []
    blocked: list = []
    set_aside = restored = 0
    touched: set = set()

    for key, sheet_id in wanted:
      entity = entries.get(key)
      if entity is None or not entity["choosable"]:
        blocked.append({"key": key, "code": "MARK_NOT_FOUND", "message": "This mark is not listed on more than one sheet, so there is nothing to choose."})
        continue
    
      plan = ME.plan_choice(entity, sheet_id)
      if plan["blocked"] == "MARK_OTHER_SHEET_ACCEPTED":
        pages = ", ".join(str(p) for p in plan["pages"])
        blocked.append({"key": key, "code": plan["blocked"], "message": f"{entity['tag'] or entity['mark']}: page {pages} already has it accepted. Delete that measurement first, or use that page."})
        continue
      if plan["blocked"]:
        blocked.append({"key": key, "code": plan["blocked"], "message": "Nothing to choose here."})
        continue

      keep = plan["keep"]
      away = [c for s in plan["set_aside"] for c in _rows(sheets[s["sheet_id"]], entity) if c.decision == "NEW"]
      back = [c for c in _rows(sheets[keep["sheet_id"]], entity) if ME.is_mine(c)]
      for c in away:
        c.decision, c.decided_by_user_id, c.decided_at = "REJECTED", user_id, _now()
        c.facts = {**(c.facts or {}), FS.SET_ASIDE: {"by": ME.BY, "page_no": keep["page_no"]}}
        touched.add(c.sheet_id)
      for c in back:
        c.decision, c.decided_by_user_id, c.decided_at = "NEW", None, None
        c.facts = {k: v for k, v in (c.facts or {}).items() if k != FS.SET_ASIDE}
        touched.add(c.sheet_id)
      set_aside += len(away)
      restored += len(back)

      chosen.append({"key": key, "sheet_id": str(keep["sheet_id"]), "page_no": keep["page_no"], "tag": entity["tag"], "set_aside": len(away), "restored": len(back)})
      project_id = next((c.project_id for c in [*away, *back]), None)
      if project_id is not None:
        await CR.record(self.session, org=org, user_id=user_id, project_id=project_id, drawing_id=drawing_id, sheet_id=keep["sheet_id"], kind=CR.MARK_CHOICE,
          subject=f"{entity['category']} {entity['tag'] or entity['mark']}",
          before={"pages": [s["page_no"] for s in entity["sources"]], "state": entity["state"], "suggested": str(entity["suggested_sheet_id"]) if entity["suggested_sheet_id"] else None},
          after={"governing_page": keep["page_no"], "set_aside": len(away), "restored": len(back)})
    if chosen:
      await self.core._log(org, user_id, drawing_id, AuditAction.UPDATE,
        "Chose the sheet to use for marks read on several sheets: " + ", ".join(f"{c['tag']} (page {c['page_no']})" for c in chosen[:12]) + (f" and {len(chosen) - 12} more" if len(chosen) > 12 else "")
        + f"; {set_aside} items set aside, {restored} restored")

    await self.session.flush()
    if touched:
      await self._sync_register(org, touched)
    await self.session.commit()
    return {"chosen": chosen, "set_aside": set_aside, "restored": restored, "blocked": blocked, "marks": self._marks(drawing_id, read)}
