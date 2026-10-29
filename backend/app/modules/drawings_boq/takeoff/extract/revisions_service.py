from __future__ import annotations
from datetime import datetime, timezone
from app.modules.drawings_boq.takeoff.extract.floor_sources_service import FloorSourceService
from uuid import UUID
from app.modules.drawings_boq.takeoff.extract import revisions as RV
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.takeoff import corrections as CR

def _now() -> datetime:
  return datetime.now(timezone.utc)

class RevisionService(FloorSourceService):

  @staticmethod
  def _groups(drawing_id: UUID, read: list) -> dict:
    return {"drawing_id": drawing_id, **RV.build(read)}

  async def revisions(self, org: UUID, drawing_id: UUID) -> dict:
    read, _ = await self._read(org, drawing_id)
    return self._groups(drawing_id, read)

  async def choose_revisions(self, org: UUID, user_id: UUID, drawing_id: UUID, payload) -> dict:
    read, by = await self._read(org, drawing_id)
    view = RV.build(read)
    entries = {g["id"]: g for g in view["groups"]}
    
    if payload.use_default:
      wanted = [(g["id"], g["default"]) for g in view["groups"] if g["state"] == "OPEN" and g["default"]]
    else:
      wanted = [(c.id, c.value) for c in payload.choices or []]
    chosen: list = []
    blocked: list = []
    set_aside = restored = 0
    touched: set = set()
    for gid, value in wanted:
      entry = entries.get(gid)
      if entry is None:
        blocked.append({"id": gid, "code": "OPTION_NOT_FOUND", "message": "This option or revision is not listed for this drawing, so there is nothing to choose."})
        continue
    
      plan = RV.plan_choice(entry, value, {})
      if plan["blocked"] == "OPTION_OTHER_ACCEPTED":
        pages = ", ".join(str(p) for p in plan["pages"])
        blocked.append({"id": gid, "code": plan["blocked"], "message": f"Page {pages} already has measurements. Delete them first, or use that page."})
        continue
      if plan["blocked"]:
        blocked.append({"id": gid, "code": plan["blocked"], "message": "That is not one of the values this sheet is printed with."})
        continue
      keep = plan["keep"]
      away = [c for o in plan["set_aside"] for sid in o["sheet_ids"] for c in by.get(sid, []) if c.decision == "NEW"]
      back = [c for sid in keep["sheet_ids"] for c in by.get(sid, []) if c.decision == "REJECTED" and ((c.facts or {}).get(FS.SET_ASIDE) or {}).get("by") == RV.BY]
      
      for c in away:
        c.decision, c.decided_by_user_id, c.decided_at = "REJECTED", user_id, _now()
        c.facts = {**(c.facts or {}), FS.SET_ASIDE: {"by": RV.BY, "page_no": keep["pages"][0]}}
        touched.add(c.sheet_id)
      for c in back:
        c.decision, c.decided_by_user_id, c.decided_at = "NEW", None, None
        c.facts = {k: v for k, v in (c.facts or {}).items() if k != FS.SET_ASIDE}
        touched.add(c.sheet_id)
      set_aside += len(away)
      restored += len(back)
      
      chosen.append({"id": gid, "kind": entry["kind"], "value": value, "pages": keep["pages"], "set_aside": len(away), "restored": len(back)})
      project_id = next((c.project_id for c in [*away, *back]), None)
      
      if project_id is not None:
        await CR.record(self.session, org=org, user_id=user_id, project_id=project_id, drawing_id=drawing_id, sheet_id=keep["sheet_ids"][0], kind=CR.LAYOUT_CHOICE, subject=f"page {keep['pages'][0]}",
          before={"kind": entry["kind"], "pages": sorted(p for o in entry["options"] for p in o["pages"]), "default": entry["default"]},
          after={"kind": entry["kind"], "value": value, "governing_page": keep["pages"][0], "set_aside": len(away), "restored": len(back)})
    if chosen:
      await self.core._log(org, user_id, drawing_id, AuditAction.UPDATE,
        "Chose the " + ("option built or revision current" if len({c["kind"] for c in chosen}) > 1 else chosen[0]["kind"].lower() + " in force") + ": " + ", ".join(f"page {c['pages'][0]}" for c in chosen) + f"; {set_aside} items set aside, {restored} restored")
    await self.session.flush()
    if touched:
      await self._sync_register(org, touched)
    await self.session.commit()
    return {"chosen": chosen, "set_aside": set_aside, "restored": restored, "blocked": blocked, "revisions": self._groups(drawing_id, read)}
