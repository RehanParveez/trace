from __future__ import annotations
import asyncio
import hashlib
import json
from app.modules.drawings_boq.takeoff.extract.extract_service import ExtractService
from uuid import UUID
from app.core.exceptions import TraceException
from app.modules.drawings_boq.takeoff.crops import render, source

DEFAULT_PX = 420

class CropService(ExtractService):
  async def crop(self, org: UUID, candidate_id: UUID, size_px: int, if_none_match: str | None) -> tuple[bytes | None, str]:
    rows = await self.repo.candidates_by_ids(org, [candidate_id])
    if not rows:
      raise TraceException("Item not found.", status_code=404, code="CANDIDATE_NOT_FOUND")
    cand = rows[0]

    sheet = await self.core._sheet(org, cand.sheet_id)
    drawing = await self.core._pdf_drawing(org, sheet.drawing_id)
    size_px = max(render.MIN_PX, min(render.MAX_PX, int(size_px or DEFAULT_PX)))
    key = json.dumps([str(cand.id), cand.kind, cand.geometry, sheet.page_no, drawing.storage_key, size_px], sort_keys=True, default=str)
    etag = '"' + hashlib.sha1(key.encode()).hexdigest()[:24] + '"'
    if if_none_match and etag in [v.strip() for v in if_none_match.split(",")]:
      return None, etag

    contents = await asyncio.to_thread(source.drawing_bytes, drawing.storage_key)
    png = await asyncio.to_thread(render.render_crop, contents, sheet.page_no, cand.kind, cand.geometry or {}, size_px)
    return png, etag
