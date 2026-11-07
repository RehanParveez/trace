from __future__ import annotations
import dataclasses
import enum

def plain(v):
  if isinstance(v, enum.Enum):
    return v.value
  if dataclasses.is_dataclass(v) and not isinstance(v, type):
    return {k: plain(x) for k, x in ((f.name, getattr(v, f.name)) for f in dataclasses.fields(v))}
  if isinstance(v, dict):
    return {str(k): plain(x) for k, x in v.items()}
  if isinstance(v, (list, tuple, set)):
    return [plain(x) for x in v]
  if v is None or isinstance(v, (str, int, float, bool)):
    return v
  return str(v)
