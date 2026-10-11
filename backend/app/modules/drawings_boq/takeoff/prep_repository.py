from __future__ import annotations
from collections import OrderedDict
from app.modules.drawings_boq.takeoff.prep.spatial import VectorIndex
from threading import Lock
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.drawings_boq.models import TakeoffSheetIndex
from sqlalchemy.orm import defer
from app.modules.drawings_boq.takeoff.prep.codec import decode_index

_CACHE_SIZE = 4
_cache: "OrderedDict[tuple, VectorIndex]" = OrderedDict()
_lock = Lock()

def _cache_get(key):
  with _lock:
    hit = _cache.get(key)
    if hit is not None:
      _cache.move_to_end(key)
    return hit

def _cache_put(key, value) -> None:
  with _lock:
    for stale in [k for k in _cache if k[0] == key[0] and k != key]:
      _cache.pop(stale, None)
    _cache[key] = value
    _cache.move_to_end(key)
    while len(_cache) > _CACHE_SIZE:
      _cache.popitem(last=False)

def cache_clear() -> None:
  with _lock:
    _cache.clear()

class PrepRepository:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def meta(self, org: UUID, sheet_id: UUID) -> TakeoffSheetIndex | None:
    """The index row without its large payload."""
    return (await self.session.execute(
      select(TakeoffSheetIndex).options(defer(TakeoffSheetIndex.payload))
      .where(TakeoffSheetIndex.sheet_id == sheet_id, TakeoffSheetIndex.organization_id == org))).scalar_one_or_none()

  async def save(self, org: UUID, sheet_id: UUID, version: int, payload: bytes, counts: dict, analysis: dict) -> TakeoffSheetIndex:
    row = await self.meta(org, sheet_id)
    if row is None:
      row = TakeoffSheetIndex(sheet_id=sheet_id, organization_id=org)
      self.session.add(row)
    row.analysis_version = version
    row.payload = payload
    row.segment_count = counts.get("segments", 0)
    row.ring_count = counts.get("rings", 0)
    row.word_count = counts.get("words", 0)
    row.analysis = analysis
    await self.session.flush()
    cache_clear()
    return row

  async def load_index(self, org: UUID, sheet_id: UUID) -> VectorIndex | None:
    meta = await self.meta(org, sheet_id)
    if meta is None:
      return None
    key = (sheet_id, meta.analysis_version, meta.updated_at.isoformat() if meta.updated_at else None)
    hit = _cache_get(key)
    if hit is not None:
      return hit
    payload = (await self.session.execute(
      select(TakeoffSheetIndex.payload).where(TakeoffSheetIndex.sheet_id == sheet_id, TakeoffSheetIndex.organization_id == org)
    )).scalar_one_or_none()
    if payload is None:
      return None
    index = decode_index(bytes(payload))
    _cache_put(key, index)
    return index
