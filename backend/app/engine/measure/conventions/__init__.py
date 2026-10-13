from __future__ import annotations
from app.engine.measure.conventions.base import Convention
from app.engine.measure.conventions.frame_monolithic_a import FrameMonolithicA
from app.engine.measure.conventions.load_bearing_masonry_a import LoadBearingMasonryA

_REGISTRY: dict[str, Convention] = {c.code: c for c in (FrameMonolithicA(), LoadBearingMasonryA())}

def get_convention(code: str | None) -> Convention | None:
  return _REGISTRY.get(code) if code else None