from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.takeoff.extract import floor_sources as FS
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from app.modules.drawings_boq.takeoff.extract.pipeline import _status
from app.modules.drawings_boq.takeoff.extract.floor_sources_schemas import ChooseFloorSourcesRequest

def _now() -> datetime:
  return datetime.now(timezone.utc)

OTHER_SHEET_FLAG = "FLOOR_READ_ON_OTHER_SHEET"

def clear_other_sheet_flag(rows: list) -> list:
  changed = []
  for c in rows:
    if c.decision == "REJECTED" or not any((n or {}).get("code") == OTHER_SHEET_FLAG for n in c.notes or []):
      continue
    c.notes = [n for n in c.notes if (n or {}).get("code") != OTHER_SHEET_FLAG]
    c.status = _status(c.notes)
    changed.append(c)
  return changed

class FloorSourceService(ExtractService):
  """The floors of a drawing, with the sheets each was read from, and the choice of which sheet to use."""

  async def _read(self, org: UUID, drawing_id: UUID) -> tuple:
    await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    exts = {e.sheet_id: e for e in await self.repo.extractions(org, [s.id for s in sheets])}
    rows = await self.repo.candidates(org, [s.id for s in sheets if s.id in exts])
    await self._heal(org, rows)
    by: dict = {}
    for r in rows:
      by.setdefault(r.sheet_id, []).append(r)
    read = [{"sheet_id": s.id, "page_no": s.page_no, "title": (s.prep_meta or {}).get("title"), "stats": exts[s.id].stats, "candidates": by.get(s.id, [])}
      for s in sheets if s.id in exts]
    return read, by

  @staticmethod
  def _view(drawing_id: UUID, read: list) -> dict:
    return {"drawing_id": drawing_id, **FS.build(read)}

  async def floor_sources(self, org: UUID, drawing_id: UUID) -> dict:
    read, _ = await self._read(org, drawing_id)
    return self._view(drawing_id, read)

  async def choose(self, org: UUID, user_id: UUID, drawing_id: UUID, payload, automatic: bool = False) -> dict:
    read, by = await self._read(org, drawing_id)
    view = FS.build(read)
    entries = {f["floor"]: f for f in view["floors"]}
    
    if payload.use_suggested:
      wanted = [(f["floor"], f["suggested_sheet_id"]) for f in view["floors"] if f["state"] == "DOUBLE" and f["suggested_sheet_id"]]
    else:
      wanted = [(c.floor, c.sheet_id) for c in payload.choices or []]
    chosen: list = []
    blocked: list = []
    kept_by_floor: dict = {f["floor"]: f["chosen_sheet_id"] for f in view["floors"] if f["state"] == "CHOSEN" and f["chosen_sheet_id"]}
    set_aside = restored = 0
    touched: set = set()
    for floor, sheet_id in wanted:
      entry = entries.get(floor)
      if entry is None:
        blocked.append({"floor": floor, "code": "FLOOR_NOT_FOUND", "message": "This floor was not read from any sheet of the drawing."})
        continue
      plan = FS.plan_choice(entry, sheet_id)
      if plan["blocked"] == "FLOOR_OTHER_SOURCE_ACCEPTED":
        pages = ", ".join(str(p) for p in plan["pages"])
        blocked.append({"floor": floor, "code": plan["blocked"], "message": f"Page {pages} already has measurements for this floor. Delete them first, or use that page."})
        continue
      if plan["blocked"]:
        blocked.append({"floor": floor, "code": plan["blocked"], "message": "This floor is read from one sheet only, or from sheets that do not hold several plans, so there is nothing to choose."})
        continue
    
      keep = plan["keep"]
      sheet_floor = {r["sheet_id"]: (None if (r["title"] or {}).get("composite") else (r["title"] or {}).get("level_hint")) for r in read}
      kept_by_floor[floor] = keep["sheet_id"]
      away = [c for s in plan["set_aside"] for c in by.get(s["sheet_id"], []) if FS.in_floor(c, floor, sheet_floor[s["sheet_id"]]) and c.decision == "NEW"]
      back = [c for c in by.get(keep["sheet_id"], []) if FS.in_floor(c, floor, sheet_floor[keep["sheet_id"]]) and c.decision == "REJECTED" and FS.is_set_aside(c)]
      for c in away:
        c.decision, c.decided_by_user_id, c.decided_at = "REJECTED", user_id, _now()
        c.facts = {**(c.facts or {}), FS.SET_ASIDE: {"by": FS.SET_ASIDE_BY, "page_no": keep["page_no"]}}
        touched.add(c.sheet_id)
        
      for c in back:
        c.decision, c.decided_by_user_id, c.decided_at = "NEW", None, None
        c.facts = {k: v for k, v in (c.facts or {}).items() if k != FS.SET_ASIDE}
        touched.add(c.sheet_id)
      set_aside += len(away)
      restored += len(back)
      chosen.append({"floor": floor, "sheet_id": str(keep["sheet_id"]), "page_no": keep["page_no"], "set_aside": len(away), "restored": len(back)})
    own_floor = {r["sheet_id"]: (None if (r["title"] or {}).get("composite") else (r["title"] or {}).get("level_hint")) for r in read}
    cleared = 0
    for floor, sid in kept_by_floor.items():
      changed = clear_other_sheet_flag([c for c in by.get(sid, []) if FS.in_floor(c, floor, own_floor.get(sid))])
      touched.update(c.sheet_id for c in changed)
      cleared += len(changed)
    if chosen:
      await self.core._log(org, user_id, drawing_id, AuditAction.UPDATE,
        ("Used the floor's own sheet after the read, for " if automatic else "Chose the sheet to use for ") + ", ".join(f"{c['floor'].lower()} (page {c['page_no']})" for c in chosen) + f": {set_aside} items set aside, {restored} brought back")
    await self.session.flush()
    if touched:
      await self._sync_register(org, touched)
    await self.session.commit()
    return {"chosen": chosen, "set_aside": set_aside, "restored": restored, "flags_cleared": cleared, "blocked": blocked, "floors": self._view(drawing_id, read)}

  async def _default_floors(self, org: UUID, user_id: UUID, drawing_id: UUID) -> list:
    out = await self.choose(org, user_id, drawing_id, ChooseFloorSourcesRequest(use_suggested=True), automatic=True)
    return out["chosen"]

  async def extract_sheet(self, org: UUID, sheet_id: UUID, user_id: UUID, payload, regions_only: bool = False) -> dict:
    out = await super().extract_sheet(org, sheet_id, user_id, payload, regions_only=regions_only)
    if not getattr(payload, "choose_floors", True):
      return out
    sheet = await self.core._sheet(org, sheet_id)
    chosen = await self._default_floors(org, user_id, sheet.drawing_id)
    if chosen:
      out.update(await self._list(org, sheet))
    out["floors_chosen"] = chosen
    return out
