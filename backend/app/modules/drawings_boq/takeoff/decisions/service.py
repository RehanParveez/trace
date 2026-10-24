from __future__ import annotations
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from uuid import UUID
from app.modules.drawings_boq.takeoff.decisions import store, catalog, effects
from app.engine.measure import proposed as PR, readings as QS
from app.core.exceptions import TraceException
from app.modules.audit.models import AuditAction

class DecisionsService(ExtractService):
  async def _state(self, org: UUID, drawing_id: UUID) -> tuple:
    drawing = await self.core._pdf_drawing(org, drawing_id)
    sheets = await self.core.repo.sheets(org, drawing_id)
    ids = [s.id for s in sheets]
    exts = {e.sheet_id: e for e in await self.repo.extractions(org, ids)}
    rows = [r for r in await self.repo.candidates(org, [i for i in ids if i in exts]) if r.decision != "REJECTED"]
    return drawing, sheets, exts, rows

  async def view(self, org: UUID, drawing_id: UUID) -> dict:
    drawing, sheets, exts, rows = await self._state(org, drawing_id)
    meta = drawing.ingestion_meta or {}

    eff, mine = store.effective(meta), store.made(meta)
    page_of = {s.id: s.page_no for s in sheets}
    level_of = {s.id: (None if ((s.prep_meta or {}).get("title") or {}).get("composite") else ((s.prep_meta or {}).get("title") or {}).get("level_hint")) for s in sheets}
    floors = self.prep._floor_keys(sheets)
    sizes = PR.sizes()
    web = float(sizes["beam_depth_mm"]["mm"])
    if QS.param("beam_depth_includes_slab"):
      web = max(web - float(QS.convention("slab_thickness_mm") or 0.0), 0.0)
    wall_rows = [r for r in (effects.wall_row(c, level_of.get(c.sheet_id) or ((c.facts or {}).get("view") or {}).get("level_hint")) for c in rows) if r]
    by_sheet: dict = {}
    for c in rows:
      by_sheet.setdefault(c.sheet_id, []).append(c)
    figures = {
      catalog.HEIGHT: effects.height(wall_rows, eff[catalog.HEIGHT], floors[0] if floors else None, float(sizes["plinth_beam_depth_mm"]["mm"]), web),
      catalog.BAND: effects.band([(e.stats or {}).get("tie_band_count") for e in exts.values()], eff[catalog.BAND]),
      catalog.NET: effects.lintel_net([([c for c in cs if c.category == "WALL"], [c for c in cs if c.category == "LINTEL"]) for cs in by_sheet.values()], eff[catalog.NET]),
      catalog.OPENINGS: effects.openings(rows, eff[catalog.OPENINGS]),
    }
    items: list = []
    every_stale: set = set()
    for d in catalog.DECISIONS:
      k = d["key"]
      stale_ids = [sid for sid, e in exts.items() if k in store.stale(e.stats, eff)]
      stale_pages = sorted(page_of[sid] for sid in stale_ids if sid in page_of)
      every_stale |= set(stale_pages)
      fx = figures[k]

      items.append({
        "key": k, "rule": d["rule"], "kind": d["kind"], "title": d["title"], "question": d["question"], "affects": d["affects"],
        "default": catalog.default_value(d), "current": eff[k], "made_by_person": k in mine, "made_at": (mine.get(k) or {}).get("at"),
        "applies": bool(fx["applies"]), "walls": int(fx.get("walls") or 0), "floors": list(fx.get("floors") or []),
        "options": [{"value": o["value"], "label": o["label"], "text": o["text"], "is_default": o["value"] == catalog.default_value(d), "in_force": o["value"] == eff[k],
          "effect": (fx["options"] or {}).get(o["value"])} for o in d["options"]],
        "stale_pages": stale_pages, "accepted_stale": sum(1 for r in rows if r.decision == "ACCEPTED" and r.sheet_id in set(stale_ids))})
    return {"drawing_id": drawing_id, "items": items, "stale_pages": sorted(every_stale), "sheets_read": len(exts)}

  async def choose(self, org: UUID, user_id: UUID, drawing_id: UUID, payload) -> dict:
    d = catalog.by_key(payload.key)

    if d is None:
      raise TraceException("This is not a decision the software asks for.", status_code=422, code="DECISION_UNKNOWN")
    if payload.value is not None and not catalog.valid(d, payload.value):
      raise TraceException("That is not one of the options.", status_code=422, code="DECISION_VALUE")
    drawing = await self.core._pdf_drawing(org, drawing_id)
    before = store.effective(drawing.ingestion_meta)[d["key"]]
    drawing.ingestion_meta = store.put(drawing.ingestion_meta, d["key"], payload.value, user_id)
    now = store.effective(drawing.ingestion_meta)[d["key"]]

    if now != before:
      label = next(o["label"] for o in d["options"] if o["value"] == now)
      await self.core._log(org, user_id, drawing_id, AuditAction.UPDATE, f"Decision '{d['title']}' set to '{label}'" + (" (back to the default)" if payload.value is None else ""), commit=False)
    await self.session.commit()
    return await self.view(org, drawing_id)
