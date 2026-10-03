from __future__ import annotations
from app.engine.measure.conventions.base import Convention
from app.engine.measure.conventions.frame_monolithic_a import FrameMonolithicA

_REGISTRY: dict[str, Convention] = {c.code: c for c in (FrameMonolithicA(),)}

def get_convention(code: str | None) -> Convention | None:
  return _REGISTRY.get(code) if code else None