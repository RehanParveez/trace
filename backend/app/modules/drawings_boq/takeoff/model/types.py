from __future__ import annotations
from dataclasses import dataclass
from typing import Any

PERSON, SECTION, PLAN_NOTES, LEVEL_MARKS, ASSUMED = "PERSON", "SECTION", "PLAN_NOTES", "LEVEL_MARKS", "ASSUMED"
TRUST = (PERSON, SECTION, PLAN_NOTES, LEVEL_MARKS, ASSUMED)

@dataclass(frozen=True)
class Source:
  kind: str
  field: str
  value: float
  how: str = ""
  basis: str = ""
  used: bool = False

  def as_dict(self) -> dict:
    return {"kind": self.kind, "field": self.field, "value": self.value, "how": self.how, "basis": self.basis, "used": self.used}

@dataclass(frozen=True)
class Level:
  key: str
  level_mm: float | None
  clear_mm: float | None
  f2f_mm: float | None
  sources: tuple = ()
  basis: str = ""
  level_how: str = ""

  def as_dict(self) -> dict:
    return {"key": self.key, "level_mm": self.level_mm, "clear_mm": self.clear_mm, "f2f_mm": self.f2f_mm, "basis": self.basis, "level_how": self.level_how,
      "sources": [s.as_dict() for s in self.sources]}

@dataclass(frozen=True)
class Decision:
  id: str
  question: str
  options: tuple = ()
  chosen: Any = None

  @property
  def open(self) -> bool:
    return self.chosen is None

  def as_dict(self) -> dict:
    return {"id": self.id, "question": self.question, "options": [dict(o) for o in self.options], "chosen": self.chosen, "open": self.open}

@dataclass(frozen=True)
class Sighting:
  drawing_id: str
  page_no: int
  candidate_key: str
  basis: str = ""

@dataclass(frozen=True)
class Member:
  id: str
  kind: str
  mark: str | None
  floor: str | None
  outline: tuple = ()
  size_mm: tuple | None = None
  height_mm: float | None = None
  sightings: tuple = ()

@dataclass(frozen=True)
class Face:
  side: str
  bounds: str = "OUTSIDE"

@dataclass(frozen=True)
class WallRun:
  id: str
  floor: str | None
  p0: tuple
  p1: tuple
  thickness_mm: float | None = None
  faces: tuple = ()

@dataclass(frozen=True)
class Fact:
  key: str
  value: Any = None
  unit: str | None = None
  sources: tuple = ()
  decision_id: str | None = None
