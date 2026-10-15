from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drawings_boq.takeoff.repository import TakeoffRepository
from app.modules.audit.service import AuditLogService
from uuid import UUID
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff import repository as repo_mod
from app.modules.drawings_boq.takeoff import frame_views as FV
from sqlalchemy import delete, select
from app.modules.audit.models import AuditAction
from app.modules.drawings_boq.finish_schedule.common import audit_entity
from app.modules.drawings_boq.models import TakeoffViewAlignment

MAX_SHIFT_MM = 1_000_000.0

class FrameService:
  """Where the views of one drawing sit on the building frame, and what people decided about it. The engine places views on its own (matching columns, else the
  outline) and grades them ASSUMED; a person's confirm or placement is stored here and wins over the engine's guess on the next run."""

  def __init__(self, session: AsyncSession):
    self.session = session
    self.repo = TakeoffRepository(session)
    self.audit = AuditLogService(session)

  async def _drawing(self, org: UUID, drawing_id: UUID):
    d = await self.repo.drawing(org, drawing_id)
    if d is None:
      raise TraceException("Drawing not found.", status_code=404, code="DRAWING_NOT_FOUND")
    return d

  async def _state(self, org: UUID, drawing_id: UUID) -> dict:
    inputs = await repo_mod.load_takeoff_inputs(self.session, org, [drawing_id])
    group = str(drawing_id)
    stored = (await repo_mod.load_stored_alignments(self.session, org, [drawing_id])).get(group) or {"reference": None, "placements": {}}
    formwork = inputs.formwork if inputs else ()
    group_of_sheet = {f.sheet_id: group for f in formwork}
    views = FV.view_points(formwork, group_of_sheet).get(group, {})
    frame = FV.solve_frames({group: views}, {group: stored})[group] if views else None
    return {"group": group, "formwork": formwork, "group_of_sheet": group_of_sheet, "views": views, "stored": stored, "frame": frame}

  async def frame(self, org: UUID, drawing_id: UUID) -> dict:
    await self._drawing(org, drawing_id)
    s = await self._state(org, drawing_id)
    if s["frame"] is None:
      return {"drawing_id": drawing_id, "reference": None, "origin_mm": [0.0, 0.0], "views": [], "status": "NONE", "open_views": [], "unplaced": [], "unconfirmed": []}
    frames = {s["group"]: s["frame"]}
    members = FV.placed_members(s["formwork"], s["group_of_sheet"], frames).get(s["group"], {})
    anchors = {k: len(v) for k, v in s["views"].items()}
    return {"drawing_id": drawing_id, **FV.describe(s["frame"], members, anchors, s["stored"])}

  async def _row(self, org: UUID, drawing_id: UUID, view: str) -> TakeoffViewAlignment | None:
    return (await self.session.execute(select(TakeoffViewAlignment).where(
      TakeoffViewAlignment.organization_id == org, TakeoffViewAlignment.drawing_id == drawing_id, TakeoffViewAlignment.frame_key == view).with_for_update())).scalar_one_or_none()

  def _need_view(self, s: dict, view: str) -> None:
    if s["frame"] is None or view not in s["frame"].alignments:
      raise TraceException("That view is not part of this drawing's frame.", status_code=422, code="FRAME_VIEW_UNKNOWN")

  async def place(self, org: UUID, drawing_id: UUID, user_id: UUID, view: str, action: str, dx_mm: float | None, dy_mm: float | None) -> dict:
    """CONFIRM keeps the engine's placement as a decision, SET stores the given shift, CLEAR hands the view back to the engine."""
    drawing = await self._drawing(org, drawing_id)
    s = await self._state(org, drawing_id)
    self._need_view(s, view)
    row = await self._row(org, drawing_id, view)
    
    if action == "CLEAR":
      if row is not None:
        await self.session.delete(row)
      what = "cleared the placement of"
    else:
      a = s["frame"].alignments[view]
      if action == "CONFIRM":
        if not a.usable:
          raise TraceException("That view has no placement to confirm; set one by hand.", status_code=422, code="FRAME_VIEW_UNPLACED")
        dx, dy, method = a.dx_mm, a.dy_mm, a.method if a.method != "REFERENCE" else "REFERENCE"
      else:
        if dx_mm is None or dy_mm is None or abs(dx_mm) > MAX_SHIFT_MM or abs(dy_mm) > MAX_SHIFT_MM:
          raise TraceException("Give the shift of this view in millimetres.", status_code=422, code="FRAME_SHIFT_INVALID")
        dx, dy, method = round(float(dx_mm), 2), round(float(dy_mm), 2), "MANUAL"
      if s["frame"].reference == view and action == "CONFIRM":
        
        await self._set_reference(org, drawing, user_id, view, s)
        what = "confirmed the reference view"
        await self._log(org, user_id, drawing_id, f"Frame: {what} {view}")
        await self.session.commit()
        return await self.frame(org, drawing_id)
      if row is None:
        row = TakeoffViewAlignment(organization_id=org, project_id=drawing.project_id, drawing_id=drawing_id, frame_key=view)
        self.session.add(row)
      if row.role == "REFERENCE":
        raise TraceException("The reference view cannot be shifted; pick another reference first.", status_code=422, code="FRAME_REFERENCE_FIXED")
      row.role, row.dx_mm, row.dy_mm, row.method, row.updated_by_user_id = "PLACEMENT", dx, dy, method[:20], user_id
      what = "confirmed" if action == "CONFIRM" else "placed"
    await self.session.flush()
    await self._log(org, user_id, drawing_id, f"Frame: {what} {view}")
    await self.session.commit()
    return await self.frame(org, drawing_id)

  async def _set_reference(self, org: UUID, drawing, user_id: UUID, view: str, s: dict) -> int:
    old = s["stored"].get("reference") or (s["frame"].reference if s["frame"] is not None else None)
    cleared = 0
    if old != view:
     
      res = await self.session.execute(delete(TakeoffViewAlignment).where(
        TakeoffViewAlignment.organization_id == org, TakeoffViewAlignment.drawing_id == drawing.id))
      cleared = res.rowcount or 0
      await self.session.flush()
    row = await self._row(org, drawing.id, view)
    if row is None:
      row = TakeoffViewAlignment(organization_id=org, project_id=drawing.project_id, drawing_id=drawing.id, frame_key=view)
      self.session.add(row)
    row.role, row.dx_mm, row.dy_mm, row.method, row.updated_by_user_id = "REFERENCE", 0, 0, "MANUAL", user_id
    return cleared

  async def set_reference(self, org: UUID, drawing_id: UUID, user_id: UUID, view: str) -> dict:
    drawing = await self._drawing(org, drawing_id)
    s = await self._state(org, drawing_id)
    self._need_view(s, view)
    cleared = await self._set_reference(org, drawing, user_id, view, s)
    await self.session.flush()
    await self._log(org, user_id, drawing_id, f"Frame: reference view {view}" + (f" ({cleared} earlier placements cleared)" if cleared else ""))
    await self.session.commit()
    out = await self.frame(org, drawing_id)
    out["cleared_placements"] = cleared
    return out

  async def _log(self, org: UUID, user_id: UUID, drawing_id: UUID, message: str) -> None:
    await self.audit.log(org, user_id, audit_entity("DRAWING"), drawing_id, AuditAction.UPDATE, message, commit=False)
